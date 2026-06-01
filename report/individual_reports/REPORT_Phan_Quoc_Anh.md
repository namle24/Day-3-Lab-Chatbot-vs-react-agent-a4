# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Phan Quốc Anh
- **Student ID**: 2A202600890
- **Date**: 1/6/2026
---

## I. Technical Contribution (15 Points)

This section summarizes concrete technical contributions made during the lab, including code modules implemented, integration points with the ReAct agent, and data ingestion work.

- **Implemented Modules and Changes**:
	- `src/rag/chunking.py`: redesigned chunking to use sentence tokenization and overlapping sliding-window chunks; added keyword extraction and support for structured vehicle documents.
	- `src/rag/store.py`: TF-IDF based RAG store with enriched metadata, search API, and `compare_models()` helper.
	- `src/services/chat_service.py`: added verification step to cross-check numeric claims against RAG results, improved fallback logic and user-facing messages, and attached sources when available.
	- `src/tools/vehicle_lookup.py` and `src/tools/registry.py`: tools formatting and helper functions for agent/tool integration.
	- Tests: adjusted `tests/test_local.py` to skip local LLM by default and updated `test_robustness.py` to match the revised fallback response format.

- **Data Ingestion / Web Scraping**:
	- Created `vinfast_rag_data.json` as the canonical data file used to build the RAG index.
	- Added (or planned) scripts to scrape official pages (HTML → JSON) and a loader script to import the produced JSON into the local DB and build the RAG index.

- **How it interacts with the ReAct loop**:
	- The ReAct agent calls `vehicle_lookup.lookup_vehicle()` or `compare_vehicles()` as tools during reasoning; results (observations) are used to verify claims before the assistant publishes numeric statements. If a claim cannot be verified, the service either prefixes the assistant reply with a warning or returns a conservative "no information" fallback.

---

## II. Debugging Case Study (10 Points)

This case study outlines a concrete failure observed during development, how it was diagnosed using logs and tests, and the root cause fix.

- **Problem Description**:
	- Merge conflicts between newly implemented sentence/window chunking and structured ingestion added in `main`. Tracked runtime artifacts (e.g. `data/vinfast.db`) caused merge/unlink problems. The LLM provider (Gemini) occasionally returned quota errors (HTTP 429), which triggered agent exceptions and fallback logic. Tests failed due to exact-string assertions after reply format changed.

- **Relevant Logs / Artifacts**:
	- Telemetry events: `AGENT_START` and `AGENT_ERROR_FALLBACK` recorded with error details (e.g., quota 429 messages).
	- Pytest outputs showed a failing assertion in `test_robustness.py` caused by a changed fallback reply wording.

- **Diagnosis**:
	- Merge conflicts arose because two feature sets modified the same modules (`src/rag/chunking.py`, `src/services/chat_service.py`).
	- Tracking runtime SQLite DB in git led to file-lock and merge issues; the DB should be excluded from version control.
	- The agent risked hallucination when an LLM returned numeric claims with no supporting evidence in the RAG index; this required a verification step.
	- Tests were brittle due to strict string matching; reply formatting changes caused false negatives.

- **Fix / Root Cause Remediation**:
	- Merged structured ingestion and new chunking by refactoring chunk creation into shared helper functions to avoid duplicate logic.
	- Removed runtime artifacts from git index (`git rm --cached data/vinfast.db data/rag_index.pkl`) and ensured `data/` is ignored in `.gitignore`.
	- Implemented verification: after the LLM produces an answer, the service checks RAG hits for numeric evidence; if evidence is missing or below a relevance threshold, the system either attaches a clear warning prefix or returns a conservative "No information in DB" reply.
	- Added a minimum relevance threshold for RAG hits (`MIN_RELEVANCE_SCORE`) to avoid using weak matches.
	- Adjusted tests to reflect the new reply format and reran the suite until green.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**: The `Thought`/Action/Observation pattern allows the agent to explicitly plan calls to tools, inspect observed results, and adapt the next step. This improves factual grounding when an external tool provides concrete evidence (e.g., pricing snippets). A pure chatbot must either memorize facts or hallucinate; ReAct lets the assistant consult authoritative sources during reasoning.

2. **Reliability**: The agent can perform worse in cases where provider availability is intermittent (API quota, rate limits) or where tool contracts are brittle. Without robust fallbacks and verification, the agent may produce inconsistent output. ReAct also increases integration complexity and surface area for bugs.

3. **Observation Influence**: Observations from RAG (snippets and scores) directly inform whether the agent publishes a numeric claim. High-confidence matches permit direct citation; low-confidence or absent matches trigger a conservative fallback or a request for clarification. This feedback loop reduces hallucinations.

---

## IV. Future Improvements (5 Points)

- **Scalability**: Move from TF-IDF to an embedding-based vector store (FAISS, Milvus, or a managed solution) for semantic retrieval at scale. Add asynchronous workers and queues for long-running or rate-limited tool calls.

- **Safety and Verification**: Add a supervisor/auditor LLM to validate critical claims, include a `verified` flag and `sources` list with every answer, and require explicit tool verification for numeric claims before publishing.

- **Reliability / Multi-provider**: Implement multi-provider failover (Gemini → OpenAI → local) with backoff and circuit-breaker patterns to reduce downtime.

- **Developer workflow**: Provide ingestion scripts and a reproducible `scripts/ingest.py` to rebuild `vinfast_rag_data.json` and the RAG index, and ensure runtime DB files are not tracked.

