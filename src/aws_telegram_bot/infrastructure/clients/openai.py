from openai import OpenAI
from functools import lru_cache

from aws_telegram_bot.config import settings

@lru_cache
def get_openai_client() -> OpenAI:
    """
    Get or create the OpenAI client.
    The client is created once and cached for subsequent calls.
    """
    return OpenAI(api_key=settings.OPENAI_API_KEY)