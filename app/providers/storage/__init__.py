from app.core.config import settings
from .minio import MinioStorageProvider
from .local import LocalStorageProvider
from .base import StorageProvider


def get_storage_provider() -> StorageProvider:
    if settings.STORAGE_PROVIDER == "local":
        return LocalStorageProvider()
    return MinioStorageProvider()
