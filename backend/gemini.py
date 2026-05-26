from pathlib import Path
import os

from dotenv import load_dotenv
from google import genai


ROOT_ENV = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ROOT_ENV)


def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to the repository .env file.")

    client = genai.Client(api_key=api_key)
    prompt = input("Enter your prompt: ")
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        config={
            "system_instruction": "You are a helpful assistant that provides concise and accurate information about cybersecurity. You are are a friendly mentor who is always eager to share knowledge and help others understand complex cybersecurity concepts in a simple way. You can provide explanations, tips, and best practices related to cybersecurity topics.",
        },
        contents=prompt,
    )

    print(response.text)


if __name__ == "__main__":
    main()


