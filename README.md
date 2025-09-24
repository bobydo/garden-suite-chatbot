# Garden Suite Chatbot (Edmonton) — Qdrant + Ollama + LangChain (Class-based)

## Quick start
```bash
# 1) Start Qdrant (Docker)
docker run -p 6333:6333 qdrant/qdrant

# 2) Install deps
pip install -r requirements.txt

# 3) Ingest local PDFs (drop into data/pdf first)
python manage.py ingest_pdfs

# 4) Ingest City websites
python manage.py ingest_websites

# 5) (Optional) Ingest text notes in data/processed/*.txt
python manage.py ingest_texts

# 6) Run API
uvicorn app.main:app --reload
```

## Endpoints
- `POST /chat` → `{"question": "...", "history": []}`

## Night Jobs
- `python jobs/refresh_websites.py`
- `python jobs/refresh_texts.py`

## Structure
- Class-based services in `/service`
- Qdrant vector DB with two collections: `bylaw_index` (PDFs) and `guides_index` (websites/texts)
- Hash-based dedup & replacement before insert
