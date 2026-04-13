from fastapi import APIRouter, Depends, HTTPException
from app.models import User, StoryMetaResponse
from app.auth_utils import get_current_active_user
from app.services.store import store

router = APIRouter(prefix="/api/playlist", tags=["playlist"])

@router.get("", response_model=list[StoryMetaResponse])
async def list_playlist(current_user: User = Depends(get_current_active_user)):
    """List all stories in the user's Alexa playlist."""
    if not current_user.alexa_user_id:
        raise HTTPException(
            status_code=403, 
            detail="Playlist ist nur für Nutzer mit verknüpftem Alexa Skill verfügbar."
        )
    return store.get_playlist(current_user.id)

@router.post("/add/{story_id}")
async def add_story(story_id: str, current_user: User = Depends(get_current_active_user)):
    """Add a story to the end of the playlist."""
    if not current_user.alexa_user_id:
        raise HTTPException(
            status_code=403, 
            detail="Playlist ist nur für Nutzer mit verknüpftem Alexa Skill verfügbar."
        )
    
    success = store.add_to_playlist(current_user.id, story_id)
    if not success:
        raise HTTPException(
            status_code=400, 
            detail="Geschichte konnte nicht zur Playlist hinzugefügt werden (vielleicht fehlt die Vertonung?)."
        )
    return {"status": "success", "message": "Story zur Playlist hinzugefügt."}

@router.delete("/{story_id}")
async def remove_story(story_id: str, current_user: User = Depends(get_current_active_user)):
    """Remove a specific story from the playlist."""
    success = store.remove_from_playlist(current_user.id, story_id)
    if not success:
        raise HTTPException(status_code=404, detail="Geschichte nicht in Playlist gefunden.")
    return {"status": "success", "message": "Story aus Playlist entfernt."}

@router.delete("")
async def clear_playlist(current_user: User = Depends(get_current_active_user)):
    """Clear the entire playlist."""
    store.clear_playlist(current_user.id)
    return {"status": "success", "message": "Playlist geleert."}
