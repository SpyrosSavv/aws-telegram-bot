from qdrant_client import QdrantClient
from functools import lru_cache

from aws_telegram_bot.config import settings

@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """
    Get or create the Qdrant client.
    The client is created once and cached for subsequent calls.
    """
    return QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY
    )