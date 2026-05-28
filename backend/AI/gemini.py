from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from backend.telemetry.telemetry import telemetry as _telemetry

try:
    from prometheus_client import Counter as _Counter
    _ai_calls = _Counter("guardio_ai_calls_total", "Total AI calls")
    _ai_failures = _Counter("guardio_ai_failures_total", "Total AI failures")
    _ai_circuit = _Counter(
        "guardio_ai_circuit_open_total", "AI circuit openings"
    )
except Exception:
    _ai_calls = None
    _ai_failures = None
    _ai_circuit = None

ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ROOT_ENV)

# Module-level pool — avoids thread-per-call overhead
_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="gemini")

_CIRCUIT: dict = {"failures": 0, "open_until": 0.0}

_MODEL = "gemini-2.0-flash-lite"
_DEFAULT_SYSTEM = (
    "You are a helpful assistant that provides concise and accurate "
    "information about cybersecurity."
)


def _get_api_key() -> Optional[str]:
    return os.getenv("GEMINI_API_KEY")


def _call_genai(
    api_key: str, prompt: str, system: Optional[str]
) -> str:
    from google import genai  # type: ignore[import-untyped]

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=_MODEL,
        config={"system_instruction": system or _DEFAULT_SYSTEM},
        contents=prompt,
    )
    return getattr(response, "text", str(response))


def generate_text(
    prompt: str,
    system_instruction: Optional[str] = None,
    timeout: float = 8.0,
    retries: int = 2,
    circuit_failures: int = 3,
    circuit_cooldown: float = 60.0,
) -> str:
    logger = logging.getLogger("backend.AI.gemini")

    if os.getenv("GUARDIO_DISABLE_AI", "false").lower() == "true":
        stub = prompt[:400] + ("..." if len(prompt) > 400 else "")
        return "[ai-stub] " + stub

    now = time.monotonic()
    if _CIRCUIT["open_until"] > now:
        return "[ai-circuit-open]"

    api_key = _get_api_key()
    if not api_key:
        stub = prompt[:400] + ("..." if len(prompt) > 400 else "")
        return "[ai-missing-key] " + stub

    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 2):
        try:
            if _ai_calls is not None:
                _ai_calls.inc()
            _telemetry.increment("ai_calls")
            future = _EXECUTOR.submit(
                _call_genai, api_key, prompt, system_instruction
            )
            return future.result(timeout=timeout)
        except Exception as exc:
            last_exc = exc
            logger.warning("Gemini attempt %d failed: %s", attempt, exc)
            if attempt <= retries:
                time.sleep(0.3 * attempt)

    _CIRCUIT["failures"] += 1
    if _CIRCUIT["failures"] >= circuit_failures:
        _CIRCUIT["open_until"] = time.monotonic() + circuit_cooldown
        logger.error("Gemini circuit opened for %.0fs", circuit_cooldown)
        if _ai_circuit is not None:
            _ai_circuit.inc()
        _telemetry.increment("ai_circuit_open")

    if _ai_failures is not None:
        _ai_failures.inc()
    _telemetry.increment("ai_failures")
    return f"[ai-error] {last_exc}"
