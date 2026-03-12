import glob
from qdrant_client import QdrantClient
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Qdrant as QdrantVS
from langchain_ollama import OllamaEmbeddings
from service.pdf_loader import LocalPdfLoader
from service.website_loader import WebsiteLoader
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from service.log_helper import LogHelper
from rank_bm25 import BM25Okapi
from config import (
    PDF_DIR, WEBSITES, EXCELS,
    QDRANT_HOST, QDRANT_PORT,
    PDF_COLLECTION, WEBSITE_COLLECTION, EXCEL_COLLECTION,
    EMBED_MODEL,
    RETRIEVAL_SCORE_THRESHOLD, HYBRID_ALPHA, HYBRID_FETCH_MULTIPLIER,
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
        website_db = QdrantVS(
            client=self.client,
            embedding_function=self.embeddings.embed_query,
            collection_name=WEBSITE_COLLECTION
        )
        excel_db = QdrantVS(
            client=self.client,
            embedding_function=self.embeddings.embed_query,
            collection_name=EXCEL_COLLECTION
        )

        # Fetch more candidates than needed so BM25 has a meaningful pool to score
        a = max(1, k // 3) * HYBRID_FETCH_MULTIPLIER
        b = max(1, k // 3) * HYBRID_FETCH_MULTIPLIER
        c = max(1, k - (k // 3) * 2) * HYBRID_FETCH_MULTIPLIER

        pdf_hits = pdf_db.similarity_search_with_score(query, k=a)
        website_hits = website_db.similarity_search_with_score(query, k=b)
        excel_hits = excel_db.similarity_search_with_score(query, k=c)

        all_candidates = pdf_hits + website_hits + excel_hits  # List[Tuple[Document, float]]

        # --- Score threshold filtering (distance: lower = more relevant) ---
        filtered = [(doc, score) for doc, score in all_candidates if score <= RETRIEVAL_SCORE_THRESHOLD]
        if not filtered:
            self.logger.warning(
                f"All {len(all_candidates)} candidates exceeded threshold {RETRIEVAL_SCORE_THRESHOLD}; "
                "falling back to top-k by vector score."
            )
            filtered = sorted(all_candidates, key=lambda x: x[1])[:k]

        # --- BM25 scoring on filtered candidates ---
        tokenized_corpus = [doc.page_content.lower().split() for doc, _ in filtered]
        query_tokens = query.lower().split()
        bm25 = BM25Okapi(tokenized_corpus)
        bm25_scores = bm25.get_scores(query_tokens)  # higher = more relevant

        max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0

        # --- Hybrid scoring: combine vector relevance + BM25 relevance ---
        scored = []
        for i, (doc, dist) in enumerate(filtered):
            vector_relevance = 1.0 - dist                      # invert distance → relevance
            bm25_relevance = bm25_scores[i] / max_bm25         # normalize to [0, 1]
            final_score = HYBRID_ALPHA * vector_relevance + (1 - HYBRID_ALPHA) * bm25_relevance
            scored.append((doc, final_score))

        # Sort by combined score descending, return top k Documents
        scored.sort(key=lambda x: x[1], reverse=True)
        results = [doc for doc, _ in scored[:k]]

        self.logger.info(
            f"Hybrid retrieval: {len(pdf_hits)} PDF + {len(website_hits)} website + "
            f"{len(excel_hits)} excel candidates → {len(filtered)} passed threshold → "
            f"returning top {len(results)}"
        )

        return results
