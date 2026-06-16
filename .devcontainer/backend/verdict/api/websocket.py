import json
import asyncio
import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from verdict.config import REDIS_URL

websocket_router = APIRouter()


@websocket_router.websocket("/ws/cases/{case_id}/live")
async def case_live_stream(websocket: WebSocket, case_id: str):
    await websocket.accept()
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(f"case:{case_id}:events")

    try:
        while True:
            message = await asyncio.wait_for(
                pubsub.get_message(ignore_subscribe_messages=True),
                timeout=30.0
            )
            if message and message["type"] == "message":
                data = message["data"]
                await websocket.send_text(data)
                # Stop streaming after verdict is issued
                try:
                    parsed = json.loads(data)
                    if parsed.get("event_type") == "VERDICT_ISSUED":
                        await asyncio.sleep(0.5)
                        break
                except Exception:
                    pass
            else:
                # Keep-alive ping
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except asyncio.TimeoutError:
        pass
    finally:
        await pubsub.unsubscribe(f"case:{case_id}:events")
        await pubsub.close()
        await r.close()
