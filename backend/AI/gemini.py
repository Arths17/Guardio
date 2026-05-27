from pathlib import Path
import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv


ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ROOT_ENV)


_CIRCUIT = {
    "failures": 0,
    "open_until": 0.0,
}


def _get_api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY")


def _call_genai(api_key: str, prompt: str, system_instruction: str | None):
    from google import genai

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        config={
            "system_instruction": system_instruction
            or (
                "You are a helpful assistant that provides concise and "
                "accurate information about cybersecurity."
            ),
        },
        contents=prompt,
    )
    return getattr(response, "text", str(response))


def generate_text(
    prompt: str,
    system_instruction: str | None = None,
    timeout: float = 8.0,
    retries: int = 2,
    circuit_failures: int = 3,
    circuit_cooldown: float = 60.0,
):
    logger = logging.getLogger("backend.AI.gemini")

    disable = os.getenv("GUARDIO_DISABLE_AI", "false").lower() == "true"
    if disable:
        return "[ai-stub] " + (prompt[:400] + ("..." if len(prompt) > 400 else ""))

    now = time.monotonic()
    if _CIRCUIT["open_until"] > now:
        return "[ai-circuit-open]"

    api_key = _get_api_key()
    if not api_key:
        return "[ai-missing-key] " + (prompt[:400] + ("..." if len(prompt) > 400 else ""))

    attempt = 0
    last_exc = None
    while attempt <= retries:
        attempt += 1
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(_call_genai, api_key, prompt, system_instruction)
                return future.result(timeout=timeout)
        except Exception as exc:
            last_exc = exc
            logger.warning("Gemini call failed (attempt %d): %s", attempt, exc)
            time.sleep(0.5 * attempt)

    _CIRCUIT["failures"] += 1
    if _CIRCUIT["failures"] >= circuit_failures:
        _CIRCUIT["open_until"] = time.monotonic() + circuit_cooldown
        logger.error("Gemini circuit opened for %.1fs", circuit_cooldown)

    return f"[ai-error] {last_exc}"
