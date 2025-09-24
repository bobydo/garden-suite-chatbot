from langchain.schema import Document
from service.log_helper import LogHelper
from service.hash_helper import HashHelper

class TextLoader:
    def __init__(self, text: str, source: str):
        self.text = text
        self.source = source  # file name or logical key
        self.logger = LogHelper.get_logger("TextLoader")

    def load(self) -> Document:
        doc_hash = HashHelper.text_hash(self.source, self.text)
        doc = Document(page_content=self.text, metadata={"source": self.source, "hash": doc_hash})
        self.logger.info(f"Created Document from text: {self.source}")
        return doc
