from config import WEBSITES, GUIDES_COLLECTION, QDRANT_HOST, QDRANT_PORT, EMBED_MODEL
from service.website_loader import WebsiteLoader
from service.log_helper import LogHelper
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Qdrant as QdrantVS
from langchain_ollama import OllamaEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, FilterSelector

logger = LogHelper.get_logger("Job.RefreshWebsites")

def run():
    docs = []
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

    for url in WEBSITES:
        loader = WebsiteLoader(url)
        doc = loader.load()
        if doc:
            # delete existing by URL
            try:
                client.delete(
                    collection_name=GUIDES_COLLECTION,
                    points_selector=FilterSelector(
                        filter=Filter(
                            must=[FieldCondition(key="url", match=MatchValue(value=url))]
                        )
                    ),
                    wait=True,
                )
                logger.info(f"Deleted existing points for {url}")
            except Exception as e:
                logger.warning(f"Delete failed for {url}: {e}")
            docs.append(doc)

    if not docs:
        logger.warning("No websites loaded.")
        return

    chunks = splitter.split_documents(docs)
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    QdrantVS.from_documents(
        chunks,
        embedding=embeddings,
        location=f"http://{QDRANT_HOST}:{QDRANT_PORT}",
        collection_name=GUIDES_COLLECTION
    )
    logger.info(f"Refreshed {len(chunks)} website chunks → {GUIDES_COLLECTION}")

if __name__ == "__main__":
    run()
