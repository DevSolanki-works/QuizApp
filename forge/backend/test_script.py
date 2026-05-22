import asyncio
from app.services.ai import generate_questions

async def test():
    qs = await generate_questions('The Solar System')
    for i, q in enumerate(qs):
        print(f'Q{i+1}: {q.question}')
        print(f' Correct: {q.options[q.correct_index]}')

asyncio.run(test())
