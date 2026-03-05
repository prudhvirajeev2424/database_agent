
import asyncio
import time
from openai import AsyncAzureOpenAI
from app.config import Config
from app.infrastructure.logger import AppLogger
import os


class LLMClient:

    def __init__(self):
        api_key = (Config.AZURE_OPENAI_KEY or "").strip()
        azure_endpoint = (Config.AZURE_OPENAI_ENDPOINT or "").rstrip("/")
        api_version = Config.AZURE_OPENAI_API_VERSION or "2023-05-15"
        if not api_key:
            raise RuntimeError(
                "Azure OpenAI API key is missing. Set AZURE_OPENAI_API_KEY in your .env (no leading spaces)."
            )

        os.environ.setdefault("OPENAI_API_KEY", api_key)
        if azure_endpoint:
            os.environ.setdefault("OPENAI_API_BASE", azure_endpoint)
            os.environ.setdefault("OPENAI_API_TYPE", "azure")
        if api_version:
            os.environ.setdefault("OPENAI_API_VERSION", api_version)

        self.client = AsyncAzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=azure_endpoint
        )
        self.model = Config.AZURE_OPENAI_DEPLOYMENT

    async def chat_completion(self, *, messages, temperature=0.0, response_format=None):
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        max_retries = 3
        backoff_base = 1.0

        for attempt in range(1, max_retries + 1):
            try:
                # Async Azure OpenAI client supports awaitable calls
                return await self.client.chat.completions.create(**kwargs)
            except Exception as e:
                serr = str(e)
                AppLogger.error(f"LLM request failed (attempt {attempt}): {serr}")

                if ("500" in serr or "internal_server_error" in serr.lower()
                        or "Backend returned unexpected response" in serr or "server_error" in serr.lower()):
                    if attempt < max_retries:
                        sleep_for = backoff_base * (2 ** (attempt - 1))
                        AppLogger.info(f"Retrying LLM request after {sleep_for}s backoff...")
                        await asyncio.sleep(sleep_for)
                        continue

                    raise RuntimeError(
                        "Azure OpenAI returned a server error (500). This may be transient — "
                        "the client retried and failed. Try again later. If the problem persists, "
                        "check Azure service health and contact Microsoft support. Original error: " + serr
                    ) from e

                if "404" in serr or "Resource not found" in serr or "Not Found" in serr:
                    raise RuntimeError(
                        "Azure OpenAI resource not found (404). Please verify `AZURE_OPENAI_ENDPOINT` "
                        "and `AZURE_OPENAI_DEPLOYMENT` in your .env, and ensure the deployment exists. "
                        "Original error: " + serr
                    ) from e

                # Other errors: don't retry further
                raise