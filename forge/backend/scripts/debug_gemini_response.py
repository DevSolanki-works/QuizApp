"""
debug_gemini_response.py — ONE-OFF diagnostic. Calls Gemini directly with
the exact same prompt/config as generate_questions(), but prints the raw
response BEFORE any parsing, so we can see exactly what came back and why
it's failing — truncation (finish_reason=MAX_TOKENS) vs a formatting/
preamble issue (finish_reason=STOP but stray text around the JSON).

Does not touch ai.py, does not write to the question bank file.

Run:
    GEMINI_MODEL=gemini-2.5-pro python scripts/debug_gemini_response.py
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.services.ai import QUIZ_PROMPT
import google.generativeai as genai

genai.configure(api_key=settings.GEMINI_API_KEY)


async def main():
    topic = os.environ.get("TEST_TOPIC", "Movies")
    prompt = QUIZ_PROMPT.format(topic=topic)
    model = genai.GenerativeModel(settings.GEMINI_MODEL)

    print(f"Model: {settings.GEMINI_MODEL}")
    print(f"Topic: {topic}\n")

    response = await asyncio.to_thread(
        model.generate_content,
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.4,
            max_output_tokens=4096,
        ),
    )

    candidate = response.candidates[0]
    print(f"finish_reason: {candidate.finish_reason}")
    print(f"raw text length: {len(response.text)} characters\n")
    print("--- FIRST 300 CHARS ---")
    print(response.text[:300])
    print("\n--- LAST 300 CHARS ---")
    print(response.text[-300:])


if __name__ == "__main__":
    asyncio.run(main())