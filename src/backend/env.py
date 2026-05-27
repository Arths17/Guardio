import os
import logging


def validate_env():
    logger = logging.getLogger("backend.env")
    recommended = [
        "GEMINI_API_KEY",
        "GUARDIO_DISABLE_AI",
    ]
    missing = [k for k in recommended if os.getenv(k) is None]
    if missing:
        logger.warning("Recommended env vars missing: %s", missing)


__all__ = ["validate_env"]
