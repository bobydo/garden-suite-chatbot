# Garden Suite Chatbot (Edmonton) — Qdrant + Ollama + LangChain (Agent-based)

## Features
- **Agent-based RAG**: Uses LangChain agents with specialized tools for precise information retrieval
- **Smart Tool Selection**: Automatically chooses the right tool (bylaw lookup, fee lookup, or general search) based on user queries
- **Fallback Support**: Falls back to traditional RAG if agent system fails
- **Real-time Data**: Tools query live Qdrant collections for up-to-date information

## Quick start

### Prerequisites
1. **Install Docker Desktop** (free): https://www.docker.com/products/docker-desktop/
   - Download and install for your OS (Windows/Mac/Linux)
   - Start Docker Desktop after installation
   
2. **Verify Docker works**:
   ```bash
   docker --version
   ```

### Setup Steps
```bash
# 1) Start Qdrant (Docker will auto-download the image)
# Option A: Simple command
docker run -p 6333:6333 qdrant/qdrant

# Option B: Using docker-compose (recommended - with data persistence)
docker-compose up -d

# 2) Install Python dependencies (includes new agent dependencies)
pip install -r requirements.txt

# 3) Ingest local PDFs (drop into data/pdf first)
python manage.py ingest_pdfs

# 4) Ingest City websites
python manage.py ingest_websites

# 5) (Optional) Ingest text notes in data/processed/*.txt
python manage.py ingest_texts

# 6) Test the tools integration (optional)
python test_tools.py

# 7) Run API
uvicorn app.main:app --reload
```

### Docker Management
```bash
# Stop Qdrant
docker-compose down          # If using docker-compose
# OR
docker stop <container-id>   # If using docker run

# Check if Qdrant is running
docker ps

# View Qdrant logs
docker logs <container-name>

# Access Qdrant web UI (optional)
# Open browser: http://localhost:6333/dashboard
```

## Agent Tools

### BylawLookup Tool
- **Purpose**: Find specific bylaw sections and regulations
- **Use cases**: "What is section 610?", "setback requirements", "zoning rules"
- **Returns**: Structured data with section numbers, regulatory text, and source URLs

### FeeLookup Tool  
- **Purpose**: Find current permit fees and costs
- **Use cases**: "development permit cost", "building permit fee", "application fees"
- **Returns**: Fee amounts, descriptive text, and official fee schedule URLs

### General Search Tool
- **Purpose**: Fallback for broad questions and general information
- **Use cases**: General garden suite questions not requiring specific tools

## Endpoints
- `POST /chat` → `{"question": "...", "history": []}`
  - Now uses intelligent agent that selects appropriate tools
  - Maintains backward compatibility with existing API

## Night Jobs
- `python jobs/refresh_websites.py`
- `python jobs/refresh_texts.py`

## System Architecture
- **Agent Layer**: LangChain ReAct agent with tool selection logic
- **Tools Layer**: Specialized search tools (`/tools/`) with real Qdrant integration  
- **Service Layer**: Class-based services in `/service/` for core functionality
- **Data Layer**: Qdrant vector DB with two collections: `bylaw_index` (PDFs) and `guides_index` (websites/texts)
- **Fallback**: Traditional RAG pipeline available if agent system fails

## Configuration
- Set `use_agents=False` in PipelineService to disable agent mode
- Agent system automatically falls back to RAG on errors
- All Qdrant/Ollama settings remain in `config.py` with environment variable overrides
