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
    """Generate text using Gemini with retries, timeout and a simple circuit breaker.

    Returns a deterministic stub when AI is disabled or API key missing. On repeated
    failures the circuit opens and calls return `[ai-circuit-open]` until cooldown.
    """
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

    # record failure and possibly open circuit
    _CIRCUIT["failures"] += 1
    if _CIRCUIT["failures"] >= circuit_failures:
        _CIRCUIT["open_until"] = time.monotonic() + circuit_cooldown
        logger.error("Gemini circuit opened for %.1fs", circuit_cooldown)

    return f"[ai-error] {last_exc}"


def main():
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to the repository .env file."
        )

    from google import genai

    client = genai.Client(api_key=api_key)
    chat = client.chats.create(
        model="gemini-3.1-flash-lite",
        config={
            "system_instruction": (
                "You are a helpful assistant that provides concise and "
                "accurate information about cybersecurity. You are a "
                "friendly mentor who is always eager to share knowledge and "
                "help others understand complex cybersecurity concepts in a "
                "simple way. You can provide explanations, tips, and best "
                "practices related to cybersecurity topics."
            ),
        },
    )
    while True:
        try:
            prompt = input("Enter your prompt: ")
            # stop on empty input
            decide = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                config={
                    "system_instruction": (
                        "Provide only a yes or no answer."
                    )
                },
                contents=prompt + " do you want to continue the conversation?",
            )
            decide = decide.text.strip().upper()
            if decide == "YES" or decide == "NO":
                break
            result = chat.send_message(prompt)
            print(result.text)
        except Exception:
            print(
                "You ran out of API credits, please upgrade your plan to "
                "continue or wait until the quota resets."
            )
            break


if __name__ == "__main__":
    main()
