# Optimum ReAct — Multi-Architecture Agent Design

**Date:** 2026-06-17  
**Status:** Approved

## Overview

Replace the single ReAct loop with a pluggable architecture system. Users select an agent architecture via `EZAgent(architecture="tot")`. Three architectures are available: `react` (existing baseline), `plan_execute` (new), and `tot` (new). All share a `BaseAgent` with built-in metrics. A CLI benchmark script compares all three using an adversarial jury evaluator.

## Architecture

### Agent Hierarchy

```
BaseAgent (core/base_agent.py)
  ├── IntelligentAgent  — react, existing v5, unchanged
  ├── PlanAndExecuteAgent — core/plan_execute_agent.py
  └── TreeOfThoughtsAgent — core/tot_agent.py
```

`EZAgent.architecture` param routes to the correct class. Default stays `"react"` for backwards compatibility.

### BaseAgent + MetricsCollector

`BaseAgent` is abstract. `MetricsCollector` wraps every LLM call via `_llm_call()` and `batch_llm_call()`, recording wall time and token estimates (chars/4). All agents return `AgentResult(answer, metrics, architecture)`.

### PlanAndExecuteAgent

Two-phase: `PLANNER_PROMPT` generates a 3–6 step JSON plan (no tools). `EXECUTOR_PROMPT` executes one step at a time with tool access. On tool failure, `REPLAN_PROMPT` regenerates remaining steps (max 2 replans). Final synthesis call combines step results.

### TreeOfThoughtsAgent

Beam search over thought tree. Parameters: `n_thoughts=3` (branching factor), `beam_width=2` (nodes kept per level), `max_depth=4`. Each depth level: generate N thoughts in parallel → score all in parallel → keep top B. Scoring returns `{score, complete}` — early exit when a complete node is found. Final answer extracted from best complete node.

## Evaluation

### Adversarial Jury (evaluation/jury.py)

3-round process:
1. **Round 1** — 3 jurors score independently in parallel (accuracy, conciseness, relevance)
2. **Round 2** — Adversary sees all scores and writes a structured critique
3. **Round 3** — Jurors revise scores after reading critique

Final score = weighted average of revised scores (accuracy 40%, relevance 35%, conciseness 25%). `score_delta` measures how much the adversary moved scores — used to calibrate jury strength.

### Benchmark CLI (benchmark.py)

```bash
python benchmark.py --query "..."          # single query
python benchmark.py --all                  # all 10 test queries
python benchmark.py --agents react,tot     # subset of architectures
python benchmark.py --all --output results/run.json
```

Outputs rich terminal table + optional JSON file.

## Cookbooks

Three runnable Python scripts in `cookbooks/`. Each teaches the architecture with inline comments, then runs a live example via `EZAgent`.

## Files

| File | Purpose |
|---|---|
| `core/base_agent.py` | BaseAgent + MetricsCollector + AgentResult |
| `core/plan_execute_agent.py` | PlanAndExecuteAgent |
| `core/tot_agent.py` | TreeOfThoughtsAgent |
| `evaluation/__init__.py` | package init |
| `evaluation/jury.py` | JuryEvaluator |
| `evaluation/test_queries.py` | 10 benchmark queries across 4 categories |
| `benchmark.py` | CLI runner |
| `cookbooks/01_plan_execute_agent.py` | P&E tutorial |
| `cookbooks/02_tot_agent.py` | ToT tutorial |
| `cookbooks/03_benchmark_and_jury.py` | Benchmarking tutorial |
| `AgenT.py` | Add `architecture=` param to `EZAgent` |
