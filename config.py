import os

# === Base paths ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, "data", "pdf")
WEBSITES_DIR = os.path.join(BASE_DIR, "data", "websites")
TEXTS_DIR = os.path.join(BASE_DIR, "data", "processed")
INDEX_DIR = os.path.join(BASE_DIR, "index", "qdrant")

# === Qdrant settings ===
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
BYLAW_COLLECTION = "bylaw_index"
GUIDES_COLLECTION = "guides_index"

# === Ollama models ===
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# === Prompt file ===
SYSTEM_PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "system_prompt.txt")

# === Websites (URLs only) ===
WEBSITES = [
    "https://zoningbylaw.edmonton.ca/part-6-specific-development-regulations/610-backyard-housing",
    "https://www.edmonton.ca/permits_development/fees"
]
