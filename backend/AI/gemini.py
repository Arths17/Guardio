from pathlib import Path
import os

from dotenv import load_dotenv


ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ROOT_ENV)


def _get_api_key() -> str | None:
	return os.getenv("GEMINI_API_KEY")


def generate_text(prompt: str, system_instruction: str | None = None) -> str:
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
