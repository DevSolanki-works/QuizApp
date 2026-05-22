import asyncio
import json
import websockets
import httpx

BASE = "ws://localhost:8000"
HTTP = "http://localhost:8000"

async def player(room_code, name, is_host, topic="The Moon"):
    uri = f"{BASE}/ws/{room_code}/{name}"
    async with websockets.connect(uri) as ws:
        print(f"[{name}] connected")

        async for raw in ws:
            msg = json.loads(raw)
            t = msg["type"]
            print(f"[{name}] ← {t}")

            # Host starts the game once 2 players have joined
            if is_host and t == "PLAYER_JOINED":
                if len(msg["data"]["players"]) >= 2:
                    await ws.send(json.dumps({"action": "start_game", "topic": topic}))
                    print(f"[{name}] → start_game")

            elif t == "QUESTION":
                await asyncio.sleep(2)
                choice = 1 if name == "Alice" else 2
                await ws.send(json.dumps({"action": "answer", "choice": choice, "time_ms": 2000}))
                print(f"[{name}] → answer {choice}")

            elif t == "GAME_OVER":
                print(f"[{name}] Final scores: {msg['data']['final_scores']}")
                break

            elif t == "ERROR":
                print(f"[{name}] ERROR: {msg['data']['message']}")
                break

async def main():
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{HTTP}/rooms/create", json={"host_name": "Alice"})
        room_code = r.json()["room_code"]
        print(f"Room created: {room_code}")

    await asyncio.gather(
        player(room_code, "Alice", is_host=True),
        player(room_code, "Bob",   is_host=False),
    )

asyncio.run(main())
