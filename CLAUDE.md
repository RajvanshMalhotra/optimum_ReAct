# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.


1. Think Before Coding
Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:

State your assumptions explicitly. If uncertain, ask.
If multiple interpretations exist, present them - don't pick silently.
If a simpler approach exists, say so. Push back when warranted.
If something is unclear, stop. Name what's confusing. Ask.
2. Simplicity First
Minimum code that solves the problem. Nothing speculative.

No features beyond what was asked.
No abstractions for single-use code.
No "flexibility" or "configurability" that wasn't requested.
No error handling for impossible scenarios.
If you write 200 lines and it could be 50, rewrite it.
Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

3. Surgical Changes
Touch only what you must. Clean up only your own mess.

When editing existing code:

Don't "improve" adjacent code, comments, or formatting.
Don't refactor things that aren't broken.
Match existing style, even if you'd do it differently.
If you notice unrelated dead code, mention it - don't delete it.
When your changes create orphans:

Remove imports/variables/functions that YOUR changes made unused.
Don't remove pre-existing dead code unless asked.
The test: Every changed line should trace directly to the user's request.

4. Goal-Driven Execution
Define success criteria. Loop until verified.

Transform tasks into verifiable goals:

"Add validation" → "Write tests for invalid inputs, then make them pass"
"Fix the bug" → "Write a test that reproduces it, then make it pass"
"Refactor X" → "Ensure tests pass before and after"
For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.



## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server (production entry point)
python api.py
# Or via uvicorn directly
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 1

# Run the agent interactively
python main.py

# Test the agent
python test.py
python final_test.py

# Build and run Docker
docker build -t agentic-app:latest .
docker run -d -p 8080:8000 --env-file .env agentic-app:latest
```

## Environment Variables

Required in `.env`:
```
GROQ_API_KEY=...       # From console.groq.com
TAVILY_API_KEY=...     # From tavily.com
```

Optional:
```
LLM_MODEL=llama-3.1-8b-instant   # Default model (see AVAILABLE_MODELS in api.py)
AGENT_DB_PATH=data/gotham_agent.db
PORT=8000
```

## Architecture

### Public Interface
`AgenT.py` exports `EZAgent` — the single entry point for all agent usage. Select the architecture via the `architecture=` param:

```python
EZAgent()                                    # react (default, backwards compatible)
EZAgent(architecture="plan_execute")         # Plan-and-Execute
EZAgent(architecture="tot", n_thoughts=3)    # Tree of Thoughts
```

All three return the same `.ask()` / `.ask_async()` interface. `plan_execute` and `tot` return `AgentResult` (with `.answer` and `.metrics`); `react` returns a plain string.

`IntelligentAgent` (aliased as `FastAgent`) from `core/agent.py` handles `react`.

```
EZAgent (AgenT.py)
  ├─ IntelligentAgent (core/agent.py)            ← react, v5, unchanged
  ├─ PlanAndExecuteAgent (core/plan_execute_agent.py)  ← new
  └─ TreeOfThoughtsAgent (core/tot_agent.py)     ← new
       │
       ├─ BaseAgent (core/base_agent.py)          ← shared abstract base + MetricsCollector
       ├─ HybridMemory (memory/hybrid.py)
       │    ├─ MemoryGraph (memory/graph.py)
       │    └─ MemoryStore (memory/store.py)
       ├─ LLMClient (core/llm.py)                ← global singleton
       └─ tool_registry (tools/registry.py)
            └─ SearchTool (tools/search_tool.py)
```

### New Architectures

**PlanAndExecuteAgent** (`core/plan_execute_agent.py`): Two LLM calls per cycle — `PLANNER_PROMPT` (no tools, produces JSON step list) and `EXECUTOR_PROMPT` (one step at a time, tool-aware). On tool failure, `REPLAN_PROMPT` regenerates remaining steps only (max 2 replans). Final synthesis call combines all step results into the answer.

**TreeOfThoughtsAgent** (`core/tot_agent.py`): Beam search over a thought tree. Each depth level generates `n_thoughts` candidates per live node (parallel), scores all candidates in a single batch call, keeps top `beam_width` nodes. `complete=true` from scorer triggers early exit. Parameters: `n_thoughts=3`, `beam_width=2`, `max_depth=4`.

**BaseAgent + MetricsCollector** (`core/base_agent.py`): Abstract base with `_llm_call()` / `batch_llm_call()` wrappers that record latency and token estimates per call. All agents return `AgentResult(answer, metrics, architecture)`.

**Adversarial Jury** (`evaluation/jury.py`): 3-round evaluation — Round 1: 3 jurors score in parallel (accuracy 40%, relevance 35%, conciseness 25%). Round 2: adversary attacks the answer and initial scores. Round 3: jurors revise after reading critique. `score_delta` measures adversary impact (healthy range: 0.5–1.5).

**Benchmark CLI** (`benchmark.py`): `python benchmark.py --query "..." --agents react,plan_execute,tot --output results/run.json`

**Cookbooks** (`cookbooks/`): Three runnable `.py` scripts. Each teaches the architecture internals through comments, then runs a live demo via `EZAgent`.

### Agent Loop (IntelligentAgent.run)
Each step calls `_think_intelligently()`, which sends a structured prompt to Groq and parses the JSON response `{reasoning, action, query, complete}`. Actions are: `web_search`, `ask_user`, `remember`, `recall`, `final_answer`. Web search results are stored in memory at importance=0.95 so the final answer synthesis step can retrieve them.

`_parse_json()` uses 4 sequential fallback strategies (direct parse → strip markdown → extract first `{}` block → fix unquoted keys). JSON parse failure defaults to a `web_search` on the task.

### Memory System (HybridMemory)
Two tiers: an in-memory `MemoryGraph` (networkx, capped at `MEMORY_MAX_GRAPH_NODES=50`) and `MemoryStore` (SQLite with FTS5). `recall()` searches the graph first, then falls back to SQLite FTS. `relate()` connects memory nodes by ID with a weight. `load_past_session_context()` seeds the graph with records from similar past sessions before each run.

### Production API (api.py — "Gotham Orbital")
FastAPI app with role-based agent pool. Agents are created lazily and cached by `(groq_key, model, role)` in the process-global `_agents` dict — **workers must be 1** or each worker gets its own empty pool.

Four roles: `atlas`, `orbital`, `news`, `analyst` — each gets a system prompt injected at construction time via `EZAgent(system_prompt=...)`.

A global `asyncio.Semaphore(1)` serializes all Groq calls to prevent 429 storms. Tasks are truncated to 4000 chars before sending. `ask_user` detection: the agent is instructed to emit `ASK_USER: <question>` (not call a tool). The API intercepts this pattern, stores the paused task as an in-memory session (TTL 10 min), and returns `{needs_input: true, question, session_id}`. The frontend resumes via `POST /agent/resume`.

### Key API Endpoints
- `GET /health` — readiness check
- `GET /models` — available Groq model list
- `POST /agent` — run a role agent (`atlas`/`orbital`/`news`/`analyst`)
- `POST /agent/resume` — resume a paused ask_user session
- `POST /intel-query` — ATLAS analysis with satellite snapshot + history
- `POST /ingest` — store a satellite position snapshot into memory
- `GET /tles` — fetch/cache TLEs from Celestrak (6h TTL, 200ms stagger between requests)

### Model Selection
`llama-3.1-8b-instant` is the default — 131k tok/min rate limit makes it suitable for multi-step agents. `llama-3.3-70b-versatile` hits its 12k tok/min limit quickly with multi-agent fan-outs. Model can be overridden per-request via `x-llm-model` header; `llm_client.api_key` is patched on every request so key rotation takes effect immediately on cached agents.

### Code History Warning
`core/agent.py` and `AgenT.py` contain many commented-out previous versions (v1–v4). The **active code is the uncommented block at the bottom** of each file (v5 for `core/agent.py`). Do not uncomment or modify the legacy blocks.

## Deployment
CD pipeline (`.github/workflows/cd.yaml`) SSHs into EC2, rebuilds the Docker image, restarts the container on port 8080→8000, and rolls back to the previous image tag if the `/health` check fails after 60s.
