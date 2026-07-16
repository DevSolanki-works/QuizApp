"""
generate_quick_picks_bank.py — ONE-OFF, offline script to (re)build the
static Quick Picks question bank (app/data/quick_picks_questions.json).

SAFETY: refuses to run if GEMINI_API_KEY isn't detected, rather than
silently falling back to the generic FALLBACK_QUESTIONS list (which is
what happened the first time this ran from the wrong working directory).

Normal run (all topics):
    cd forge/backend
    source .venv/bin/activate
    GEMINI_MODEL=gemini-2.5-pro python scripts/generate_quick_picks_bank.py

Dry-run ONE topic first to sanity-check real output before committing to
the full run:
    GEMINI_MODEL=gemini-2.5-pro TEST_TOPIC="Movies" python scripts/generate_quick_picks_bank.py
"""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # allow `app.*` imports

from app.core.config import settings
from app.services.ai import generate_questions
from app.services.quick_picks import QUICK_PICK_TOPICS

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "app" / "data" / "quick_picks_questions.json"
BATCHES_PER_TOPIC = 15
SECONDS_BETWEEN_CALLS = 4.5
TEST_TOPIC = os.environ.get("TEST_TOPIC")  # set to dry-run a single topic only


async def build_topic_bank(topic: str) -> list[dict]:
    seen_questions: set[str] = set()
    bank: list[dict] = []

    for i in range(BATCHES_PER_TOPIC):
        print(f"  [{topic}] batch {i + 1}/{BATCHES_PER_TOPIC}...")
        try:
            questions = await generate_questions(topic, max_output_tokens=4096)
        except Exception as exc:
            print(f"  [{topic}] batch {i + 1} failed: {exc} — skipping")
            await asyncio.sleep(SECONDS_BETWEEN_CALLS)
            continue

        for q in questions:
            key = q.question.strip().lower()
            if key not in seen_questions:
                seen_questions.add(key)
                bank.append(q.model_dump())

        await asyncio.sleep(SECONDS_BETWEEN_CALLS)

    print(f"  [{topic}] done — {len(bank)} unique questions")
    return bank


async def main():
    # ── Hard fail if Gemini isn't actually reachable — this is the exact
    #    guard that would have caught last time's silent fallback-junk run.
    if not settings.GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY is empty in settings. Refusing to run.")
        print(f"   Current working directory: {Path.cwd()}")
        print("   Pydantic loads .env relative to CWD — run this from inside forge/backend/,")
        print("   or confirm GEMINI_API_KEY is exported in your shell.")
        sys.exit(1)

    print(f"✅ GEMINI_API_KEY detected (starts with: {settings.GEMINI_API_KEY[:6]}...)")
    print(f"✅ Model: {settings.GEMINI_MODEL}\n")

    topics_to_run = [TEST_TOPIC] if TEST_TOPIC else list(QUICK_PICK_TOPICS)
    if TEST_TOPIC:
        print(f"⚠️  TEST_TOPIC set — dry-running ONLY '{TEST_TOPIC}', existing file will NOT be modified.\n")

    result: dict[str, list[dict]] = {}
    if not TEST_TOPIC and OUTPUT_PATH.exists():
        result = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    for topic in topics_to_run:
        print(f"Generating bank for: {topic}")
        bank = await build_topic_bank(topic)

        if TEST_TOPIC:
            print(f"\n--- SAMPLE OUTPUT (not saved) ---")
            print(json.dumps(bank[:3], indent=2))
            print(f"--- end sample, {len(bank)} total generated ---\n")
            return  # dry run — never touches the real file

        result[topic] = bank
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"  Saved progress to {OUTPUT_PATH}\n")

    total = sum(len(v) for v in result.values())
    print(f"✅ Done. Total questions in bank: {total}")


if __name__ == "__main__":
    asyncio.run(main())