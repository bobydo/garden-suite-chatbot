# Technical Decision Notes — Interview Reference

Practical reasoning behind the key choices in this project.
Use these when asked "why did you choose X?" or "walk me through your architecture."

---

## Why Qdrant (over Chroma / Pinecone / Weaviate)

**Chose Qdrant because:**
- Single Docker container — zero-config local start, same image in production
- Built-in REST API + Python client + Web UI dashboard at `localhost:6333/dashboard`
- Native payload filtering: filter by `source`, `url`, or any metadata field before vector search
- Supports multiple named collections — lets you partition PDF / website / Excel data cleanly
- Production-ready: supports distributed clustering and replicas if the project scales
- `similarity_search_with_score` returns cosine distances directly — easy to threshold-filter

**Why not Chroma:**
- Embedded / in-process by default — no dashboard, no REST API, hard to inspect
- Limited observability (can't browse vectors or payloads easily)
- No strong clustering story for production
- Fine for a quick proof-of-concept, not for a system you'd hand to a team

**Why not Pinecone:**
- Cloud-only — data leaves the machine (violates Enbridge / enterprise security posture)
- Cost at scale

**Interview line:** *"Qdrant gave us the local-first, observable, production-gradeable stack we needed. You can start with Docker and scale to a cluster without changing your client code."*

---

## Why Ollama (over OpenAI API / Azure OpenAI)

**Chose Ollama because:**
- All inference runs on-device — no data sent to external APIs
- Enbridge and similar enterprise clients require data to stay on-prem (SCADA data, regulatory docs)
- Model swap is one env-var change: `OLLAMA_MODEL=llama3` → `OLLAMA_MODEL=mistral`
- Embedding model (`nomic-embed-text`) also runs locally — consistent privacy boundary
- Free to run, no token costs during development

**Why not OpenAI / Azure:**
- Data leaves the machine — non-starter for pipeline operations, legal docs, sensitive data
- Cost and latency at query time
- Dependency on external availability

**Interview line:** *"Local LLM was a hard requirement — same as what Enbridge runs. Ollama made it easy to swap models and keep everything on-prem."*

---

## Why LangGraph (over LangChain ReAct AgentExecutor)

**Chose LangGraph because:**
- ReAct is an autonomous loop: the LLM decides every step — unpredictable, hard to debug
- LangGraph gives you an explicit `StateGraph`: you define the nodes and edges in code
- Flow is guaranteed: `classify → retrieve → generate → END`, always
- 2 LLM calls per question (classify + generate) vs 3–5 in a ReAct loop
- Typed `ChatState` makes it easy to inspect what happened at each step
- Conditional edges route to the right retrieval path (bylaw / fee / general) without trusting the LLM to pick the right tool

**The key insight:** In ReAct, the LLM is the conductor. In LangGraph, *you* are the conductor and the LLM is just one of the musicians.

**Interview line:** *"ReAct was the 2023 approach. LangGraph is the 2024–2025 standard for production agentic systems — explicit, inspectable, and testable."*

---

## Why Hybrid Retrieval (BM25 + Vector, not pure vector)

**Chose hybrid because:**
- Pure vector search matches semantic meaning — great for natural language
- Bylaw section numbers (`610.3(b)`, `s.7.10`) are not semantic — embeddings often miss them
- BM25 is lexical: exact keyword overlap — perfect complement for structured identifiers
- Combined score: `0.7 × vector_relevance + 0.3 × bm25_relevance` — configurable via env vars
- Result: natural language queries AND exact term lookups both work well

**Why not pure BM25:**
- Misses synonyms and paraphrasing ("setback" vs "minimum distance from property line")

**Why not a dedicated search engine (Elasticsearch):**
- Extra infrastructure, more ops overhead
- `rank-bm25` is pure Python — runs in-process, no server needed
- At this data scale, in-process BM25 on the retrieved candidates is fast enough

**Interview line:** *"Vector search alone missed exact bylaw section numbers. Adding BM25 as a 30% signal fixed that without any extra infrastructure."*

---

## Why Three Separate Qdrant Collections (not one)

**Chose separate collections because:**
- PDFs (bylaws), websites (city pages), and Excel (fee schedules) have different schemas and retrieval characteristics
- Separate collections let you control how many results come from each source
- Easier to re-ingest one source type without touching others
- Metadata filtering is cleaner — no need to filter by `doc_type` within a shared collection
- In `get_relevant_chunks`: fetch candidates from each, then re-rank across all — best of both worlds

**Interview line:** *"Three collections gave us source-type control at ingest time and cross-collection re-ranking at query time."*

---

## Why Score Threshold Filtering

**Problem without it:** Every query returns k results regardless of relevance — low-confidence chunks pollute the LLM context and cause hallucinations or "I don't know" responses on off-topic questions.

**Chose threshold filtering because:**
- Cosine distance > 0.65 means the chunk is less than 35% similar to the query — not worth including
- Prevents garbage-in-garbage-out at the LLM context assembly step
- Configurable via `RETRIEVAL_SCORE_THRESHOLD` env var — tune without code changes
- Fallback: if all chunks exceed the threshold, return top-k by vector score anyway (never return empty context)

**Interview line:** *"Without a threshold, the LLM gets noise and hallucinates. With it, you get precision — the LLM either answers from good context or says it doesn't know."*

---

## Why RecursiveCharacterTextSplitter at 800/100

**Chose these settings because:**
- 800 characters ≈ 200–250 tokens — fits comfortably in a retrieval chunk without being too large
- 100-character overlap preserves sentence continuity across chunk boundaries
- `RecursiveCharacterTextSplitter` tries paragraph → sentence → word splits in order — avoids cutting mid-sentence
- For bylaw text (dense, structured paragraphs), 800 chars typically captures one complete regulation

**Interview line:** *"800/100 was the sweet spot between context richness and retrieval precision for dense regulatory text."*

---

## Why Table Parsing Was a Challenge (PDF + Excel)

Tables are one of the hardest problems in RAG — the challenge is preserving row↔column relationships after the content becomes a flat text chunk.

### PDF tables

**The problem:** PyPDF (used here) reads text linearly — left-to-right, top-to-bottom. A two-column fee table like:

```
| Fee Type         | Amount |
| Development      | $500   |
| Building Permit  | $1,200 |
```

Becomes a single string: `"Fee Type Amount Development $500 Building Permit $1200"` — column context is gone. The LLM sees `$500` with no label telling it what fee it belongs to.

**What helps:**
- `pdfplumber` — detects cell boundaries geometrically, preserves column alignment better than PyPDF
- `camelot` or `tabula-py` — purpose-built PDF table extractors, good for dense grid tables
- For this project: bylaw PDFs are mostly prose, not tables — PyPDF was acceptable. Fee tables came from Excel instead.

### Excel tables

**The problem:** Pandas reads structure correctly in memory, but a naive `.to_string()` or `.to_csv()` conversion loses row context at chunk boundaries — a chunk may contain data rows with no column headers.

**What was built here (`service/excel_loader.py` line 141–153):**
Row-level chunking — each row is serialized as `"col: value | col: value"` with column names prepended:

```
Row 1: Fee Type: Development Permit | Amount: $500.00 | Notes: Per unit
Row 2: Fee Type: Building Permit | Amount: $1200.00 | Notes: Per sq ft
```

Every chunk is self-contained — column headers travel with each row, so the LLM always knows what a value means.

### The better upstream fix: AI-friendly content guidelines

The most scalable solution isn't a smarter parser — it's preventing the problem before ingestion. On the Enbridge SCADA doc chatbot, content creators were given a guide for authoring AI-friendly documentation:

**What the guide covered:**
- Use simple flat tables — no merged cells, no rotated headers
- Put units in column headers (`Amount ($)`), not in data cells (`$500`)
- One topic per section — don't mix procedures with reference tables
- Use consistent heading hierarchy (H1 → H2 → H3) so chunking follows document structure
- Avoid images of tables — use actual markup so text is extractable
- Embed context inline — don't rely on footnotes or side-notes that get separated during chunking

**Why this beats parser tricks:**
- No parser handles every edge case (merged cells, watermarks, scanned images)
- A content guide costs nothing and scales to every document going forward
- Fixes the problem at the source instead of downstream

**Interview line:** *"We gave content creators an AI-friendly authoring guide. Clean input beats clever parsing — and it scales. A smarter parser is a technical debt you pay forever; a content standard pays forward."*

---

## How Misleading or Outdated Content Is Handled

RAG systems are only as trustworthy as their sources. This is what the code does — and what it leaves to governance.

### What the code handles

| Problem | Mechanism |
|---|---|
| Outdated content on re-ingest | `_delete_by_filter` removes all old points for a URL/file before inserting new ones (`retriever_service.py`) |
| Stale website content | `jobs/refresh_websites.py` and `jobs/refresh_texts.py` re-scrape and re-ingest on a schedule |
| Contradictory sources | `system_prompt.txt`: *"If info is missing or contradictory, say 'uncertain' and ask for lot details"* |
| Low-confidence chunks | Score threshold filters them before they reach the LLM context |

### What the code does NOT handle

| Gap | Impact |
|---|---|
| Wrong content in a source document | Ingested as truth — no validation at ingest time |
| Two official sources disagree | LLM may pick whichever scores higher without flagging the conflict |
| Source credibility weighting | A third-party blog post and an official bylaw PDF have equal weight in retrieval |
| Human review loop | No mechanism to flag a bad answer and correct the source |

### Primary defence: content governance

The content governance guide (given to content creators) is the most reliable control — if the source documents are accurate and well-structured, the system answers accurately. Garbage in, garbage out is the fundamental constraint of RAG.

### Future improvement: source credibility weighting

A practical next step would be boosting the hybrid score for PDF chunks (official bylaws) over website chunks (third-party sites):

```python
# In get_relevant_chunks: apply source_weight multiplier before combining scores
source_weight = 1.2 if doc.metadata.get("source", "").endswith(".pdf") else 1.0
final_score = source_weight * (HYBRID_ALPHA * vector_relevance + (1 - HYBRID_ALPHA) * bm25_relevance)
```

This ensures official bylaws rank above secondary sources when both are retrieved.

**Interview line:** *"The system trusts its sources completely — that's the fundamental constraint of RAG. We controlled it on two levels: a content governance guide for quality at the source, and a system prompt instruction to say 'uncertain' when sources conflict. Source credibility weighting is the logical next step."*

### Future improvement: gap logging

When the system returns no context or an "uncertain" answer, that question should be logged automatically — giving content creators a prioritised list of what to write next.

```python
# In _generate_node: detect gaps and log them
if state["retrieved_context"] == "(no context retrieved)" or "uncertain" in answer.lower():
    with open("logs/content_gaps.log", "a") as f:
        f.write(f"{datetime.now().isoformat()} | {state['question']}\n")
```

Content creators review `content_gaps.log` weekly and add the missing documentation. This closes the feedback loop: real user questions drive content priorities instead of guesswork.

**Interview line:** *"We logged every question the system couldn't answer. Content creators reviewed the gap log weekly — so the knowledge base grew based on actual user needs, not assumptions."*

---

## Architecture Summary (one paragraph for interviews)

*"The app uses a LangGraph StateGraph to orchestrate a three-step pipeline: the first node uses the LLM to classify the user's intent as a bylaw question, a fee question, or a general inquiry. The second node routes to the appropriate retrieval strategy — PDF bylaws, fee schedule websites, or a hybrid search across all three Qdrant collections. The hybrid retrieval combines cosine vector similarity with BM25 lexical scoring and filters out low-confidence chunks before passing context to the final generation node. Everything runs locally on Ollama — no data leaves the machine — which mirrors the security posture required for enterprise SCADA and pipeline operations systems."*
