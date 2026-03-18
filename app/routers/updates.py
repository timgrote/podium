import asyncio
import json
import time

from fastapi import APIRouter
from starlette.responses import StreamingResponse

from ..events import event_bus

router = APIRouter()


async def _event_stream(project_id: str):
    last_check = time.time()
    while True:
        events = event_bus.get_since(project_id, last_check)
        if events:
            last_check = events[-1].timestamp
            for ev in events:
                data = json.dumps({"type": ev.event_type, "entity_id": ev.entity_id})
                yield f"event: {ev.event_type}\ndata: {data}\n\n"
        else:
            yield ": keepalive\n\n"
        await asyncio.sleep(2)


@router.get("/projects/{project_id}/stream")
async def project_stream(project_id: str):
    return StreamingResponse(
        _event_stream(project_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
