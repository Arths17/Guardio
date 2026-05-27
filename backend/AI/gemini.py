from pathlib import Path
import os
from dotenv import load_dotenv


ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ROOT_ENV)


def _get_api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY")


def generate_text(prompt: str, system_instruction: str | None = None) -> str:
    """Generate text using Gemini.

    Falls back to a deterministic stub if `GUARDIO_DISABLE_AI` is set or
    the API key is missing.
    """
    disable = os.getenv("GUARDIO_DISABLE_AI", "false").lower() == "true"
    if disable:
        return "[ai-stub] " + (
            prompt[:400] + ("..." if len(prompt) > 400 else "")
        )

    api_key = _get_api_key()
    if not api_key:
        return "[ai-missing-key] " + (
            prompt[:400] + ("..." if len(prompt) > 400 else "")
        )

    try:
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
    except Exception as e:
        return f"[ai-error] {e}"


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
