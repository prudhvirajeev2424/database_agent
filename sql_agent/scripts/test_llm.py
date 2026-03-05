# LLM client tests
"""Small diagnostic script to exercise the LLM client and show full errors.

Run from project root (with .env loaded):

    python scripts/test_llm.py

It will attempt a simple chat completion and print the result or full traceback.
"""
import asyncio
import traceback
from dotenv import load_dotenv
load_dotenv()

from app.infrastructure.llm_client import LLMClient


async def main():
    client = LLMClient()
    try:
        resp = await client.chat_completion(messages=[{"role": "user", "content": "Say hello"}], temperature=0.0)
        print("RESPONSE:", resp)
    except Exception:
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
