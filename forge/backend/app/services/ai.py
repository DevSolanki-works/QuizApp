"""
ai.py — Gemini AI service for quiz generation.

STUB for Milestone 2. The actual Gemini API call is implemented in Milestone 4.
Having the file now lets other modules import it without breaking.

WHY GEMINI 1.5 FLASH:
  - Free tier: 15 requests/minute, 1 million tokens/day — more than enough.
  - Fast: Flash is optimised for low latency (important for game UX).
  - Structured output: we can prompt for raw JSON and validate with Pydantic.
"""

import logging
from typing import List

from app.models.quiz import Question

logger = logging.getLogger(__name__)


async def generate_questions(topic: str) -> List[Question]:
    """
    Call Gemini to produce 10 quiz questions on `topic`.

    Returns a list of validated Question objects.
    Raises ValueError if Gemini's response can't be parsed.

    NOTE: Full implementation in Milestone 4.
    """
    # Placeholder — will be replaced with real Gemini call
    logger.warning("ai.generate_questions called but Gemini integration not yet implemented")
    raise NotImplementedError("Gemini integration coming in Milestone 4")
