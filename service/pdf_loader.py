import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain.schema import Document
from service.log_helper import LogHelper
from service.hash_helper import HashHelper

class PdfLoader:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.logger = LogHelper.get_logger("PdfLoader")

    def load(self) -> List[Document]:
        if not os.path.exists(self.pdf_path):
            self.logger.error(f"PDF not found: {self.pdf_path}")
            return []
        loader = PyPDFLoader(self=self.pdf_path)  # NOTE: older sig: PyPDFLoader(path); some envs accept PyPDFLoader(self=...) fix below
        try:
            loader = PyPDFLoader(self.pdf_path)
        except TypeError:
            # fallback if constructor signature differs
            pass
        docs = loader.load()
        doc_hash = HashHelper.file_hash(self.pdf_path)
        for d in docs:
            # do not set fragile titles; only source + hash
            d.metadata.update({"source": self.pdf_path, "hash": doc_hash})
        self.logger.info(f"Loaded {len(docs)} pages from {self.pdf_path}")
        return docs
