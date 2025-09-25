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
    PDF_DIR, WEBSITES,
    QDRANT_HOST, QDRANT_PORT,
    BYLAW_COLLECTION, GUIDES_COLLECTION,
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
                self._delete_by_filter(BYLAW_COLLECTION, "source", src)

        chunks = self.splitter.split_documents(docs)
        QdrantVS.from_documents(
            chunks,
            embedding=self.embeddings,
            location=self.location,
            collection_name=BYLAW_COLLECTION
        )
        self.logger.info(f"Ingested {len(chunks)} PDF chunks → {BYLAW_COLLECTION}")

    def ingest_websites(self):
        docs = []
        for url in WEBSITES:
            doc = WebsiteLoader(url).load()
            if doc:
                # delete by 'url' before inserting new
                self._delete_by_filter(GUIDES_COLLECTION, "url", url)
                docs.append(doc)

        if not docs:
            self.logger.warning("No websites loaded; nothing ingested.")
            return

        chunks = self.splitter.split_documents(docs)
        QdrantVS.from_documents(
            chunks,
            embedding=self.embeddings,
            location=self.location,
            collection_name=GUIDES_COLLECTION
        )
        self.logger.info(f"Ingested {len(chunks)} website chunks → {GUIDES_COLLECTION}")

    def ingest_texts_folder(self, texts_glob: str = "data/processed/*.txt"):
        from service.text_loader import TextLoader
        docs = []
        for fp in glob.glob(texts_glob):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    txt = f.read()
                # delete old by 'source' (file path) before inserting
                self._delete_by_filter(GUIDES_COLLECTION, "source", fp)
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
            collection_name=GUIDES_COLLECTION
        )
        self.logger.info(f"Ingested {len(chunks)} text chunks → {GUIDES_COLLECTION}")

    def get_relevant_chunks(self, query: str, k: int = 4):
        bylaw_db = QdrantVS(
            client=self.client,
            embedding_function=self.embeddings.embed_query,
            collection_name=BYLAW_COLLECTION
        )
        guides_db = QdrantVS(
            client=self.client,
            embedding_function=self.embeddings.embed_query,
            collection_name=GUIDES_COLLECTION
        )

        a = max(1, k//2)
        b = max(1, k - a)

        bylaw_hits = bylaw_db.similarity_search(query, k=a)
        guides_hits = guides_db.similarity_search(query, k=b)

        self.logger.info(f"Retrieved {len(bylaw_hits)} bylaw + {len(guides_hits)} guides chunks")
        return bylaw_hits + guides_hits
