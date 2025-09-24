import hashlib
import os

class HashHelper:
    @staticmethod
    def file_hash(file_path: str) -> str:
        """Hash based on file name + last modified time + size."""
        if not os.path.exists(file_path):
            return ""
        stat = os.stat(file_path)
        base = f"{file_path}-{stat.st_mtime}-{stat.st_size}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    @staticmethod
    def url_hash(url: str, text: str) -> str:
        """Hash based on URL + first 2KB of content (stable & light)."""
        base = f"{url}-{text[:2000]}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    @staticmethod
    def text_hash(file_name: str, text: str) -> str:
        """Hash based on text file name + content length."""
        base = f"{file_name}-{len(text)}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()
