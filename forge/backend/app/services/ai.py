"""
AI service for Forge: AI Trivia Showdown.
Handles all communication with the Google Gemini API.
Generates structured trivia questions using Pydantic validation.
"""

import json
import logging
from app.core.config import settings
from app.models.quiz import Question, Difficulty
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Configure Gemini with our API key on module load
genai.configure(api_key=settings.GEMINI_API_KEY)


# Difficulty-specific prompt instructions
DIFFICULTY_PROMPTS = {
    Difficulty.EASY: (
        "Make the questions easy — suitable for general audiences with common "
        "everyday knowledge. Avoid obscure facts. Questions should be fun and "
        "accessible to everyone."
    ),
    Difficulty.MEDIUM: (
        "Make the questions moderately challenging — a mix of straightforward "
        "and slightly tricky questions. Suitable for someone with a general "
        "interest in the topic."
    ),
    Difficulty.HARD: (
        "Make the questions difficult — specific, expert-level, and tricky. "
        "Include nuanced details, less commonly known facts, and questions that "
        "would challenge even enthusiasts of the topic. Avoid obvious answers."
    ),
}


def build_prompt(topic: str, total_questions: int, difficulty: Difficulty) -> str:
    """
    Build the Gemini prompt with topic, question count, and difficulty baked in.

    Args:
        topic:            The trivia topic chosen by the host.
        total_questions:  How many questions to generate (5–20).
        difficulty:       Easy, Medium, or Hard difficulty level.

    Returns:
        A fully formatted prompt string ready to send to Gemini.
    """
    difficulty_instruction = DIFFICULTY_PROMPTS[difficulty]

    return f"""Generate exactly {total_questions} trivia questions about: {topic}

Difficulty level: {difficulty.value.upper()}
{difficulty_instruction}

Return ONLY a valid JSON array with exactly {total_questions} objects.
Each object must follow this exact structure:
{{
  "question": "Question text here?",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correct_index": 0
}}

Rules:
- correct_index is 0-based (0=A, 1=B, 2=C, 3=D)
- Every question must have exactly 4 options
- No duplicate questions
- No markdown, no explanation — JSON array only
- Array must contain exactly {total_questions} items"""


async def generate_questions(
    topic: str,
    total_questions: int = 10,
    difficulty: Difficulty = Difficulty.MEDIUM
) -> list[Question]:
    """
    Call Gemini to generate trivia questions for the given topic.

    Args:
        topic:            The trivia topic (e.g. "Marvel Movies").
        total_questions:  Number of questions to generate (default 10).
        difficulty:       Difficulty level (default Medium).

    Returns:
        A list of validated Question objects.

    Raises:
        ValueError: If Gemini returns malformed JSON or wrong question count.
        Exception:  On any Gemini API error.
    """
    try:
        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            generation_config={
                "temperature":        0.8,
                "max_output_tokens":  8192,   # Must be high to avoid truncation
            }
        )

        prompt = build_prompt(topic, total_questions, difficulty)
        logger.info(
            f"Generating {total_questions} {difficulty.value} questions for topic: '{topic}'"
        )

        response = await model.generate_content_async(prompt)
        raw = response.text.strip()

        # Strip markdown code fences if Gemini adds them despite instructions
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        # Parse and validate with Pydantic
        data = json.loads(raw)
        questions = [Question(**q) for q in data]

        if len(questions) != total_questions:
            raise ValueError(
                f"Expected {total_questions} questions, got {len(questions)}"
            )

        logger.info(f"Successfully generated {len(questions)} questions.")
        return questions

    except json.JSONDecodeError as e:
        logger.error(f"Gemini returned invalid JSON: {e}")
        raise ValueError(f"AI returned malformed response: {e}")
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise
