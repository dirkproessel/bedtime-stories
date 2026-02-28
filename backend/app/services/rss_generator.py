"""
Podcast RSS feed generator for bedtime stories.
"""

from datetime import datetime, timezone
from pathlib import Path
from feedgen.feed import FeedGenerator


def generate_rss_feed(
    stories: list[dict],
    base_url: str,
    output_path: Path,
    image_url: str | None = None,
    email: str | None = None,
) -> Path:
    """
    Generate a podcast-compatible RSS feed.

    Args:
        stories: List of story dicts with keys:
            - id, title, description, duration_seconds, filename, created_at
        base_url: Base URL where audio files are served
        output_path: Where to write the RSS XML file

    Returns:
        Path to the generated RSS file
    """
    fg = FeedGenerator()
    fg.load_extension("podcast")

    # Feed metadata
    fg.title("Abenteuer aus der Hosentasche")
    fg.link(href=base_url, rel="alternate")
    fg.description("Alles, was zu groß für den Alltag ist, passt perfekt in diese Hosentasche. Die Sektion Unfug liefert echte Abenteuer zwischen Küchentresen und Sternenhimmel: ohne Kitsch, dafür als idealer Abschluss für den Tag und eine himmlisch gute Nacht.")
    fg.language("de-DE")
    fg.podcast.itunes_category("Kids & Family", "Stories for Kids")
    fg.podcast.itunes_author("Sektion Unfug")
    fg.podcast.itunes_explicit("no")
    fg.podcast.itunes_summary(
        "Alles, was zu groß für den Alltag ist, passt perfekt in diese Hosentasche. Die Sektion Unfug liefert echte Abenteuer zwischen Küchentresen und Sternenhimmel: ohne Kitsch, dafür als idealer Abschluss für den Tag und eine himmlisch gute Nacht."
    )

    if image_url:
        fg.logo(image_url)
        fg.podcast.itunes_image(image_url)

    if email:
        fg.podcast.itunes_owner(name="Sektion Unfug", email=email)

    # Add episodes (newest first)
    for story in sorted(stories, key=lambda s: s["created_at"], reverse=True):
        fe = fg.add_entry()
        fe.id(f"{base_url}/audio/{story['id']}")
        fe.title(story["title"])
        fe.description(story.get("description", ""))

        audio_url = f"{base_url}/api/stories/{story['id']}/audio"
        fe.enclosure(audio_url, 0, "audio/mpeg")

        fe.podcast.itunes_duration(
            _seconds_to_hms(story.get("duration_seconds", 0))
        )

        created = story.get("created_at")
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        fe.published(created)

    # Write RSS file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fg.rss_file(str(output_path), pretty=True)
    return output_path


def _seconds_to_hms(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
