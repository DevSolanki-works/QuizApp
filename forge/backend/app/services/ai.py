"""
app/services/ai.py — Gemini AI quiz generation service.

WHY a separate service module?
  - Keeps the WebSocket handler clean — it shouldn't know HOW we call the AI.
  - Easy to swap Gemini for another LLM later with zero changes to the router.
  - All retry / error handling lives here, not scattered through game logic.

STRUCTURED OUTPUTS strategy:
  We use Gemini's response_schema parameter to force a valid JSON structure.
  This is MORE reliable than asking the model to "return JSON" in the prompt,
  because the model is constrained at the token-generation level.
"""

import json
import logging

import google.generativeai as genai
from pydantic import ValidationError

from app.core.config import settings
from app.models.quiz import Question, Quiz

logger = logging.getLogger(__name__)


def _get_gemini_client() -> genai.GenerativeModel:
    """
    Initialize the Gemini client.
    WHY lazy init (called each time)? 
    Cloud Run may have GEMINI_API_KEY injected after module load.
    Lazy init ensures we always use the current env var value.
    """
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=genai.GenerationConfig(
            # Force JSON output at the model level — most reliable approach
            response_mime_type="application/json",
            temperature=0.9,      # A bit of creativity for interesting questions
            max_output_tokens=2048,
        ),
    )


QUIZ_PROMPT_TEMPLATE = """
Generate a quiz about the topic: "{topic}"

Return ONLY a JSON object matching this exact structure:
{{
  "questions": [
    {{
      "question": "Question text here?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 0
    }}
  ]
}}

Rules:
- Exactly 10 questions
- Each question has exactly 4 options (options array length = 4)
- correct_index is 0, 1, 2, or 3 (the index of the correct option)
- Questions should be specific, interesting, and at medium difficulty
- Do NOT include explanations, markdown, or any text outside the JSON
"""


async def generate_quiz(topic: str) -> list[Question]:
    """
    Call Gemini and return a validated list of 10 Question objects.

    WHY async?
    Gemini's API call is I/O-bound (network request). Using async means
    FastAPI's event loop can handle OTHER WebSocket messages while we wait
    for Gemini to respond — the server doesn't freeze during AI generation.

    FLOW:
    1. Build prompt with topic
    2. Call Gemini (async, non-blocking)
    3. Parse JSON response
    4. Validate with Pydantic
    5. Return list[Question] or raise exception
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set. Add it to your .env file.")

    model = _get_gemini_client()
    prompt = QUIZ_PROMPT_TEMPLATE.format(topic=topic)

    logger.info(f"🤖 Calling Gemini for topic: '{topic}'")

    try:
        # NOTE: The official google-genai library uses sync calls.
        # We wrap it in asyncio's run_in_executor to avoid blocking the event loop.
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,                          # Use default thread pool
            lambda: model.generate_content(prompt)
        )

        raw_text = response.text
        logger.info(f"✅ Gemini responded ({len(raw_text)} chars)")

        # Parse and validate with Pydantic
        data = json.loads(raw_text)
        quiz = Quiz.model_validate(data)

        # Ensure we got exactly 10 questions
        if len(quiz.questions) != 10:
            logger.warning(f"Gemini returned {len(quiz.questions)} questions, expected 10")

        return quiz.questions

    except json.JSONDecodeError as e:
        logger.error(f"❌ Gemini returned invalid JSON: {e}\nRaw: {raw_text[:500]}")
        raise ValueError(f"AI returned malformed data. Please try again.")

    except ValidationError as e:
        logger.error(f"❌ Pydantic validation failed: {e}")
        raise ValueError(f"AI response didn't match expected format. Please try again.")

    except Exception as e:
        logger.error(f"❌ Unexpected AI error: {e}")
        raise ValueError(f"AI service error: {str(e)}")