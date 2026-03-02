"""
Podcast RSS feed generator for bedtime stories.
"""

from datetime import datetime, timezone
from pathlib import Path
from feedgen.feed import FeedGenerator


def generate_rss_feed(
    stories: list,
    base_url: str,
    image_url: str | None = None,
    email: str | None = None,
) -> str:
    """
    Generate a podcast-compatible RSS feed XML.

    Args:
        stories: List of story dicts or StoryMeta Pydantic models.
        base_url: Base URL where audio files are served

    Returns:
        The RSS XML string
    """
    fg = FeedGenerator()
    fg.load_extension("podcast")

    # Feed metadata
    fg.title("Kurzgeschichten-Labor")
    fg.link(href=base_url, rel="alternate")
    desc = "Hier werden Geschichten nicht geschrieben, sie werden gestanzt. Das Labor für anspruchsvolle Literatur kombiniert die DNA von vielen Meister-Autoren. Präzise geformt, individuell veredelt und garantiert ohne Einheitsbrei."
    fg.description(desc)
    fg.language("de-DE")
    
    fg.podcast.itunes_category("Fiction", "Short Stories")
    fg.podcast.itunes_category("Kids & Family", "Stories for Kids")
    
    fg.podcast.itunes_author("Stanzwerk")
    fg.podcast.itunes_explicit("no")
    fg.podcast.itunes_summary(desc)

    if image_url:
        fg.logo(image_url)
        fg.podcast.itunes_image(image_url)

    if email:
        fg.podcast.itunes_owner(name="Stanzwerk", email=email)

    # Add episodes (newest first)
    for s in stories:
        # Normalize to dict if it's a Pydantic model
        story = s.model_dump(mode="json") if hasattr(s, "model_dump") else s
        
        fe = fg.add_entry()
        fe.id(f"{base_url}/audio/{story['id']}")
        fe.title(story["title"])
        fe.description(story.get("description", ""))

        audio_url = f"{base_url}/api/stories/{story['id']}/audio"
        fe.enclosure(audio_url, 0, "audio/mpeg")
        
        # Add episode-specific image if available
        # Note: Feedgen requires setting the image directly via the iTunes extension at the item level
        if story.get("image_url"):
            fe.podcast.itunes_image(story["image_url"])
        else:
            # Fallback to general podcast cover
            fe.podcast.itunes_image(f"{base_url}/api/podcast-cover.png")

        fe.podcast.itunes_duration(
            _seconds_to_hms(story.get("duration_seconds", 0))
        )

        created = story.get("created_at")
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        fe.published(created)

    return fg.rss_str(pretty=True).decode("utf-8")


def _seconds_to_hms(seconds: float | None) -> str:
    """Convert seconds to HH:MM:SS format."""
    if seconds is None:
        return "00:00"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
