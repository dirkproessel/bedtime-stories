import asyncio
import os
import sys
import json

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.services.story_generator import inject_speaker_tags_to_story, extract_speakers_from_tagged_story

mock_story = {
    "title": "Das Kuchenabenteuer und die stumme Mama",
    "synopsis": "Ein Backabenteuer in der Küche mit Mia und Leo, das durch einen chaotischen Staubi und eine sprachlose Mama eine unerwartete Wendung nimmt, gefolgt von einer Zeichenstunde bei Herrn Kunze.",
    "chapters": [
        {
            "title": "Kapitel 1: Der Mehlsturm",
            "text": "Ich stehe in der Küche und backe einen herrlichen Kuchen. „Der Teig riecht schon so lecker!“, sage ich laut zu mir selbst.\n\nPlötzlich fiept Staubi, der kleine Saugroboter, wild und saust im Zickzack um meine Beine. Chantal wird das bestimmt lustig finden, wenn ich ihr morgen in der Schule davon erzähle.\n\nDa klingelt mein Tablet auf der Arbeitsplatte. Ich tippe auf den Bildschirm.\n\n„Hallo!“, ruft meine Freundin Mia auf dem Bildschirm. „Was backst du da Feines?“\n\n„Ich backe einen Schokoladenkuchen!“, antworte ich stolz.\n\nMein kleiner Bruder Leo kommt mit seinem T-Rex-Spielzeug ins Zimmer gestürmt. „Roar! Der T-Rex will auch ein großes Stück Kuchen!“, ruft Leo und fuchtelt mit dem Plastiksaurier vor der Kamera herum.\n\nDa öffnet sich die Küchentür und Mama kommt herein. Sie sieht das Chaos aus Mehl auf dem Boden, dem wild gewordenen Staubi und Leo, der laut schreiend herumspringt. Sie bringt vor Schock keinen einzigen Ton heraus, hält sich die Hände vor den Mund und starrt uns einfach nur fassungslos an."
        },
        {
            "title": "Kapitel 2: Die Kunst der Aula",
            "text": "Später am Nachmittag sitzen wir alle in der Aula für den Zeichenkurs.\n\nHerr Kunze, der Kunstlehrer, steht an der großen Tafel und zeichnet einen Kreis. „Heute malen wir stillstehende Objekte, zum Beispiel einen frisch gebackenen Kuchen“, erklärt Herr Kunze mit ruhiger Stimme.\n\n„Aber Herr Kunze!“, meldet sich Mia zu Wort. „Wir haben doch vorhin schon einen echten Kuchen gebacken, der viel besser aussieht!“\n\nHerr Kunze schmunzelt und rückt seine Brille zurecht. „Das ist wunderbar, Mia, aber heute üben wir das Schattieren auf Papier.“\n\nLeo flitzt durch die Aula und ruft laut: „Und können wir auch meinen T-Rex schattieren? Bitte, Herr Kunze!“"
        }
    ]
}

async def main():
    print("--- 1. Injecting speaker tags (using current prompt) ---")
    tagged_story = await inject_speaker_tags_to_story(mock_story, supports_emotions=True)
    print("\nTagged Story chapters:")
    for idx, chap in enumerate(tagged_story.get("chapters", [])):
        print(f"\n[Chapter {idx + 1}]:")
        print(chap.get("text"))
        
    print("\n--- 2. Extracting speakers from tagged story ---")
    speakers = await extract_speakers_from_tagged_story(tagged_story)
    print("\nExtracted Speakers:")
    print(json.dumps(speakers, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
