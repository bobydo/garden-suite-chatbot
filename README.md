# Garden Suite Chatbot — Local RAG + Agentic AI Reference Implementation

A production-style **Retrieval-Augmented Generation (RAG) chatbot** built entirely on a local, private stack. Developed as a reference implementation to demonstrate Agentic AI architecture, multi-source data ingestion, and hybrid retrieval — all without sending data to external APIs.

> Built as hands-on preparation for applying the same architecture to enterprise document intelligence use cases (SCADA documentation, facilities management, CMMS integration).

---

## Architecture Overview

```
User Question
     │
     ▼
┌─────────────────────────────────┐
│        FastAPI  /chat           │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│       PipelineService           │
│  LangGraph StateGraph           │
│  classify → retrieve → generate │
└──────┬──────────────────────────┘
       │ conditional edge (intent)
  ┌────┴──────────────────────┐
  │                           │
  ▼                           ▼
BylawLookup              FeeLookup
(PDF collection)    (website collection)
       │                     │
       └──────────┬──────────┘
                  ▼
      RetrieverService  ←── Hybrid Retrieval
      (Qdrant vector DB)     BM25 + Vector + Score Threshold
          │
   ┌──────┼──────┐
   ▼      ▼      ▼
 PDF   Website  Excel
 index  index   index
          │
          ▼
    Ollama (local LLM)
    llama3 / nomic-embed-text
    [no data leaves the machine]
```

### Why Local LLM (Ollama)?
All inference runs on-device via **Ollama** — no data is sent to OpenAI, Anthropic, or any external API. This is the same requirement for enterprise deployments where documents contain sensitive operational or regulatory data (e.g., SCADA systems, facilities management, legal documents).

---

## Key Technical Features

| Feature | Implementation |
|---|---|
| **Agentic reasoning** | LangGraph StateGraph: classify → retrieve → generate (2 LLM calls, explicit flow) |
| **Multi-source RAG** | 3 Qdrant collections: PDFs, websites, Excel |
| **Hybrid retrieval** | Vector similarity + BM25 lexical scoring combined |
| **Score threshold filtering** | Discards low-confidence chunks before LLM context assembly |
| **Adaptive web scraping** | BeautifulSoup → Playwright fallback for JS-heavy pages |
| **Deduplication** | Hash-based change detection prevents duplicate ingestion |
| **Graceful fallback** | Agent failure → traditional RAG pipeline |
| **Scheduled refresh** | Jobs to re-ingest websites and text files |

### Hybrid Retrieval Pipeline
The `get_relevant_chunks` method in [service/retriever_service.py](service/retriever_service.py) implements:

1. **Wide candidate fetch** — retrieves `k × HYBRID_FETCH_MULTIPLIER` candidates per collection
2. **Score threshold filter** — drops candidates with cosine distance > `RETRIEVAL_SCORE_THRESHOLD`
3. **BM25 scoring** — ranks survivors using keyword overlap (critical for exact section numbers like `610.3(b)`)
4. **Hybrid score** — `final = α × vector_relevance + (1-α) × bm25_relevance`
5. **Re-rank and return** — top-k across all collections sorted by final score, not collection order

All thresholds are tunable via environment variables — no code changes needed.

---

## Agent Tools

### BylawLookup
Searches the PDF collection for bylaw sections and regulations. Enriches the query with zone and lot context before searching, extracts section numbers from results, and returns structured data with confidence scores.

### FeeLookup
Searches the website collection for permit fee amounts. Applies keyword filtering to find fee-specific chunks (dollar amounts, cost tables) from the top candidates.

### General Search (fallback)
Cross-collection search when the query doesn't match a specialized tool.

---

## Data Sources

| Source | Collection | Loader |
|---|---|---|
| Local PDF bylaws | `pdf_index` | PyPDF |
| City website pages (40+) | `website_index` | BeautifulSoup / Playwright |
| Excel fee schedules | `excel_index` | Pandas |
| Text notes | `website_index` | TextLoader |

---

## Setup

### Prerequisites
- [Ollama](https://ollama.com/) running locally with `llama3` and `nomic-embed-text` models pulled
- Qdrant running locally (binary or Docker)

```bash
# Pull required models
ollama pull llama3
ollama pull nomic-embed-text

# Start Qdrant (Docker)
docker-compose up -d

# Or start Qdrant binary
C:\Tools\Qdrant\qdrant.exe --config-path C:\Tools\Qdrant\config.yaml
```

### Install & Ingest

```bash
python -m venv myenv
source myenv/bin/activate  # Windows: myenv\Scripts\activate
pip install -r requirements.txt
python -m playwright install

# Ingest data sources (order doesn't matter)
python manage.py ingest_pdfs      # place .pdf files in data/pdf/ first
python manage.py ingest_websites
python manage.py ingest_excel     # place .xlsx files in data/excel/ first
python manage.py ingest_texts     # place .txt files in data/processed/ first
```

### Run

```bash
uvicorn app.main:app --reload
```

### API

```bash
POST /chat
{"question": "What are the setback requirements for a garden suite?", "history": []}
```

---

## Configuration

All settings are in [config.py](config.py) and overridable via environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_MODEL` | `llama3` | LLM model name |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `RETRIEVAL_SCORE_THRESHOLD` | `0.65` | Max cosine distance to keep a chunk |
| `HYBRID_ALPHA` | `0.7` | Vector weight in hybrid score (0–1) |
| `HYBRID_FETCH_MULTIPLIER` | `3` | Candidate pool multiplier per collection |
| `EXCEL_MAX_ROWS_PER_SHEET` | `1000` | Row limit for Excel ingestion |

---

## Database Tools

```bash
# Detect and remove corrupted vectors
python database_tools/advanced_cleanup.py

# Inspect embedding distributions
python database_tools/peek_embeddings.py

# Scheduled refresh jobs
python jobs/refresh_websites.py
python jobs/refresh_texts.py
```

```powershell
# Delete and rebuild a collection
Invoke-RestMethod -Uri "http://localhost:6333/collections/pdf_index" -Method Delete
python manage.py ingest_pdfs
```

---

## Type Checking

```powershell
npx pyright
```
