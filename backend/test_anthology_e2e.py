import asyncio
import json
import uuid
from pathlib import Path
from sqlmodel import Session, select

from app.database import engine, create_db_and_tables
from app.config import settings
from app.models import User, StoryMeta, BookProject, BookChapter, BookAnthologyCreate
from app.routers.pro import api_create_anthology_from_stories, SuggestAnthologyMetadataRequest, api_suggest_anthology_metadata
from app.services.book_export_service import generate_book_epub, generate_book_pdf, generate_kdp_metadata


async def run_test():
    print("=== STARTING ANTHOLOGY E2E TEST ===")
    create_db_and_tables()

    # 1. Setup Admin User
    with Session(engine) as session:
        admin_user = session.exec(select(User).where(User.email == "admin@test.com")).first()
        if not admin_user:
            admin_user = User(
                id="test-admin-id",
                email="admin@test.com",
                hashed_password="hash",
                is_admin=True,
                username="Dirk Proessel"
            )
            session.add(admin_user)
            session.commit()
            session.refresh(admin_user)
        print(f"Admin User: {admin_user.email} (ID: {admin_user.id})")

    # 2. Create 3 Sample Short Stories
    sample_stories = [
        {
            "id": f"story_test_{uuid.uuid4().hex[:6]}",
            "title": "Schatten der Leidenschaft",
            "genre": "Erotik",
            "style": "Anaïs Nin",
            "description": "Eine geheimnisvolle Begegnung in einem verregneten Pariser Café entfacht eine verbotene Affäre.",
            "chapters": [
                {"title": "Teil 1: Der Fremde im Regen", "text": "Der Regen trommelte sanft gegen die Fensterscheiben des kleinen Cafés am Montmartre. Sie saß allein am Tisch, als ein Blick alles veränderte."},
                {"title": "Teil 2: Das Flüstern der Nacht", "text": "In den Schatten der Pariser Gassen verschmolzen Verlangen und Sehnsucht zu einem unvergesslichen Abenteuer."}
            ]
        },
        {
            "id": f"story_test_{uuid.uuid4().hex[:6]}",
            "title": "Berührung im Mondlicht",
            "genre": "Erotik",
            "style": "Anaïs Nin",
            "description": "Ein nächtlicher Spaziergang am Meer führt zu einer überraschenden, sinnlichen Enthüllung.",
            "chapters": [
                {"title": "Die Wellen des Begehrens", "text": "Die Meeresbrise strich kühl über ihre Haut, während seine Hände warm und fordernd über ihren Rücken glitten."}
            ]
        },
        {
            "id": f"story_test_{uuid.uuid4().hex[:6]}",
            "title": "Das verbotene Zimmer",
            "genre": "Erotik",
            "style": "Anaïs Nin",
            "description": "Hinter einer schweren Holztür verbirgt sich ein Ort voller Sinnlichkeit und Geheimnisse.",
            "chapters": [
                {"title": "Der goldene Schlüssel", "text": "Mit zitternden Fingern drehte sie den Schlüssel im Schloss. Das Zimmer war in sanftes Kerzenlicht getaucht."}
            ]
        }
    ]

    story_ids = []
    with Session(engine) as session:
        for s in sample_stories:
            story_meta = StoryMeta(
                id=s["id"],
                title=s["title"],
                description=s["description"],
                prompt=s["description"],
                genre=s["genre"],
                style=s["style"],
                voice_key="seraphina",
                chapter_count=len(s["chapters"]),
                status="done",
                user_id=admin_user.id
            )
            session.add(story_meta)
            story_ids.append(s["id"])

            # Write story.json to settings.AUDIO_OUTPUT_DIR
            story_dir = settings.AUDIO_OUTPUT_DIR / s["id"]
            story_dir.mkdir(parents=True, exist_ok=True)
            story_file = story_dir / "story.json"
            story_file.write_text(json.dumps({
                "title": s["title"],
                "synopsis": s["description"],
                "chapters": s["chapters"]
            }, ensure_ascii=False, indent=2), encoding="utf-8")
        session.commit()

    print(f"Created {len(story_ids)} test stories on disk and in database.")

    # 3. Test Metadata Suggestion API
    print("\n--- Testing Suggest Anthology Metadata ---")
    suggest_req = SuggestAnthologyMetadataRequest(
        story_ids=story_ids,
        genre="Erotik",
        style="Anaïs Nin",
        author="Dirk Proessel"
    )
    suggest_res = await api_suggest_anthology_metadata(suggest_req, current_user=admin_user)
    print(f"Suggested Title: {suggest_res.get('title')}")
    print(f"Suggested Subtitle: {suggest_res.get('subtitle')}")
    print(f"Suggested Blurb: {suggest_res.get('blurb')[:120]}...")
    print(f"Suggested Cover Prompt: {suggest_res.get('cover_prompt')[:120]}...")
    assert "title" in suggest_res, "Title should be suggested"

    # 4. Test Create Anthology from Stories API
    print("\n--- Testing Create Anthology Book ---")
    anthology_req = BookAnthologyCreate(
        title="3 Sinnliche Nächte: Erotischer Sammelband",
        subtitle="Verführerische Kurzgeschichten",
        author="Dirk Proessel",
        genre="Erotik",
        style="Anaïs Nin",
        language="de",
        story_ids=story_ids,
        auto_generate_blurb=True
    )
    created_book = await api_create_anthology_from_stories(anthology_req, current_user=admin_user)
    print(f"Created Anthology Book ID: {created_book.id}")
    print(f"Title: {created_book.title}")
    print(f"Is Anthology: {created_book.is_anthology}")
    print(f"Chapters Count: {len(created_book.chapters)}")
    
    assert created_book.is_anthology is True, "Project must be marked as anthology"
    assert len(created_book.chapters) == 3, "Project must contain exactly 3 chapters"
    assert created_book.chapters[0].title == "Schatten der Leidenschaft"
    assert created_book.chapters[0].status == "done"
    assert "Der Regen trommelte" in created_book.chapters[0].content
    print("All chapters successfully imported with full story text!")

    # 5. Test EPUB Generation
    print("\n--- Testing EPUB Export for Anthology ---")
    with Session(engine) as session:
        db_project = session.get(BookProject, created_book.id)
        db_chapters = session.exec(
            select(BookChapter)
            .where(BookChapter.book_project_id == created_book.id)
            .order_by(BookChapter.chapter_number)
        ).all()
        
    epub_out = settings.AUDIO_OUTPUT_DIR / "books" / f"test_anthology_{created_book.id}.epub"
    await generate_book_epub(db_project, db_chapters, epub_out)
    assert epub_out.exists(), "EPUB file must exist"
    print(f"EPUB exported successfully ({epub_out.stat().st_size} bytes): {epub_out}")

    # 6. Test PDF Generation
    print("\n--- Testing PDF Export for Anthology ---")
    pdf_out = settings.AUDIO_OUTPUT_DIR / "books" / f"test_anthology_{created_book.id}.pdf"
    generate_book_pdf(db_project, db_chapters, pdf_out)
    assert pdf_out.exists(), "PDF file must exist"
    print(f"PDF exported successfully ({pdf_out.stat().st_size} bytes): {pdf_out}")

    # 7. Test Amazon KDP Metadata Generation
    print("\n--- Testing Amazon KDP Metadata for Anthology ---")
    kdp_meta = await generate_kdp_metadata(db_project, db_chapters, marketplace="amazon.de")
    print(f"KDP Target Audience: {kdp_meta.get('target_audience')}")
    print(f"KDP Keywords: {kdp_meta.get('search_keywords')}")
    print(f"KDP Categories: {[c.get('path') for c in kdp_meta.get('kdp_categories', [])]}")
    print(f"KDP Pricing: {kdp_meta.get('pricing_recommendation')}")
    assert len(kdp_meta.get("search_keywords", [])) == 7, "Should have 7 KDP keywords"
    assert len(kdp_meta.get("kdp_categories", [])) == 3, "Should have 3 KDP categories"

    print("\n=== ALL ANTHOLOGY E2E TESTS PASSED SUCCESSFULLY! ===")


if __name__ == "__main__":
    asyncio.run(run_test())
