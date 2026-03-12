# Improvements Log

## 2026-03-12 — LangGraph Agent Orchestration

### Problem
`AgentExecutor` (LangChain ReAct) let the LLM decide every step in an unpredictable loop (3–5 LLM calls per question). Flow was hard to debug, slow, and occasionally looped unnecessarily.

### Changes

#### `service/pipeline_service.py` — full rewrite
- Replaced `create_react_agent` + `AgentExecutor` with a **LangGraph `StateGraph`**
- Explicit 3-node graph: `classify → retrieve_[bylaw|fee|general] → generate → END`
- Typed `ChatState` carries `question`, `history`, `intent`, `retrieved_context`, `answer`
- **2 LLM calls per question** (classify + generate) vs previous 3–5 in ReAct loop
- Conditional edges route to `BylawLookup`, `FeeLookup`, or hybrid general search based on intent
- Retrieval nodes are pure Python (no LLM) — faster and cheaper
- Classify defaults to `"general"` on any LLM failure
- `use_agents` parameter kept as `_use_agents` for backwards API compatibility

#### `requirements.txt`
- Added `langgraph`

---

## 2026-03-12 — Content Gap Logging

### Problem
When the system couldn't answer a question (no context retrieved or uncertain answer), the failure was silent — content creators had no way to know what topics were missing from the knowledge base.

### Changes

#### `service/pipeline_service.py`
- Added `_log_gap_if_needed(question, context, answer)` called at the end of `_generate_node`
- Detects two gap conditions: `context == "(no context retrieved)"` or `"uncertain"` / `"i don't know"` in the answer
- Appends a timestamped line to `logs/content_gaps.log`: `ISO-timestamp | reason | question`
- `reason` is `no_context` or `uncertain_answer`
- Creates `logs/` directory if it doesn't exist

---

## 2026-03-12 — Hybrid Retrieval Quality Upgrade

### Problem
- `get_relevant_chunks` used basic `similarity_search` with no score filtering
- Results were concatenated in collection order (PDF → website → Excel), not by relevance
- No lexical/keyword matching — exact bylaw section numbers (e.g. `610.3(b)`) were poorly matched by embeddings alone

### Changes

#### `service/retriever_service.py`
- Switched from `similarity_search` to `similarity_search_with_score` across all 3 collections
- Added **score threshold filtering**: candidates with cosine distance > `RETRIEVAL_SCORE_THRESHOLD` are discarded before LLM context assembly
- Added **BM25 scoring** (`rank_bm25.BM25Okapi`) on filtered candidates — improves recall for exact terms and section numbers
- Added **hybrid scoring**: `final = α × vector_relevance + (1−α) × bm25_relevance`
- Results are now **re-ranked by hybrid score** across all collections (not collection order)
- Added threshold fallback: if all candidates are filtered, falls back to top-k by vector score with a warning log

#### `config.py`
- `RETRIEVAL_SCORE_THRESHOLD` (default `0.65`) — cosine distance cutoff, env-var overridable
- `HYBRID_ALPHA` (default `0.7`) — vector weight in hybrid score, env-var overridable
- `HYBRID_FETCH_MULTIPLIER` (default `3`) — candidate pool multiplier per collection, env-var overridable

#### `requirements.txt`
- Added `rank-bm25`

#### `README.md`
- Full rewrite: ASCII architecture diagram, local LLM / data privacy rationale, hybrid retrieval pipeline documentation, configuration reference table
