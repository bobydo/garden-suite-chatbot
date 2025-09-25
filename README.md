# Garden Suite Chatbot (Edmonton) — Qdrant + Ollama + LangChain (Agent-based)

## Features
- **Agent-based RAG**: Uses LangChain agents with specialized tools for precise information retrieval
- **Smart Tool Selection**: Automatically chooses the right tool (bylaw lookup, fee lookup, or general search) based on user queries
- **Fallback Support**: Falls back to traditional RAG if agent system fails
- **Real-time Data**: Tools query live Qdrant collections for up-to-date information

### Setup Steps

#### For Local Qdrant Users:
```bash
# Start Qdrant locally with custom storage path (using config file)
C:\Tools\Qdrant\qdrant.exe --config-path C:\Tools\Qdrant\config.yaml
```

#### Common Steps (Both Docker and Local):
```bash
# 2) Install Python dependencies (includes new agent dependencies)
python -m venv myenv
pip install -r requirements.txt
pip install --force-reinstall -r requirements.txt

# 3) Ingest local PDFs (drop into da

# 4) Ingest City websites
python manage.py ingest_websites

# 5) (Optional) Ingest text notes in data/processed/*.txt
python manage.py ingest_texts

# 6) Test the tools integration (optional)
python test_tools.py

# 7) Run API
uvicorn app.main:app --reload
```

#### Local Qdrant Commands:
```bash
# Start Qdrant with custom storage location (using config file)
C:\Tools\Qdrant\start-qdrant.bat
Start-Sleep 3; curl "http://localhost:6333/collections"

# Check if Qdrant is running
Open browser: http://localhost:6333/
```

#### Both Methods:
```bash
# Access Qdrant web UI (optional)
Open browser: http://localhost:6333/dashboard
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

## Data Management

### Regular Jobs
- `python jobs/refresh_websites.py` - Refresh website content
- `python jobs/refresh_texts.py` - Refresh text files

### Cleanup & Reset
When you need to clear corrupted data or start fresh:

**Windows (PowerShell):**
```powershell
# Run interactive cleanup script
.\jobs\cleanup_qdrant.ps1

# Or use batch file
.\jobs\cleanup_qdrant.bat
```

**Manual API cleanup:**
```powershell
# Delete all collections
Invoke-RestMethod -Uri "http://localhost:6333/collections/website_index" -Method Delete
Invoke-RestMethod -Uri "http://localhost:6333/collections/bylaw_index" -Method Delete

# Verify cleanup
Invoke-RestMethod -Uri "http://localhost:6333/collections" -Method Get
```

**After cleanup, re-ingest data:**
```bash
python manage.py ingest_websites  # Clean HTML content only
python manage.py ingest_pdfs      # Process PDFs separately  
python manage.py ingest_texts     # Additional text files
```

## System Architecture
- **Agent Layer**: LangChain ReAct agent with tool selection logic
- **Tools Layer**: Specialized search tools (`/tools/`) with real Qdrant integration  
- **Service Layer**: Class-based services in `/service/` for core functionality
- **Data Layer**: Qdrant vector DB with two collections: `bylaw_index` (PDFs) and `website_index` (websites/texts)
- **Fallback**: Traditional RAG pipeline available if agent system fails

## Configuration
- Set `use_agents=False` in PipelineService to disable agent mode
- Agent system automatically falls back to RAG on errors
- All Qdrant/Ollama settings remain in `config.py` with environment variable overrides
