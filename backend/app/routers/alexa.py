from fastapi import APIRouter, Request, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime, timedelta, timezone
import asyncio
import logging
import uuid
import json
import httpx
from jose import jwt, JWTError

from app.database import get_session
from app.models import User, StoryMeta, StoryRequest
from app.config import settings
from app.services.store import store
from app.auth_utils import get_password_hash, SECRET_KEY, ALGORITHM, get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alexa", tags=["alexa"])

# ──────────────────────────────────
# Alexa User Mapping
# ──────────────────────────────────

def get_or_create_alexa_user(alexa_user_id: str, session: Session, access_token: str | None = None) -> User:
    """Map an Alexa userId to a Storyja User (Linked, Guest, or Admin Fallback)."""
    
    # 1. Handle Account Linking (Access Token present)
    if access_token:
        try:
            payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                linked_user = session.get(User, user_id)
                if linked_user:
                    # Is this a new link? (First time using Alexa after Linking)
                    if linked_user.alexa_user_id != alexa_user_id:
                        logger.info(f"MIGRATION: Linking User {linked_user.email} (ID: {linked_user.id}) to Alexa {alexa_user_id}")
                        
                        # Store link
                        linked_user.alexa_user_id = alexa_user_id
                        session.add(linked_user)
                        
                        # Migrate Guest Stories (if any exist for this Alexa ID)
                        migrate_guest_stories(alexa_user_id, linked_user.id, session)
                        
                        session.commit()
                        session.refresh(linked_user)
                    else:
                        logger.info(f"ALEXA RESOLVE: User {linked_user.email} already linked.")
                    
                    return linked_user
            else:
                logger.warning("ALEXA RESOLVE: No user_id (sub) found in token payload")
        except JWTError as e:
            logger.warning(f"ALEXA RESOLVE: Invalid Access Token: {e}")
        except Exception as e:
            logger.error(f"ALEXA RESOLVE: Error in token-based resolution: {e}")

    # 2. Check for previously linked account (by index)
    if alexa_user_id:
        user = session.exec(select(User).where(User.alexa_user_id == alexa_user_id)).first()
        if user:
            logger.info(f"ALEXA RESOLVE: Found Linked User {user.email} (ID: {user.id})")
            return user

    # 3. Handle Guests (Phase 1 logic)
    guest_email = f"alexa_{alexa_user_id[-20:]}@storyja.guest".lower()
    existing_guest = session.exec(select(User).where(User.email == guest_email)).first()
    if existing_guest:
        return existing_guest

    # Create new Guest User
    if not settings.ALEXA_ALLOW_GUESTS:
        raise HTTPException(status_code=403, detail="Guests not allowed")

    new_user = User(
        id=str(uuid.uuid4())[:8],
        email=guest_email,
        username=f"Alexa Guest {alexa_user_id[-4:]}",
        hashed_password=get_password_hash(str(uuid.uuid4())),
        is_active=True,
        is_admin=False
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    logger.info(f"Created new Alexa Guest User: {new_user.username}")
    return new_user

def migrate_guest_stories(alexa_user_id: str, target_user_id: str, session: Session):
    """Move all stories from the anonymous Alexa guest account to the real user account."""
    guest_email = f"alexa_{alexa_user_id[-20:]}@storyja.guest".lower()
    guest_user = session.exec(select(User).where(User.email == guest_email)).first()
    
    if not guest_user:
        return # No guest history to migrate
    
    # Update all stories belonging to the guest
    stories = session.exec(select(StoryMeta).where(StoryMeta.user_id == guest_user.id)).all()
    count = 0
    for story in stories:
        story.user_id = target_user_id
        session.add(story)
        count += 1
    
    # Delete the guest user instead of just deactivating (as requested by user)
    session.delete(guest_user)
    session.commit()
    
    logger.info(f"MIGRATED {count} stories from guest {guest_user.id} to {target_user_id}. Guest user deleted.")

# ──────────────────────────────────
# Alexa Response Helpers
# ──────────────────────────────────

def get_canonical_slot_value(slot_data: dict) -> str | None:
    """Extract the canonical Name from Alexa Entity Resolution if available."""
    if not slot_data:
        return None
    resolutions = slot_data.get("resolutions", {}).get("resolutionsPerAuthority", [])
    for res in resolutions:
        if res.get("status", {}).get("code") == "ER_SUCCESS_MATCH":
            values = res.get("values", [])
            if values:
                return values[0].get("value", {}).get("name")
    return slot_data.get("value")

def alexa_response(text: str, should_end_session: bool = False, directives: list = None, session_attributes: dict = None):
    return {
        "version": "1.0",
        "sessionAttributes": session_attributes or {},
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": text
            },
            "shouldEndSession": should_end_session,
            "directives": directives or []
        }
    }

def alexa_elicit_slot(text: str, slot_to_elicit: str, intent_name: str, slots: dict):
    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": text
            },
            "directives": [
                {
                    "type": "Dialog.ElicitSlot",
                    "slotToElicit": slot_to_elicit,
                    "updatedIntent": {
                        "name": intent_name,
                        "confirmationStatus": "NONE",
                        "slots": slots
                    }
                }
            ],
            "shouldEndSession": False
        }
    }

# ──────────────────────────────────
# Webhook Endpoint
# ──────────────────────────────────

async def _alexa_webhook_logic(data: dict, session: Session):
    logger.info(f"ALEXA REQUEST: {json.dumps(data)}")
    req_type = data.get("request", {}).get("type", "")
    # Robust User ID Extraction (Session vs Context)
    alexa_user_id = data.get("session", {}).get("user", {}).get("userId")
    if not alexa_user_id:
        alexa_user_id = data.get("context", {}).get("System", {}).get("user", {}).get("userId")
    
    if not alexa_user_id and req_type not in ["AudioPlayer.PlaybackStarted", "AudioPlayer.PlaybackFinished"]:
        logger.error("No Alexa UserID found in request")
        return {}

    # Extract Access Token (for Phase 2 Account Linking)
    access_token = data.get("session", {}).get("user", {}).get("accessToken")
    
    # Get the internal user
    try:
        user = get_or_create_alexa_user(alexa_user_id, session, access_token=access_token)
    except Exception as e:
        logger.error(f"Alexa Auth Error: {e} | UserID: {alexa_user_id}")
        return alexa_response("Entschuldigung, ich konnte dein Profil nicht laden.")

    # 1. Handle AudioPlayer & System events (Must return empty response, NO SPEECH)
    if req_type == "AudioPlayer.PlaybackNearlyFinished":
        token = data.get("request", {}).get("token", "")
        if token.startswith("playlist_"):
            playlist = store.get_playlist(user.id)
            if playlist:
                next_story = playlist[0]
                # Remove from database immediately as it's being queued
                store.remove_from_playlist(user.id, next_story.id)
                
                audio_url = f"{settings.BASE_URL}/api/stories/{next_story.id}/audio"
                directive = {
                    "type": "AudioPlayer.Play",
                    "playBehavior": "ENQUEUE",
                    "audioItem": {
                        "stream": {
                            "token": f"playlist_{next_story.id}",
                            "url": audio_url,
                            "offsetInMilliseconds": 0,
                            "expectedPreviousToken": token
                        },
                        "metadata": {
                            "title": next_story.title,
                            "subtitle": "Nächste Geschichte aus deiner Liste",
                            "art": {
                                "sources": [{"url": f"{settings.BASE_URL}{next_story.image_url}" if next_story.image_url else ""}]
                            }
                        }
                    }
                }
                return {"version": "1.0", "response": {"directives": [directive]}}
        return {"version": "1.0", "response": {}}

    if req_type.startswith("AudioPlayer.") or req_type == "System.ExceptionEncountered":
        logger.info(f"Handling background Alexa event: {req_type}")
        return {"version": "1.0", "response": {}}

    # 2. Handle LaunchRequest
    if req_type == "LaunchRequest":
        playlist = store.get_playlist(user.id)
        if playlist:
            prompt = "Willkommen zurück! Möchtest du eine fertige Geschichte abspielen oder eine neue Geschichte erstellen?"
            last_prompt = "OFFERED_PLAYLIST"
        else:
            prompt = "Willkommen bei Storyja. Möchtest du eine neue Geschichte erstellen?"
            last_prompt = "OFFERED_CREATE"
            
        return alexa_response(
            prompt,
            should_end_session=False,
            session_attributes={"lastPrompt": last_prompt}
        )

    if req_type == "IntentRequest":
        intent_name = data["request"]["intent"]["name"]
        slots = data["request"]["intent"].get("slots", {})

        if intent_name == "GenerateStoryIntent":
            idea = slots.get("idea", {}).get("value")
            genre = slots.get("genre", {}).get("value")

            # 1. Elicit Idea if missing
            if not idea:
                return alexa_response(
                    "Über was soll die Geschichte handeln?",
                    should_end_session=False
                )
            
            # 2. Genre is automatically defaulted if missing. We skip explicitly asking for it 
            # to prevent Alexa Dialog.ElicitSlot crashes if the Alexa model isn't fully configured.

            # Start Generation Pipeline
            story_id = str(uuid.uuid4())[:8]
            
            # Better Genre Mapping
            raw_genre = get_canonical_slot_value(slots.get("genre"))
            backend_genre = raw_genre or "Abenteuer"
            
            # Fuzzy fallback / Normalization
            bg_lower = backend_genre.lower()
            if "nach" in bg_lower or "schlaf" in bg_lower: backend_genre = "Gute Nacht"
            elif "lustig" in bg_lower or "kom" in bg_lower: backend_genre = "Komödie"
            elif "krimi" in bg_lower or "spann" in bg_lower or "detekt" in bg_lower: backend_genre = "Krimi"
            elif "grusel" in bg_lower or "horror" in bg_lower: backend_genre = "Grusel"
            elif "abenteu" in bg_lower: backend_genre = "Abenteuer"
            elif "märchen" in bg_lower or "fabel" in bg_lower: backend_genre = "Märchen"

            # Style Mapping (Author)
            style = "adams"
            bg_lower = backend_genre.lower()
            if "nach" in bg_lower or "schlaf" in bg_lower: backend_genre = "Gute Nacht"
            elif "lustig" in bg_lower or "kom" in bg_lower: backend_genre = "Komödie"
            elif "spannend" in bg_lower or "krimi" in bg_lower or "spann" in bg_lower or "detekt" in bg_lower: backend_genre = "Krimi"
            elif "grusel" in bg_lower or "horror" in bg_lower: backend_genre = "Grusel"
            elif "abenteu" in bg_lower: backend_genre = "Abenteuer"
            elif "märchen" in bg_lower or "fabel" in bg_lower: backend_genre = "Märchen"

            if "Krimi" in backend_genre: style = "fitzek"
            elif "Gute Nacht" in backend_genre: style = "lindgren"
            elif "Grusel" in backend_genre: style = "king"
            elif "Komödie" in backend_genre: style = "jaud"
            elif "Abenteuer" in backend_genre: style = "adams"

            # Execute pipeline in background via StoryService
            from app.services.story_service import story_service
            asyncio.create_task(
                story_service.run_pipeline(
                    story_id=story_id,
                    prompt=f"Kurzgeschichte über {idea}",
                    genre=backend_genre,
                    style=style,
                    characters=None,
                    target_minutes=10,
                    voice_key="seraphina",
                    speech_rate="0%",
                    original_prompt=idea,
                    user_id=user.id,
                    alexa_user_id=alexa_user_id
                )
            )

            return alexa_response(
                f"Abgemacht! Ich erstelle dir eine {backend_genre} Geschichte über {idea}. "
                "Das dauert etwa zwei Minuten. Ich bin gleich fertig!",
                should_end_session=True
            )

        if intent_name == "PlayPlaylistIntent":
            playlist = store.get_playlist(user.id)
            if not playlist:
                return alexa_response("Deine Liste ist aktuell leer. Füge in der App Geschichten hinzu.")
            
            first = playlist[0]
            # Remove from database immediately as playback starts
            store.remove_from_playlist(user.id, first.id)
            
            audio_url = f"{settings.BASE_URL}/api/stories/{first.id}/audio"
            
            directive = {
                "type": "AudioPlayer.Play",
                "playBehavior": "REPLACE_ALL",
                "audioItem": {
                    "stream": {
                        "token": f"playlist_{first.id}",
                        "url": audio_url,
                        "offsetInMilliseconds": 0
                    },
                    "metadata": {
                        "title": first.title,
                        "subtitle": "Aus deiner Liste",
                        "art": {
                            "sources": [{"url": f"{settings.BASE_URL}{first.image_url}" if first.image_url else ""}]
                        }
                    }
                }
            }
            return alexa_response(f"Alles klar! Ich spiele deine Geschichte: {first.title}.", should_end_session=True, directives=[directive])

        if intent_name == "ClearPlaylistIntent":
            store.clear_playlist(user.id)
            return alexa_response("Deine Alexa Playlist wurde geleert.", should_end_session=True)

        if intent_name == "PlayStoryIntent" or intent_name == "AMAZON.ResumeIntent":
            # Get latest story for this user
            stories = store.get_all(user_id=user.id)
            if not stories:
                return alexa_response("Du hast bisher noch keine Geschichten. Sag einfach: Erstelle eine Geschichte.")
            
            latest = stories[0]
            if latest.status != "done":
                return alexa_response("Deine Geschichte wird gerade noch geschrieben. Ich sag Bescheid, wenn sie fertig ist.")

            audio_url = f"{settings.BASE_URL}/api/stories/{latest.id}/audio"
            
            directive = {
                "type": "AudioPlayer.Play",
                "playBehavior": "REPLACE_ALL",
                "audioItem": {
                    "stream": {
                        "token": latest.id,
                        "url": audio_url,
                        "offsetInMilliseconds": 0
                    },
                    "metadata": {
                        "title": latest.title,
                        "subtitle": f"Ein {latest.genre} Epos",
                        "art": {
                            "sources": [
                                {
                                    "url": f"{settings.BASE_URL}{latest.image_url}" if latest.image_url else ""
                                }
                            ]
                        }
                    }
                }
            }
            return alexa_response(f"Ich spiele deine Geschichte: {latest.title}.", should_end_session=True, directives=[directive])

        if intent_name == "AMAZON.StopIntent" or intent_name == "AMAZON.CancelIntent":
            return alexa_response("Tschüss! Bis zum nächsten Mal.", should_end_session=True, directives=[{"type": "AudioPlayer.Stop"}])

        if intent_name == "AMAZON.HelpIntent":
            return alexa_response("Du kannst mir eine Idee für eine neue Geschichte geben oder eine bereits fertige Geschichte aus deiner Playlist hören. Was möchtest du tun?")

        if intent_name == "AMAZON.YesIntent":
            session_attr = data.get("session", {}).get("attributes", {})
            last_prompt = session_attr.get("lastPrompt")
            
            if last_prompt == "OFFERED_PLAYLIST":
                # ... [Playlist removal logic same as before, preserving it] ...
                playlist = store.get_playlist(user.id)
                if not playlist:
                    return alexa_response("Deine Liste ist aktuell leer. Möchtest du stattdessen eine neue Geschichte erfinden?")
                
                first = playlist[0]
                store.remove_from_playlist(user.id, first.id)
                
                audio_url = f"{settings.BASE_URL}/api/stories/{first.id}/audio"
                directive = {
                    "type": "AudioPlayer.Play",
                    "playBehavior": "REPLACE_ALL",
                    "audioItem": {
                        "stream": {"token": f"playlist_{first.id}", "url": audio_url, "offsetInMilliseconds": 0},
                        "metadata": {
                            "title": first.title,
                            "subtitle": "Aus deiner Liste",
                            "art": {"sources": [{"url": f"{settings.BASE_URL}{first.image_url}" if first.image_url else ""}]}
                        }
                    }
                }
                return alexa_response(f"Alles klar! Ich spiele deine Geschichte: {first.title}.", should_end_session=True, directives=[directive])
            
            # Start Creation Flow
            return alexa_response(
                "Prima! Über was soll die neue Geschichte handeln?",
                should_end_session=False
            )

        if intent_name == "AMAZON.NoIntent":
            return alexa_response("Kein Problem. Melde dich einfach, wenn du Lust auf eine Geschichte hast. Tschüss!", should_end_session=True)

    return alexa_response("Das habe ich leider nicht verstanden. Möchtest du eine bereits fertige Geschichte hören oder eine neue Geschichte erfinden?")

@router.post("/webhook")
async def alexa_webhook(request: Request, session: Session = Depends(get_session)):
    data = await request.json()
    import traceback
    try:
        with open("alexa_debug.txt", "a", encoding="utf-8") as f:
            f.write(f"\n\n=== NEW REQUEST ===\n{json.dumps(data, indent=2)}\n")
        
        response = await _alexa_webhook_logic(data, session)
        
        with open("alexa_debug.txt", "a", encoding="utf-8") as f:
            f.write(f"\n--- RESPONSE ---\n{json.dumps(response, indent=2)}\n")
        return response
    except Exception as e:
        with open("alexa_debug.txt", "a", encoding="utf-8") as f:
            f.write(f"\n--- ERROR ---\n{traceback.format_exc()}\n")
        raise

# ──────────────────────────────────
# Proactive Events (Notification)
# ──────────────────────────────────

async def send_alexa_notification(alexa_user_id: str, title: str):
    """Send a proactive event notification to Alexa (LED glow)."""
    if not settings.ALEXA_CLIENT_ID or not settings.ALEXA_CLIENT_SECRET:
        logger.warning("Alexa Client ID/Secret not set. Skiping notification.")
        return

    try:
        # 1. Get Access Token from Amazon LWA
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.amazon.com/auth/o2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.ALEXA_CLIENT_ID.strip(),
                    "client_secret": settings.ALEXA_CLIENT_SECRET.strip(),
                    "scope": "alexa::proactive_events"
                }
            )
            if resp.status_code != 200:
                logger.error(f"LWA Token Error: {resp.status_code} - {resp.text}")
                resp.raise_for_status()
            
            access_token = resp.json()["access_token"]

            # 2. Send Proactive Event
            # Schema: AMAZON.MediaContent.Available
            # Use direct strings (no localizedattribute refs) for simplicity and reliability
            # NOTE: Use strftime to avoid microseconds in timestamps (Amazon rejects them)
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            expiry_str = (datetime.now(timezone.utc) + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
            safe_title = (title or "Deine Geschichte")[:60]
            event_payload = {
                "timestamp": now_str,
                "referenceId": str(uuid.uuid4()),
                "expiryTime": expiry_str,
                "event": {
                    "name": "AMAZON.MediaContent.Available",
                    "payload": {
                        "availability": {
                            "startTime": now_str,
                            "method": "STREAM"
                        },
                        "content": {
                            "name": safe_title,
                            "contentType": "BOOK"
                        }
                    }
                },
                "relevantAudience": {
                    "type": "Unicast",
                    "payload": {
                        "user": alexa_user_id
                    }
                }
            }

            multimodal_payload = {
                "title": title
            }
            
            # Note: The API endpoint depends on the region. Amazon Europe: api.eu.amazonalexa.com
            # For simplicity we try the global/European one.
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
            
            # Alexa Notification Endpoint (Region: Europe)
            base_api_url = "https://api.eu.amazonalexa.com/v1/proactiveEvents"
            if settings.ALEXA_SKILL_STAGE == "development":
                api_url = f"{base_api_url}/stages/development"
            else:
                api_url = base_api_url
            
            event_resp = await client.post(api_url, json=event_payload, headers=headers)
            if event_resp.status_code != 202:
                logger.error(f"Alexa Notification Error: {event_resp.status_code} - {event_resp.text} | Payload: {json.dumps(event_payload)}")
            else:
                logger.info(f"Successfully sent Alexa notification to {alexa_user_id} (title: {title})")
                
    except Exception as e:
        logger.error(f"Failed to send Alexa notification: {e}", exc_info=True)

@router.post("/unlink")
async def alexa_unlink(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Manually clear the Alexa User ID from the profile."""
    if current_user.alexa_user_id:
        logger.info(f"ALEXA UNLINK: Manually clearing Alexa ID for {current_user.email}")
        current_user.alexa_user_id = None
        session.add(current_user)
        session.commit()
        return {"status": "success", "message": "Alexa Verknüpfung aufgehoben."}
    return {"status": "success", "message": "Keine Verknüpfung vorhanden."}

# ──────────────────────────────────
# Alexa Permission Check (Admin)
# ──────────────────────────────────

@router.get("/check-permissions")
async def alexa_check_permissions(
    current_user: User = Depends(get_current_active_user)
):
    """
    Admin endpoint: Checks Alexa Proactive Events configuration by attempting
    to obtain an LWA access token. Returns a detailed status report.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur für Admins.")

    report = {
        "client_id_set": bool(settings.ALEXA_CLIENT_ID),
        "client_secret_set": bool(settings.ALEXA_CLIENT_SECRET),
        "skill_stage": settings.ALEXA_SKILL_STAGE,
        "lwa_token_status": None,
        "lwa_error": None,
        "proactive_events_enabled": False,
    }

    if not settings.ALEXA_CLIENT_ID or not settings.ALEXA_CLIENT_SECRET:
        report["lwa_error"] = "ALEXA_CLIENT_ID oder ALEXA_CLIENT_SECRET fehlen in der .env Datei."
        return report

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.amazon.com/auth/o2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.ALEXA_CLIENT_ID.strip(),
                    "client_secret": settings.ALEXA_CLIENT_SECRET.strip(),
                    "scope": "alexa::proactive_events"
                }
            )
            report["lwa_http_status"] = resp.status_code

            if resp.status_code == 200:
                token_data = resp.json()
                report["lwa_token_status"] = "ok"
                report["proactive_events_enabled"] = True
                report["token_expires_in"] = token_data.get("expires_in")
                report["token_type"] = token_data.get("token_type")
            else:
                body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                report["lwa_token_status"] = "error"
                report["lwa_error"] = body
                if isinstance(body, dict) and body.get("error") == "invalid_scope":
                    report["lwa_error"] = (
                        "Permission 'Alexa Proactive Events' ist im Skill NICHT aktiviert. "
                        "Bitte in der Alexa Developer Console unter Build → Permissions aktivieren."
                    )
    except Exception as e:
        report["lwa_token_status"] = "exception"
        report["lwa_error"] = str(e)

    return report


# ──────────────────────────────────
# Test Notification (Admin Debug)
# ──────────────────────────────────

@router.post("/test-notification")
async def alexa_test_notification(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    Admin endpoint: Sends a real Alexa notification to the current user's
    linked Alexa device. Returns the full Amazon API response for debugging.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur für Admins.")

    alexa_user_id = current_user.alexa_user_id
    if not alexa_user_id:
        return {"status": "error", "message": "Kein Alexa User ID mit diesem Account verknüpft. Bitte zuerst Account Linking durchführen."}

    if not settings.ALEXA_CLIENT_ID or not settings.ALEXA_CLIENT_SECRET:
        return {"status": "error", "message": "ALEXA_CLIENT_ID oder ALEXA_CLIENT_SECRET fehlen."}

    debug = {
        "alexa_user_id": alexa_user_id[:20] + "...",
        "skill_stage": settings.ALEXA_SKILL_STAGE,
        "lwa_status": None,
        "notification_status": None,
        "notification_response": None,
        "notification_body": None,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Step 1: Get token
            lwa_resp = await client.post(
                "https://api.amazon.com/auth/o2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.ALEXA_CLIENT_ID.strip(),
                    "client_secret": settings.ALEXA_CLIENT_SECRET.strip(),
                    "scope": "alexa::proactive_events"
                }
            )
            debug["lwa_status"] = lwa_resp.status_code
            if lwa_resp.status_code != 200:
                debug["lwa_error"] = lwa_resp.text
                return debug

            access_token = lwa_resp.json()["access_token"]

            # Step 2: Send notification
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            expiry_str = (datetime.now(timezone.utc) + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
            payload = {
                "timestamp": now_str,
                "referenceId": str(uuid.uuid4()),
                "expiryTime": expiry_str,
                "event": {
                    "name": "AMAZON.MediaContent.Available",
                    "payload": {
                        "availability": {
                            "startTime": now_str,
                            "method": "STREAM"
                        },
                        "content": {
                            "name": "Neue Geschichte bereit",
                            "contentType": "BOOK"
                        }
                    }
                },
                "relevantAudience": {
                    "type": "Unicast",
                    "payload": {"user": alexa_user_id}
                }
            }

            base_url = "https://api.eu.amazonalexa.com/v1/proactiveEvents"
            api_url = f"{base_url}/stages/development" if settings.ALEXA_SKILL_STAGE == "development" else base_url

            notify_resp = await client.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}
            )
            debug["notification_status"] = notify_resp.status_code
            debug["notification_body"] = notify_resp.text or "(leer – 202 bedeutet Erfolg)"

            if notify_resp.status_code == 202:
                debug["result"] = "✅ Benachrichtigung erfolgreich gesendet!"
            else:
                debug["result"] = f"❌ Fehler: HTTP {notify_resp.status_code}"

    except Exception as e:
        debug["exception"] = str(e)

    return debug
