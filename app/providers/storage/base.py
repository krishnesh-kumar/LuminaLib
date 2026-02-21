from abc import ABC, abstractmethod
from typing import BinaryIO, Iterable


class StorageProvider(ABC):
    @abstractmethod
    def put(self, file_obj: BinaryIO, object_name: str) -> str: ...

    @abstractmethod
    def get(self, object_name: str) -> bytes: ...

    def get_stream(self, object_name: str, chunk_size: int = 64 * 1024) -> Iterable[bytes]:
        """Optional streaming interface; default falls back to full read."""
        data = self.get(object_name)
        yield data

    @abstractmethod
    def delete(self, object_name: str) -> None: ...
