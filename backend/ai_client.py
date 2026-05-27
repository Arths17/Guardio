from backend.AI import gemini as gemini_helper
from backend.db import db
from backend.replay import replays


def summarize_replay(rid: str) -> str:
    events = db.get_events(rid) if db else None
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

    return gemini_helper.generate_text(
        prompt, system_instruction="Summarize and provide remediation steps."
    )


def suggest_defense_for_event(event: dict) -> str:
    prompt = (
        f"Given this event: {event!r}\n"
        "What defensive action should be taken (one short sentence)?"
    )
    return gemini_helper.generate_text(
        prompt,
        system_instruction=(
            "Provide a single concise defensive recommendation."
        ),
    )
