from functools import lru_cache

from app.config.settings import get_settings
from app.storage.provider import MinioStorageProvider, StorageProvider


@lru_cache
def get_object_storage() -> StorageProvider:
    return MinioStorageProvider(get_settings())
