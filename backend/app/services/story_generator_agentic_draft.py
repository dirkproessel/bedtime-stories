"""
Agentic Story Generation Service using the Antigravity Library.
Uses a multi-agent workflow: Planner -> Writer -> Editor.
"""

import asyncio
import json
import logging
from pathlib import Path
import antigravity as ag
from antigravity import ModelConfig
from app.config import settings
from app.services.story_generator import STANZWERK_BIBLIOTHEK, GENRES_BIBLIOTHEK, generate_modular_prompt

logger = logging.getLogger(__name__)

# Primary Model for Storytelling
STORY_MODEL = "gemini-2.0-pro-exp" # Or gemini-3-pro-preview if available

class StoryAgent:
    def __init__(self, role: str, instruction: str):
        self.role = role
        self.instruction = instruction
        self.model = ag.TextGenerationModel(
            config=ModelConfig(
                model_name=STORY_MODEL,
                system_instruction=instruction,
                safety_settings=[ag.SafetySetting(category='HATE_SPEECH', threshold='BLOCK_NONE')]
            )
        )

    async def run(self, prompt: str, **kwargs):
        # Emulating the agentic execution
        response = await asyncio.to_thread(self.model.generate_text, prompt=prompt, **kwargs)
        return response.text

async def generate_agentic_story(
    prompt: str,
    genre: str = "Realismus",
    style: str = "Douglas Adams",
    target_minutes: int = 20,
    on_progress: callable = None
) -> dict:
    """
    The Agentic Pipeline:
    1. PLANNER: Creates a story bible (Plot, Characters, Tone).
    2. WRITER: Writes chapters iteratively.
    3. EDITOR: Reviews each chapter and requests adjustments if needed.
    """
    
    style_info = generate_modular_prompt(style)
    genre_data = GENRES_BIBLIOTHEK.get(genre, GENRES_BIBLIOTHEK["Fantasy"])
    
    # --- PHASE 1: PLANNING ---
    if on_progress: await on_progress("planning", "Agent 'Planner' entwirft die Story-Bibel...", 10)
    
    planner = StoryAgent(
        role="Planner",
        instruction="Du bist ein erfahrener Dramaturg. Plane eine fesselnde Kurzgeschichte basierend auf dem Nutzerwunsch, dem Genre und dem Autorenstil."
    )
    
    planning_prompt = f"Genre: {genre}. Stil: {style_info}. Wunsch: {prompt}. Plane {target_minutes} Minuten Geschichte in {target_minutes//5} Kapiteln."
    story_bible_raw = await planner.run(planning_prompt)
    # (In reality, we would parse JSON here)
    
    # --- PHASE 2 & 3: WRITING & EDITING ---
    writer = StoryAgent(
        role="Writer",
        instruction=f"Du bist ein preisgekrönter Autor im Stil von {style}. Nutze 'Show, don't tell'."
    )
    
    editor = StoryAgent(
        role="Editor",
        instruction="Du bist ein strenger Lektor. Prüfe auf Pacing, Stilbrüche und 'Tell statt Show'. Gib konkrete Kritik oder gib das Kapitel frei."
    )
    
    chapters = []
    num_chapters = target_minutes // 5
    
    for i in range(num_chapters):
        if on_progress: 
            await on_progress("writing", f"Agent 'Writer' schreibt Kapitel {i+1}...", 20 + i*20)
            
        chapter_text = await writer.run(f"Schreibe Kapitel {i+1} basierend auf der Bibel: {story_bible_raw}")
        
        # Iterative Review
        if on_progress: await on_progress("editing", f"Agent 'Editor' prüft Kapitel {i+1}...", 25 + i*20)
        review = await editor.run(f"Prüfe dieses Kapitel: {chapter_text}")
        
        if "REVISE" in review.upper():
            # Autonomous Self-Correction
            chapter_text = await writer.run(f"Überarbeite Kapitel {i+1} basierend auf dieser Kritik: {review}")
            
        chapters.append({"title": f"Kapitel {i+1}", "text": chapter_text})

    return {
        "title": "Der automatische Titel",
        "synopsis": "Die Zusammenfassung der Agenten",
        "chapters": chapters
    }
