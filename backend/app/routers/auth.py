from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select
from datetime import timedelta
import uuid
import html
import urllib.parse

from app.database import get_session
from app.models import User, UserCreate, UserResponse, Token, PasswordUpdate, KindleEmailUpdate, UsernameUpdate, VoiceNameUpdate
from app.auth_utils import (
    verify_password, get_password_hash, create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES, get_current_active_user,
    create_alexa_auth_code, verify_alexa_auth_code
)
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
def register_user(user_in: UserCreate, session: Session = Depends(get_session)):
    """Register a new standard user."""
    # Check if user exists
    existing_user = session.exec(select(User).where(User.email == user_in.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Eine Registrierung mit dieser E-Mail ist bereits vorhanden."
        )

    # Determine if this should be the admin
    is_admin = False
    config_admin = settings.ADMIN_EMAIL.lower()
    target_email = user_in.email.lower()
    
    logger.info(f"Registering user: {target_email}. Configured admin: '{config_admin}'")
    
    if target_email == config_admin:
        is_admin = True
        logger.info(f"User matches admin email. Setting is_admin=True")

    new_user = User(
        id=str(uuid.uuid4()),
        email=user_in.email.lower(),
        username=user_in.email.lower(),
        hashed_password=get_password_hash(user_in.password),
        is_admin=is_admin,
    )
    
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """OAuth2 compatible token login, get an access token for future requests."""
    user = session.exec(select(User).where(User.email == form_data.username.lower())).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falsche E-Mail oder Passwort",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Benutzerkonto inaktiv")
    
    # Failsafe: Force is_admin and kindle_email for the configured admin email
    config_admin = settings.ADMIN_EMAIL.lower().strip()
    user_email = user.email.lower().strip()
    
    logger.info(f"Checking failsafe for {user_email}. DB admin: {user.is_admin}, Config admin: '{config_admin}'")
    
    if user_email == config_admin:
        needs_update = False
        
        if not user.is_admin:
            logger.info(f"Failsafe: Promoting {user_email} to admin.")
            user.is_admin = True
            needs_update = True
        
        if not user.kindle_email and settings.KINDLE_EMAIL:
            logger.info(f"Failsafe: Restoring Kindle email for {user_email}.")
            user.kindle_email = settings.KINDLE_EMAIL
            needs_update = True
            
        if needs_update:
            session.add(user)
            session.commit()
            session.refresh(user)
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def read_users_me(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Get the profile of the currently logged-in user."""
    config_admin = settings.ADMIN_EMAIL.lower().strip()
    user_email = current_user.email.lower().strip()
    
    if user_email == config_admin:
        needs_update = False
        if not current_user.is_admin:
            current_user.is_admin = True
            needs_update = True
        if not current_user.kindle_email and settings.KINDLE_EMAIL:
            current_user.kindle_email = settings.KINDLE_EMAIL
            needs_update = True
        
        if needs_update:
            session.add(current_user)
            session.commit()
            session.refresh(current_user)
            
    return current_user


@router.put("/me/password")
def update_password(
    data: PasswordUpdate, 
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Update current user password."""
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Das aktuelle Passwort ist falsch.")
        
    current_user.hashed_password = get_password_hash(data.new_password)
    session.add(current_user)
    session.commit()
    return {"status": "success", "message": "Passwort erfolgreich geändert."}
    
    
@router.put("/me/kindle")
def update_kindle_email(
    data: KindleEmailUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    current_user.kindle_email = data.kindle_email
    session.add(current_user)
    session.commit()
    return {"status": "success", "message": "Kindle-Adresse geändert."}

@router.put("/me/username")
def update_username(
    data: UsernameUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    current_user.username = data.username
    session.add(current_user)
    session.commit()
    return {"status": "success", "message": "Benutzername geändert."}
 
@router.put("/me/voice-name")
def update_voice_name(
    data: VoiceNameUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    current_user.custom_voice_name = data.voice_name
    session.add(current_user)
    session.commit()
    return {"status": "success", "message": "Stimmen-Name geändert."}


@router.put("/me/avatar", response_model=UserResponse)
async def update_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Upload or update profile picture."""
    # Validate mime type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image type")

    avatars_dir = settings.AUDIO_OUTPUT_DIR / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)
    
    avatar_path = avatars_dir / f"{current_user.id}.jpg"
    thumb_path = avatars_dir / f"{current_user.id}_thumb.jpg"
    
    try:
        content = await file.read()
        avatar_path.write_bytes(content)
        
        # use the existing generator utility or recreate here via to_thread
        from PIL import Image
        import asyncio
        import io
        
        def process_image():
            # load the image
            with Image.open(io.BytesIO(content)) as img:
                img = img.convert("RGB")
                
                # Make sure the main avatar is a reasonable size
                img.thumbnail((512, 512), Image.LANCZOS)
                img.save(avatar_path, "JPEG", quality=85, optimize=True)
                
                # Make the thumbnail
                img.thumbnail((128, 128), Image.LANCZOS)
                img.save(thumb_path, "JPEG", quality=80, optimize=True)
        
        await asyncio.to_thread(process_image)
        
        # update DB
        current_user.avatar_url = f"{settings.BASE_URL}/api/users/{current_user.id}/avatar.jpg"
        session.add(current_user)
        session.commit()
        session.refresh(current_user)
        
        return current_user
        
    except Exception as e:
        logger.error(f"Failed to process avatar for {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Fehler bei der Bildverarbeitung")

@router.post("/me/voice-clone", response_model=UserResponse)
async def create_voice_clone(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Clone user voice via Fish Audio API."""
    if not settings.FISH_API_KEY:
        raise HTTPException(status_code=500, detail="Fish Audio API Key nicht konfiguriert")

    # Validate audio type
    if not (file.content_type.startswith("audio/") or file.filename.endswith(('.mp3', '.wav', '.m4a'))):
        raise HTTPException(status_code=400, detail="Bitte lade eine Audiodatei hoch (MP3, WAV, M4A)")

    try:
        from fishaudio import FishAudio
        import asyncio
        
        content = await file.read()
        fish = FishAudio(api_key=settings.FISH_API_KEY)
        
        # Check max voices limit
        if len(current_user.custom_voices) >= 5:
            raise HTTPException(status_code=400, detail="Maximal 5 Stimmen-Klone erlaubt.")

        # Create the model on Fish Audio
        # We use the username or email as the title
        title = f"Voice for {current_user.username or current_user.email}"
        
        def call_fish():
            return fish.voices.create(
                title=title,
                voices=[content],
                visibility="private",
            )
        
        # Run the blocking SDK call in a separate thread
        model = await asyncio.to_thread(call_fish)
        
        # Create UserVoice in DB
        from app.models import UserVoice
        new_voice = UserVoice(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            fish_voice_id=model.id,
            name=title,
            is_public=False
        )
        
        session.add(new_voice)
        session.commit()
        
        # 1. Generate Voice Preview
        from app.services.tts_service import generate_voice_preview
        from pathlib import Path
        import json
        
        preview_dir = settings.AUDIO_OUTPUT_DIR / "previews"
        preview_dir.mkdir(parents=True, exist_ok=True)
        preview_path = preview_dir / f"{new_voice.id}.mp3"
        
        try:
            await generate_voice_preview(new_voice.id, preview_path)
            
            # 2. Analyze with Gemini
            if settings.GEMINI_API_KEY and preview_path.exists():
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                
                def analyze_audio():
                    uploaded = genai.upload_file(path=str(preview_path), display_name=preview_path.stem)
                    prompt = '''
                    Hör dir diese kurze Sprachaufnahme an.
                    Analysiere die Stimme und antworte **ausschließlich** im folgenden JSON Format ohne Markdown-Blöcke:
                    {
                        "gender": "Schreibe exakt 'male', 'female' oder 'neutral'",
                        "description": "Maximal 2 bis 3 kurze, knackige Worte zum Klang der Stimme (z.B. 'Warm & sanft')"
                    }
                    '''
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    res = model.generate_content([uploaded, prompt])
                    genai.delete_file(uploaded.name)
                    return res.text
                
                res_text = await asyncio.to_thread(analyze_audio)
                clean_text = res_text.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_text)
                
                new_voice.gender = data.get("gender")
                new_voice.description = data.get("description")
                session.add(new_voice)
                session.commit()
                logger.info(f"Gemini voice analysis succeeded: {data}")
                
        except Exception as preview_err:
            logger.warning(f"Failed to generate or analyze voice preview for {new_voice.id}: {preview_err}")
        session.refresh(current_user)
        
        logger.info(f"Successfully created voice clone {model.id} for user {current_user.email}")
        return current_user
        
    except Exception as e:
        logger.error(f"Voice Cloning Error for {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Fehler beim Stimmen-Klonen: {str(e)}")

@router.delete("/me/voices/{voice_id}", response_model=UserResponse)
def delete_custom_voice(
    voice_id: str,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    from app.models import UserVoice
    voice = session.get(UserVoice, voice_id)
    if not voice or voice.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Stimme nicht gefunden")
        
    session.delete(voice)
    session.commit()
    session.refresh(current_user)
    return current_user

from pydantic import BaseModel
class UpdateVoiceRequest(BaseModel):
    name: str | None = None
    is_public: bool | None = None

@router.put("/me/voices/{voice_id}", response_model=UserResponse)
def update_custom_voice(
    voice_id: str,
    data: UpdateVoiceRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    from app.models import UserVoice
    voice = session.get(UserVoice, voice_id)
    if not voice or voice.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Stimme nicht gefunden")
        
    if data.name is not None:
        voice.name = data.name
    if data.is_public is not None:
        voice.is_public = data.is_public
        
    session.add(voice)
    session.commit()
    session.refresh(current_user)
    return current_user


# ──────────────────────────────────
# Alexa Account Linking (OAuth2)
# ──────────────────────────────────

@router.get("/alexa/authorize", response_class=HTMLResponse)
async def alexa_authorize(
    request: Request,
    client_id: str,
    redirect_uri: str,
    state: str,
    response_type: str = "code",
    scope: str | None = None
):
    """Serve the login page for Alexa Account Linking."""
    q_client_id = html.escape(client_id)
    q_redirect_uri = html.escape(redirect_uri)
    q_state = html.escape(state)
    
    return f"""
    <html>
        <head>
            <title>Storyja - Alexa Verknüpfung</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: -apple-system, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #0f172a; color: white; margin: 0; }}
                .card {{ background: #1e293b; padding: 2.5rem; border-radius: 16px; width: 320px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); border: 1px solid #334155; }}
                .logo {{ text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 20px; color: #38bdf8; }}
                input {{ width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px; border: 1px solid #334155; background: #0f172a; color: white; box-sizing: border-box; }}
                button {{ width: 100%; padding: 14px; border: none; border-radius: 8px; background: #38bdf8; color: #0f172a; font-weight: bold; cursor: pointer; margin-top: 10px; }}
                p {{ font-size: 14px; color: #94a3b8; text-align: center; line-height: 1.4; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="logo">Storyja</div>
                <p>Logge dich ein, um dein Storyja-Konto mit Alexa zu verbinden.</p>
                <form action="/api/auth/alexa/authorize" method="post">
                    <input type="hidden" name="client_id" value="{q_client_id}">
                    <input type="hidden" name="redirect_uri" value="{q_redirect_uri}">
                    <input type="hidden" name="state" value="{q_state}">
                    <input type="email" name="email" placeholder="E-Mail" required>
                    <input type="password" name="password" placeholder="Passwort" required>
                    <button type="submit">Einloggen & Verknüpfen</button>
                </form>
            </div>
        </body>
    </html>
    """

@router.post("/alexa/authorize")
async def alexa_authorize_post(
    email: str = Form(...),
    password: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    state: str = Form(...),
    session: Session = Depends(get_session)
):
    """Handle the login form submission for Alexa."""
    user = session.exec(select(User).where(User.email == email.lower())).first()
    if not user or not verify_password(password, user.hashed_password):
         return HTMLResponse(content="<h2>Fehler</h2><p>Falsche E-Mail oder Passwort. Bitte versuche es erneut.</p>", status_code=401)
    
    # Create the authorization code
    code = create_alexa_auth_code(user.id)
    
    # Robustly build redirect URL (handling existing query params)
    parts = list(urllib.parse.urlparse(redirect_uri))
    query_params = dict(urllib.parse.parse_qsl(parts[4]))
    query_params.update({"code": code, "state": state})
    parts[4] = urllib.parse.urlencode(query_params)
    redirect_url = urllib.parse.urlunparse(parts)
    
    logger.info(f"ALEXA AUTH SUCCESS: Redirecting user {user.email} back to Alexa at {redirect_url}")
    return RedirectResponse(url=redirect_url, status_code=303)

@router.post("/alexa/token")
async def alexa_token(
    request: Request,
    grant_type: str = Form(...),
    code: str | None = Form(None),
    refresh_token: str | None = Form(None),
    client_id: str | None = Form(None),
    client_secret: str | None = Form(None),
    session: Session = Depends(get_session)
):
    """Exchange the auth code for a long-lived access token."""
    
    # Support HTTP Basic Auth (Recommended by Alexa Console)
    auth_header = request.headers.get("Authorization")
    logger.info(f"ALEXA TOKEN REQUEST: grant_type={grant_type}, code={code[:8] if code else 'None'}, AuthHeader={'Present' if auth_header else 'None'}")
    
    if auth_header and auth_header.startswith("Basic "):
        try:
            import base64
            encoded_creds = auth_header.split(" ")[1]
            decoded_creds = base64.b64decode(encoded_creds).decode("utf-8")
            if ":" in decoded_creds:
                h_client_id, h_client_secret = decoded_creds.split(":", 1)
                client_id = h_client_id
                client_secret = h_client_secret
                logger.info(f"ALEXA TOKEN: Decoded ClientID from Basic Auth: {client_id}")
        except Exception as e:
            logger.error(f"ALEXA TOKEN: Failed to decode Basic Auth: {e}")

    logger.info(f"ALEXA TOKEN FINAL: ClientID={client_id}")

    if grant_type == "authorization_code":
        user_id = verify_alexa_auth_code(code)
        if not user_id:
            logger.warning(f"ALEXA TOKEN: Invalid code {code[:8] if code else 'None'}")
            raise HTTPException(status_code=400, detail="Ungültiger Authorization Code")
        
        user = session.get(User, user_id)
        if not user:
            logger.warning(f"ALEXA TOKEN: User {user_id} not found")
            raise HTTPException(status_code=404, detail="Nutzer nicht gefunden")
            
        # Create a long-lived token for Alexa
        token_expires = timedelta(days=365) # Long lived
        access_token = create_access_token(data={"sub": str(user.id), "scope": "alexa"}, expires_delta=token_expires)
        
        logger.info(f"ALEXA TOKEN SUCCESS: Issued token for {user.email}")
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "dummy_refresh_token"
        }

    raise HTTPException(status_code=400, detail="Nicht unterstützter Grant Type")
