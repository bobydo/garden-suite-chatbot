# Garden Suite Chatbot AI Guidelines

## System Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot for Edmonton garden suite regulations using **Qdrant + Ollama + LangChain**. The system follows a **class-based service architecture** with clear separation of concerns.

### Core Components
- **Data Sources**: PDFs (`data/pdf/`), websites (config.WEBSITES), text files (`data/processed/`)  
- **Vector Storage**: Two Qdrant collections - `bylaw_index` (PDFs) and `website_index` (websites/texts)
- **Services**: Class-based services in `/service/` handle specific responsibilities
- **Jobs**: Background refresh scripts in `/jobs/` for periodic data updates
- **Tools**: Placeholder classes in `/tools/` for future function calling

### Data Flow Pattern
1. **Ingestion**: `manage.py` → `RetrieverService` → Custom loaders → Text splitting → Qdrant storage
2. **Chat**: FastAPI `/chat` → `PipelineService` → `RetrieverService.get_relevant_chunks()` → LLM with context
3. **Refresh**: Background jobs directly update vector collections with hash-based deduplication

## Configuration Management

All settings centralized in `config.py` using environment variables with sensible defaults:
```python
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
```

## Logging Convention

**Always** use `LogHelper.get_logger()` for consistent logging across services:
```python
from service.log_helper import LogHelper
logger = LogHelper.get_logger("Component.SubComponent")  # Hierarchical naming
logger.info(f"Processed {count} items")  # Use f-strings for context
```
- Auto-creates `/logs/YYYY-MM-DD/` directories  
- File naming: `{component}_YYYY-MM-DD.log`
- Logs to both file and console

## Service Class Pattern

Services are **stateful classes** initialized once, not functional modules:
```python
class RetrieverService:
    def __init__(self):
        self.embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        # Initialize once, reuse connections
```

## Vector Storage Patterns

### Hash-Based Deduplication
Before inserting new chunks, **always delete existing points by source**:
```python
self._delete_by_filter(collection, "source", file_path)  # PDFs/texts
self._delete_by_filter(collection, "url", website_url)   # Websites
```

### Chunking Strategy
- **Fixed settings**: 800 char chunks, 100 char overlap via `RecursiveCharacterTextSplitter`
- **Metadata preservation**: Include `source`, `url`, `title` in all chunks for retrieval context

### Dual Collection Strategy
- `bylaw_index`: Official PDF documents (zoning bylaws, regulations)
- `website_index`: Web content + processed text files (guides, FAQs)
- **Retrieval splits k/2 between collections** to ensure balanced context

## Development Workflows

### Local Setup
```bash
docker run -p 6333:6333 qdrant/qdrant  # Start Qdrant first
pip install -r requirements.txt
python manage.py ingest_pdfs           # Initial data load
uvicorn app.main:app --reload          # Dev server
```

### Content Management
- **Initial ingestion**: `python manage.py ingest_{pdfs,websites,texts}`
- **Background refresh**: `python jobs/refresh_{websites,texts}.py` (run as cron jobs)
- **Data directories**: Drop PDFs in `data/pdf/`, texts in `data/processed/`

## Error Handling Patterns

Services log warnings/errors but continue processing other items:
```python
for item in items:
    try:
        process(item)
    except Exception as e:
        logger.error(f"Failed processing {item}: {e}")
        continue  # Don't stop the whole batch
```

## API Design

Simple, focused FastAPI with minimal endpoints:
- `POST /chat`: Takes `{"question": str, "history": list}` 
- `GET /health`: System status check
- **No authentication** - designed for internal/demo use

## Future Extension Points

- **Tools directory**: Ready for LangChain function calling (see `BylawLookup` placeholder)
- **Prompt management**: System prompt externalized to `prompts/system_prompt.txt`
- **Environment-specific configs**: All Ollama/Qdrant settings via env vars

When adding features, follow the established patterns: class-based services, centralized config, consistent logging, and hash-based data management for vector stores.