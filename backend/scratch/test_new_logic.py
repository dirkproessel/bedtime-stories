import asyncio
import os
import sys
import json
from pydantic import BaseModel, Field

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.services.text_generator import generate_text
from app.services.rate_limiter import rate_limiter
from app.services.store import store
from app.config import settings

class TaggedChapter(BaseModel):
    title: str
    text: str = Field(description="Der Text des Kapitels mit eingefügten <|speaker:X|> Tags vor jedem Sprecherwechsel.")

class SpeakerAnalysis(BaseModel):
    all_characters_in_story: list[str] = Field(description="Liste aller Charaktere, die in der Geschichte vorkommen oder erwähnt werden.")
    actually_speaking_characters: list[str] = Field(description="Liste der Charaktere, die tatsächlich wörtliche Rede sprechen (laut im Dialog).")
    silent_characters_to_exclude: list[str] = Field(description="Charaktere, die stumm sind, nur erwähnt werden oder Geräusche machen, aber KEIN Wort sprechen (müssen von speaker:0 gelesen werden).")

class SpeakerMappingItem(BaseModel):
    speaker_id: int = Field(description="Die ID für den Sprecher (0 für Erzähler, 1, 2, 3 etc. für die sprechenden Charaktere).")
    character_name: str = Field(description="Name des Charakters.")

class TaggedStoryResponse(BaseModel):
    analysis: SpeakerAnalysis
    speaker_mapping: list[SpeakerMappingItem]
    chapters: list[TaggedChapter]

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

async def new_inject_speaker_tags_to_story(story_data: dict, supports_emotions: bool = False) -> dict:
    input_json = json.dumps(story_data, ensure_ascii=False, indent=2)
    
    prompt = f"""Du bist ein Lektor und Hörspiel-Produzent. Deine Aufgabe ist es, eine bestehende Geschichte so aufzubereiten, dass sie mit mehreren Stimmen (S2-Pro Format) vertont werden kann.
Dazu musst du den Erzähler und alle tatsächlich sprechenden Charaktere identifizieren, ihnen feste Sprecher-IDs zuweisen und die entsprechenden S2-Pro Sprecher-Tags (<|speaker:X|>) in den Text einfügen.

REGELN:
1. NARRATOR & ICH-PERSPEKTIVE (<|speaker:0|>):
   - `<|speaker:0|>` ist IMMER der Erzähler (Narrator).
   - WICHTIG: Wenn die Geschichte aus der Ich-Perspektive erzählt wird (z.B. "Ich stehe in der Küche...", "sage ich laut zu mir selbst"), gehört die direkte Rede der Hauptfigur ("Ich") ebenfalls zu `<|speaker:0|>`. Sie darf NIEMALS eine eigene Sprecher-ID wie `<|speaker:1|>` erhalten! Die Hauptfigur und der Erzähler sind dieselbe physische Person und Stimme, daher müssen beide `<|speaker:0|>` nutzen.

2. SPRECHENDE CHARAKTERE:
   - `<|speaker:1|>`, `<|speaker:2|>`, `<|speaker:3|>` etc. sind die IDs für die anderen Charaktere, die in der Geschichte TATSÄCHLICH sprechen.
   - Weise jedem Charakter eine feste, konsistente ID über alle Kapitel hinweg zu.

3. SPRECHER-TAGS EINFÜGEN:
   - Füge den jeweiligen Sprecher-Tag IMMER direkt vor dem Textabsatz oder dem gesprochenen Satz ein.
   - Ändere den Sprecher-Tag nur, wenn ein anderer Charakter spricht oder der Erzähler fortfährt.
   - Jede wörtliche Rede MUSS mit dem passenden Sprecher-Tag versehen werden.

4. TEXT NICHT VERÄNDERN:
   - Ändere den eigentlichen Text der Geschichte (Wortlaut, Zeichensetzung, Handlung) NICHT. Füge nur die Sprecher-Tags ein.

5. EMOTIONEN (OPTIONAL):
   - Falls emotions_enabled True ist, kannst du optionale emotionale Ausdrücke in eckigen Klammern (z.B. [whispering], [laughing], [excited], [sad], [sighing]) direkt nach dem Sprecher-Tag einfügen. Verwende diese sehr sparsam (maximal 1-2 pro Kapitel).

6. ABSÄTZE & ZEILENUMBRÜCHE (SEHR WICHTIG):
   - Behalte alle Zeilenumbrüche und Absätze (insbesondere doppelte Zeilenumbrüche zwischen Absätzen) exakt bei.
   - Die Struktur der Absätze darf keinesfalls zusammengezogen oder in eine einzelne Zeile konvertiert werden! Jeder Absatz muss durch einen doppelten Zeilenumbruch (\\n\\n) getrennt bleiben.

7. NUR TATSÄCHLICH SPRECHENDE ROLLEN (STRIKTE AUSSCHLÜSSE):
   - Weise Sprecher-Tags (wie <|speaker:1|>, <|speaker:2|>) NUR Absätzen oder Sätzen zu, in denen ein Charakter tatsächlich wörtliche Rede spricht (oder laut im Dialog spricht).
   - Stumme Charaktere (die anwesend sind, beschrieben werden, aber kein Wort sprechen), erwähnte Personen, Gegenstände, Tiere oder Roboter (die Geräusche machen, aber nicht sprechen) dürfen KEINEN eigenen Sprecher-Tag erhalten!
   - Jegliche Beschreibungen, Handlungen oder Geräusche dieser stummen/nicht sprechenden Entitäten müssen vom Erzähler (<|speaker:0|>) vorgelesen werden.
   - Beispiel: Wenn "Mama" in die Küche kommt und keinen Ton herausbringt, spricht sie nicht. Der Absatz wird komplett vom Erzähler (<|speaker:0|>) gelesen.
   - Beispiel: Wenn "Staubi" fiept, spricht er nicht. Der Absatz wird vom Erzähler (<|speaker:0|>) gelesen.

emotions_enabled: {str(supports_emotions)}

GESCHICHTE (JSON-Format):
{input_json}
"""
    await rate_limiter.wait_for_capacity("text")
    text_model = store.get_system_setting("gemini_text_model", settings.GEMINI_TEXT_MODEL)
    print(f"Generating with model: {text_model}")
    
    response_text = await generate_text(
        prompt=prompt,
        model=text_model,
        temperature=0.1, # lower temp for higher reliability
        max_tokens=8192,
        response_mime_type="application/json",
        response_schema=TaggedStoryResponse
    )
    rate_limiter.increment_daily_quota("text")
    
    data = json.loads(response_text.strip())
    return data

async def main():
    print("--- Running new tagging logic with Pydantic Schema and detailed rules ---")
    result = await new_inject_speaker_tags_to_story(mock_story, supports_emotions=True)
    
    print("\n--- 1. Analysis Output ---")
    print(json.dumps(result["analysis"], indent=2, ensure_ascii=False))
    
    print("\n--- 2. Speaker Mapping ---")
    print(json.dumps(result["speaker_mapping"], indent=2, ensure_ascii=False))
    
    print("\n--- 3. Tagged Chapters ---")
    for idx, chap in enumerate(result["chapters"]):
        print(f"\n[Chapter {idx + 1}]:")
        print(chap["text"])

if __name__ == "__main__":
    asyncio.run(main())
