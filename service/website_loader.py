import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from langchain.schema import Document
from service.log_helper import LogHelper
from service.hash_helper import HashHelper

class WebsiteLoader:
    def __init__(self, url: str):
        self.url = url
        self.logger = LogHelper.get_logger("WebsiteLoader")

    def _auto_title(self) -> str:
        parsed = urlparse(self.url)
        return f"{parsed.netloc}{parsed.path}".replace("/", " ").strip()

    def load(self) -> Document | None:
        try:
            resp = requests.get(self.url, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(" ", strip=True)
            doc_hash = HashHelper.url_hash(self.url, text)
            title = self._auto_title()
            doc = Document(page_content=text, metadata={"url": self.url, "hash": doc_hash, "title": title})
            self.logger.info(f"Loaded website: {self.url}")
            return doc
        except Exception as e:
            self.logger.error(f"Failed to load {self.url}: {e}")
            return None
