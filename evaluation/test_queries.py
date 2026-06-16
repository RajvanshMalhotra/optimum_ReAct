"""
Benchmark query bank — 10 queries across 4 categories.

Categories are chosen to stress different agent strengths:
- factual: tests tool use + accuracy
- reasoning: tests multi-step decomposition
- current_events: tests web search + recency
- analysis: tests open-ended synthesis
"""

TEST_QUERIES = [
    # ── Factual lookup ────────────────────────────────────────────────────────
    {
        "id": "q1",
        "category": "factual",
        "query": "What are the key milestones of the ITER fusion project and when are they expected?",
    },
    {
        "id": "q2",
        "category": "factual",
        "query": "What are the current leading battery chemistries for electric vehicles in 2026?",
    },
    {
        "id": "q3",
        "category": "factual",
        "query": "What is the current state of quantum computing — what problems can it actually solve today?",
    },

    # ── Multi-step reasoning ──────────────────────────────────────────────────
    {
        "id": "q4",
        "category": "reasoning",
        "query": "Compare nuclear fusion vs fission as grid energy sources — cover pros, cons, cost, and realistic timelines.",
    },
    {
        "id": "q5",
        "category": "reasoning",
        "query": "A startup wants to build an AI coding assistant. What infrastructure choices matter most and what are the tradeoffs?",
    },
    {
        "id": "q6",
        "category": "reasoning",
        "query": "What are the concrete tradeoffs between RAG vs fine-tuning for a customer support AI system?",
    },

    # ── Current events ────────────────────────────────────────────────────────
    {
        "id": "q7",
        "category": "current_events",
        "query": "What are the most significant AI safety developments and regulations from 2025 to mid-2026?",
    },
    {
        "id": "q8",
        "category": "current_events",
        "query": "What major model releases and company moves happened at Anthropic, OpenAI, and Google DeepMind in 2026?",
    },

    # ── Open-ended analysis ───────────────────────────────────────────────────
    {
        "id": "q9",
        "category": "analysis",
        "query": "What should an early-stage AI infrastructure startup focus on to win its first 10 enterprise customers?",
    },
    {
        "id": "q10",
        "category": "analysis",
        "query": "Design a go-to-market strategy for a developer tool that reduces LLM API costs by 60%.",
    },
]
