import glob
from config import TEXTS_DIR, WEBSITE_COLLECTION, QDRANT_HOST, QDRANT_PORT, EMBED_MODEL
from service.text_loader import TextLoader
from service.log_helper import LogHelper
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Qdrant as QdrantVS
from langchain_ollama import OllamaEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, FilterSelector

logger = LogHelper.get_logger("Job.RefreshTexts")

def run():
    text_files = glob.glob(f"{TEXTS_DIR}/*.txt")
    if not text_files:
        logger.warning("No text files found.")
        return

    docs = []
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

    for file in text_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                text = f.read()
            # delete existing by source
            try:
                client.delete(
                    collection_name=WEBSITE_COLLECTION,
                    points_selector=FilterSelector(
                        filter=Filter(
                            must=[FieldCondition(key="source", match=MatchValue(value=file))]
                        )
                    ),
                    wait=True,  # ensures deletion finishes before you insert new chunks
                )
                logger.info(f"Deleted existing points for {file}")
            except Exception as e:
                logger.warning(f"Delete failed for {file}: {e}")
            docs.append(TextLoader(text, source=file).load())
        except Exception as e:
            logger.error(f"Failed to read {file}: {e}")

    chunks = splitter.split_documents(docs)
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    QdrantVS.from_documents(
        chunks,
        embedding=embeddings,
        location=f"http://{QDRANT_HOST}:{QDRANT_PORT}",
        collection_name=WEBSITE_COLLECTION
    )
    logger.info(f"Refreshed {len(chunks)} text chunks → {WEBSITE_COLLECTION}")

if __name__ == "__main__":
    run()
