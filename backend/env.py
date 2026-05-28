import os
import logging


def validate_env():
    logger = logging.getLogger("backend.env")
    has_key = bool(os.getenv("GEMINI_API_KEY"))
    ai_disabled = os.getenv("GUARDIO_DISABLE_AI", "").lower() == "true"

    if not has_key and not ai_disabled:
        logger.info(
            "No GEMINI_API_KEY set — AI Copilot will return stub responses. "
            "Set GUARDIO_DISABLE_AI=true to suppress this message, or add a key to .env."
        )


__all__ = ["validate_env"]
