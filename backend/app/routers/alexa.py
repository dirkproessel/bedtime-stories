from fastapi import APIRouter, Request, Depends, HTTPException
from sqlmodel import Session, select
import asyncio
import logging
import uuid
import json
import httpx
from datetime import datetime, timezone

from app.database import get_session
from app.models import User, StoryMeta, StoryRequest
from app.config import settings
from app.services.store import store
from app.auth_utils import get_password_hash

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alexa", tags=["alexa"])

# ──────────────────────────────────
# Alexa User Mapping
# ──────────────────────────────────

def get_or_create_alexa_user(alexa_user_id: str, session: Session) -> User:
    """Map an Alexa userId to a Storyja User (Guest or Admin Fallback)."""
    
    # 1. Check for Admin Fallback if configured and no other link exists
    if settings.ALEXA_DEFAULT_USER_ID:
        # If the skill is private, we can just return the Admin
        admin = session.exec(select(User).where(User.id == settings.ALEXA_DEFAULT_USER_ID)).first()
        if admin:
            return admin

    # 2. Check for existing Alexa Guest User
    guest_email = f"alexa_{alexa_user_id[-20:]}@storyja.guest".lower()
    existing_user = session.exec(select(User).where(User.email == guest_email)).first()
    if existing_user:
        return existing_user

    # 3. Create new Guest User if allowed
    if not settings.ALEXA_ALLOW_GUESTS:
        raise HTTPException(status_code=403, detail="Guests not allowed")

    new_user = User(
        id=str(uuid.uuid4())[:8],
        email=guest_email,
        username=f"Alexa Guest {alexa_user_id[-4:]}",
        hashed_password=get_password_hash(str(uuid.uuid4())), # Random pass
        is_active=True,
        is_admin=False
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    logger.info(f"Created new Alexa Guest User: {new_user.username}")
    return new_user

# ──────────────────────────────────
# Alexa Response Helpers
# ──────────────────────────────────

def alexa_response(text: str, should_end_session: bool = False, directives: list = None):
    return {
        "version": "1.0",
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

@router.post("/webhook")
async def alexa_webhook(request: Request, session: Session = Depends(get_session)):
    data = await request.json()
    logger.info(f"ALEXA REQUEST: {json.dumps(data)}")
    req_type = data.get("request", {}).get("type")
    alexa_user_id = data.get("session", {}).get("user", {}).get("userId")
    
    # Extract Access Token (for Phase 2 Account Linking)
    access_token = data.get("session", {}).get("user", {}).get("accessToken")
    
    # Get the internal user
    try:
        if access_token:
            # TODO: Validate JWT for Phase 2
            # user = get_user_from_token(access_token)
            user = get_or_create_alexa_user(alexa_user_id, session)
        else:
            user = get_or_create_alexa_user(alexa_user_id, session)
    except Exception as e:
        logger.error(f"Alexa Auth Error: {e}")
        return alexa_response("Entschuldigung, ich konnte dein Profil nicht laden.")

    if req_type == "LaunchRequest":
        return alexa_response(
            "Willkommen bei Storyja. Möchtest du eine Geschichte erstellen oder deine letzte Geschichte abspielen?",
            should_end_session=False
        )

    if req_type == "IntentRequest":
        intent_name = data["request"]["intent"]["name"]
        slots = data["request"]["intent"].get("slots", {})

        if intent_name == "GenerateStoryIntent":
            idea = slots.get("idea", {}).get("value")
            genre = slots.get("genre", {}).get("value")

            # Check dialog state - if not complete, delegate back to Alexa
            dialog_state = data.get("request", {}).get("dialogState")
            if dialog_state != "COMPLETED" and (not idea or not genre):
                return {
                    "version": "1.0",
                    "response": {
                        "directives": [
                            {
                                "type": "Dialog.Delegate",
                                "updatedIntent": {
                                    "name": "GenerateStoryIntent",
                                    "confirmationStatus": "NONE",
                                    "slots": slots
                                }
                            }
                        ]
                    }
                }

            # Start Generation Pipeline
            story_id = str(uuid.uuid4())[:8]
            
            # Map genre to backend genre if needed
            backend_genre = genre or "Abenteuer"
            if "nach" in backend_genre.lower(): backend_genre = "Gute Nacht"
            elif "kom" in backend_genre.lower(): backend_genre = "Komödie"
            
            # Style Mapping
            style = "adams"
            if "krimi" in backend_genre.lower(): style = "fitzek"
            elif "nach" in backend_genre.lower(): style = "lindgren"

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
                "Das dauert etwa zwei Minuten. Ich lasse deine Alexa leuchten, sobald ich fertig bin. "
                "Bis gleich!",
                should_end_session=True
            )

        if intent_name == "PlayStoryIntent" or intent_name == "AMAZON.ResumeIntent":
            # Get latest story for this user
            stories = store.get_all(user_id=user.id)
            if not stories:
                return alexa_response("Du hast bisher noch keine Geschichten. Sag einfach: Erstelle eine Geschichte.")
            
            latest = stories[0]
            if latest.status != "done":
                return alexa_response("Deine Geschichte wird gerade noch geschrieben. Ich melde mich, wenn sie fertig ist.")

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
            return alexa_response("Du kannst mir eine Idee für eine neue Geschichte geben, oder mich bitten, deine letzte Geschichte abzuspielen. Was möchtest du tun?")

    return alexa_response("Das habe ich leider nicht verstanden. Möchtest du eine Geschichte erstellen oder eine abspielen?")

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
                    "client_id": settings.ALEXA_CLIENT_ID,
                    "client_secret": settings.ALEXA_CLIENT_SECRET,
                    "scope": "alexa::proactive_events"
                }
            )
            resp.raise_for_status()
            access_token = resp.json()["access_token"]

            # 2. Send Proactive Event
            # Schema: AMAZON.MediaContent.Available
            event_payload = {
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "referenceId": str(uuid.uuid4()),
                "expiryTime": (datetime.now(timezone.utc).replace(microsecond=0)).isoformat().replace("+00:00", "Z"),
                "event": {
                    "name": "AMAZON.MediaContent.Available",
                    "payload": {
                        "availability": {
                            "startTime": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                            "method": "STREAM"
                        },
                        "content": {
                            "name": "localized:title",
                            "contentType": "AUDIOBOOK"
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
            
            # Try Europe first (assuming user is in Germany/Europe)
            api_url = "https://api.eu.amazonalexa.com/v1/proactiveEvents/stages/development" 
            # In production, this would be /v1/proactiveEvents
            
            event_resp = await client.post(api_url, json=event_payload, headers=headers)
            if event_resp.status_code != 202:
                logger.error(f"Alexa Notification Error: {event_resp.status_code} - {event_resp.text}")
            else:
                logger.info(f"Successfully sent Alexa notification to {alexa_user_id}")
                
    except Exception as e:
        logger.error(f"Failed to send Alexa notification: {e}")
