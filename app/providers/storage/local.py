from pathlib import Path
from typing import BinaryIO
from app.core.config import settings
from .base import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self) -> None:
        self.base = Path(settings.LOCAL_STORAGE_PATH)
        self.base.mkdir(parents=True, exist_ok=True)

    def put(self, file_obj: BinaryIO, object_name: str) -> str:
        target = self.base / object_name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as f:
            f.write(file_obj.read())
        return str(target)

    def get(self, object_name: str) -> bytes:
        path = self.base / object_name
        return path.read_bytes()

    def get_stream(self, object_name: str, chunk_size: int = 64 * 1024):
        path = self.base / object_name
        with path.open("rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    def delete(self, object_name: str) -> None:
        path = self.base / object_name
        if path.exists():
            path.unlink()
