from typing import BinaryIO
from minio import Minio
from app.core.config import settings
from .base import StorageProvider


class MinioStorageProvider(StorageProvider):
    def __init__(self) -> None:
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,
        )
        if not self.client.bucket_exists(settings.STORAGE_BUCKET):
            self.client.make_bucket(settings.STORAGE_BUCKET)

    def put(self, file_obj: BinaryIO, object_name: str) -> str:
        self.client.put_object(
            settings.STORAGE_BUCKET,
            object_name,
            data=file_obj,
            length=-1,
            part_size=10 * 1024 * 1024,
        )
        return object_name

    def get(self, object_name: str) -> bytes:
        response = self.client.get_object(settings.STORAGE_BUCKET, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data

    def get_stream(self, object_name: str, chunk_size: int = 64 * 1024):
        response = self.client.get_object(settings.STORAGE_BUCKET, object_name)
        try:
            for chunk in response.stream(chunk_size):
                yield chunk
        finally:
            response.close()
            response.release_conn()

    def delete(self, object_name: str) -> None:
        self.client.remove_object(settings.STORAGE_BUCKET, object_name)
