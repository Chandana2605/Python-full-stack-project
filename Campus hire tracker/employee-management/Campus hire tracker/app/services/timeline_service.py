from typing import Any

from app.core.enums import TimelineEventType
from app.db.postgresql import get_database
from app.schemas.common import utc_now
from app.utils.ids import new_id


async def add_timeline_event(
    candidate_id: str,
    actor_id: str,
    event_type: TimelineEventType,
    description: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "id": new_id(),
        "candidate_id": candidate_id,
        "actor_id": actor_id,
        "event_type": event_type.value,
        "description": description,
        "metadata": metadata or {},
        "created_at": utc_now(),
    }
    await get_database().timeline_events.insert_one(event)
    return event
