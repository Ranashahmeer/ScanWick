"""Manual smoke test for the Gemini client — NOT run in CI.

Hits the real Gemini API, so it needs a valid GEMINI_API_KEY in .env and
will consume API quota. Run by hand:

    python scripts/smoke_test_gemini.py
"""

import asyncio

from app.services.ai_client import generate_text


async def main() -> None:
    result = await generate_text("Reply with exactly the word: pong")
    print("Gemini response:", result)


if __name__ == "__main__":
    asyncio.run(main())
