from elevenlabs.client import ElevenLabs
from functools import lru_cache

from aws_telegram_bot.config import settings

@lru_cache(maxsize=1)
def get_elevenlabs_client() -> ElevenLabs:
    """
    Get or create the ElevenLabs client.
    The client is created once and cached for subsequent calls.
    """
    return ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)