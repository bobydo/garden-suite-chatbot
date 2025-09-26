import glob
from typing import List
from qdrant_client import QdrantClient
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Qdrant as QdrantVS
from langchain_ollama import OllamaEmbeddings
from service.pdf_loader import LocalPdfLoader
from service.website_loader import WebsiteLoader
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from service.log_helper import LogHelper
from config import (
    PDF_DIR, WEBSITES, EXCELS,
    QDRANT_HOST, QDRANT_PORT,
    PDF_COLLECTION, WEBSITE_COLLECTION, EXCEL_COLLECTION,
    EMBED_MODEL
)

class RetrieverService:
    def __init__(self):
        self.embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        self.logger = LogHelper.get_logger("RetrieverService")
        self.location = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
        self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

    # ---- helper: delete all points for a source/url before reinserting ----
    def _delete_by_filter(self, collection: str, key: str, value: str):
        try:
            self.client.delete(
                collection_name=collection,
                points_selector=Filter(
                    must=[FieldCondition(key=key, match=MatchValue(value=value))]
                ),
                wait=True,  # ensure deletion completes before reinsert
            )
            self.logger.info(f"Deleted old points in {collection} where {key}=={value}")
        except Exception as e:
            self.logger.warning(f"Delete filter failed ({collection}, {key}={value}): {e}")

    def ingest_pdfs(self):
        pdf_files = glob.glob(f"{PDF_DIR}/*.pdf")
        if not pdf_files:
            self.logger.warning("No PDFs found to ingest.")
            return

        docs = []
        for pdf_path in pdf_files:
            docs.extend(LocalPdfLoader(pdf_path).load())

        # delete old by 'source' for each pdf before writing new
        seen_sources = set(d.metadata.get("source") for d in docs if d is not None)
        for src in seen_sources:
            if src:
                self._delete_by_filter(PDF_COLLECTION, "source", src)

        chunks = self.splitter.split_documents(docs)
        QdrantVS.from_documents(
            chunks,
            embedding=self.embeddings,
            location=self.location,
            collection_name=PDF_COLLECTION
        )
        self.logger.info(f"Ingested {len(chunks)} PDF chunks → {PDF_COLLECTION}")

    def ingest_websites(self):
        docs = []
        for url in WEBSITES:
            doc = WebsiteLoader(url).load()
            if doc:
                # delete by 'url' before inserting new
                self._delete_by_filter(WEBSITE_COLLECTION, "url", url)
                docs.append(doc)

        if not docs:
            self.logger.warning("No websites loaded; nothing ingested.")
            return

        chunks = self.splitter.split_documents(docs)
        QdrantVS.from_documents(
            chunks,
            embedding=self.embeddings,
            location=self.location,
            collection_name=WEBSITE_COLLECTION
        )
        self.logger.info(f"Ingested {len(chunks)} website chunks → {WEBSITE_COLLECTION}")

    def ingest_texts_folder(self, texts_glob: str = "data/processed/*.txt"):
        from service.text_loader import TextLoader
        docs = []
        for fp in glob.glob(texts_glob):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    txt = f.read()
                # delete old by 'source' (file path) before inserting
                self._delete_by_filter(WEBSITE_COLLECTION, "source", fp)
                docs.append(TextLoader(text=txt, source=fp).load())
            except Exception as e:
                self.logger.error(f"Failed reading {fp}: {e}")

        if not docs:
            self.logger.warning("No text docs to ingest.")
            return

        chunks = self.splitter.split_documents(docs)
        QdrantVS.from_documents(
            chunks,
            embedding=self.embeddings,
            location=self.location,
            collection_name=WEBSITE_COLLECTION
        )
        self.logger.info(f"Ingested {len(chunks)} text chunks → {WEBSITE_COLLECTION}")

    def ingest_excel_files(self, excel_glob: str = "data/excel/*.xlsx"):
        from service.excel_loader import ExcelLoader
        docs = []
        
        # Process local Excel files
        excel_files = glob.glob(excel_glob) + glob.glob("data/excel/*.xls")
        for fp in excel_files:
            try:
                self.logger.info(f"Processing Excel file: {fp}")
                # Delete old data by 'source' before inserting
                self._delete_by_filter(EXCEL_COLLECTION, "source", fp)
                excel_docs = ExcelLoader(fp).load()
                docs.extend(excel_docs)
            except Exception as e:
                self.logger.error(f"Failed processing Excel file {fp}: {e}")

        # Process Excel URLs from EXCELS config
        if EXCELS:
            self.logger.info(f"Found {len(EXCELS)} Excel URLs in config")
        
        for url in EXCELS:
            try:
                self.logger.info(f"Processing Excel URL: {url}")
                # Delete old data by 'url' before inserting
                self._delete_by_filter(EXCEL_COLLECTION, "url", url)
                excel_docs = ExcelLoader(url).load()
                docs.extend(excel_docs)
            except Exception as e:
                self.logger.error(f"Failed processing Excel URL {url}: {e}")

        if not docs:
            self.logger.warning("No Excel files to ingest. Place .xlsx/.xls files in data/excel/ or add Excel URLs to config.")
            return

        chunks = self.splitter.split_documents(docs)
        QdrantVS.from_documents(
            chunks,
            embedding=self.embeddings,
            location=self.location,
            collection_name=EXCEL_COLLECTION
        )
        self.logger.info(f"Ingested {len(chunks)} Excel chunks → {EXCEL_COLLECTION}")

    def get_relevant_chunks(self, query: str, k: int = 6):
        pdf_db = QdrantVS(
            client=self.client,
            embedding_function=self.embeddings.embed_query,
            collection_name=PDF_COLLECTION
        )
        guides_db = QdrantVS(
            client=self.client,
            embedding_function=self.embeddings.embed_query,
            collection_name=WEBSITE_COLLECTION
        )
        excel_db = QdrantVS(
            client=self.client,
            embedding_function=self.embeddings.embed_query,
            collection_name=EXCEL_COLLECTION
        )

        # Split k across three collections
        a = max(1, k//3)           # PDF chunks
        b = max(1, k//3)           # Website chunks  
        c = max(1, k - a - b)      # Excel chunks (gets remainder)

        pdf_hits = pdf_db.similarity_search(query, k=a)
        guides_hits = guides_db.similarity_search(query, k=b)
        excel_hits = excel_db.similarity_search(query, k=c)

        self.logger.info(f"Retrieved {len(pdf_hits)} PDF + {len(guides_hits)} guides + {len(excel_hits)} excel chunks")
        return pdf_hits + guides_hits + excel_hits
