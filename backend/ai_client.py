import asyncio
from typing import Any, Dict, List, Optional

from backend.AI import gemini as gemini_helper
from backend.db import db
from backend.replay import replays


async def summarize_replay(rid: str) -> str:
    # Prefer DB-stored events; fall back to in-memory cache
    events: Optional[List[Dict[str, Any]]] = None
    try:
        events = await db.get_events_async(rid)
    except Exception:
        try:
            events = replays.get(rid) or []
        except Exception:
            events = []

    if not events:
        events = replays.get(rid) or []

    sample = events[:40]
    prompt = (
        "Summarize the following security incident as a short paragraph and "
        "list key actions to remediate:\n\n"
    )
    for ev in sample:
        prompt += (
            f"{ev.get('ts', '')}: {ev.get('type')} - "
            f"{ev.get('name', ev.get('color', ev.get('details', '')))}\n"
        )

    # Run AI call in a thread to avoid blocking
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: gemini_helper.generate_text(
            prompt,
            system_instruction=("Summarize and provide remediation steps."),
        ),
    )


def suggest_defense_for_event(event: Dict[str, Any]) -> str:
    prompt = (
        f"Given this event: {event!r}\n"
        "What defensive action should be taken (one short sentence)?"
    )
    return gemini_helper.generate_text(
        prompt,
        system_instruction=("Provide a single concise defensive recommendation."),
    )
