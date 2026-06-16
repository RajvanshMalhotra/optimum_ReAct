"""
╔══════════════════════════════════════════════════════════════════════╗
║  OPTIMUM REACT — COOKBOOK 1: Plan-and-Execute Agent                 ║
║  How we built it, why, and when to use it                           ║
╚══════════════════════════════════════════════════════════════════════╝

Run this script:
    python cookbooks/01_plan_execute_agent.py

Requirements: GROQ_API_KEY and TAVILY_API_KEY in your .env file.
"""

# ── SECTION 1: The problem with ReAct for structured tasks ────────────────────
#
# ReAct (Reasoning + Acting) is the classic agent loop:
#
#   Observe → Think → Act → Observe → Think → Act → ...
#
# It works great for exploratory tasks but has a structural weakness:
# the model decides both WHAT to do and HOW to do it in the same step.
# For multi-step tasks, this leads to:
#
#   - Inconsistent step granularity (some steps too big, some trivial)
#   - No upfront plan = the model can "wander" before converging
#   - Each step re-reads the entire context, burning tokens on state management
#
# Plan-and-Execute fixes this with a clean separation of concerns:
#   PLANNER  → thinks in goals, never touches tools
#   EXECUTOR → executes one step at a time, never sees the full task
#
# Paper: "Plan-and-Solve Prompting" (Wang et al., 2023)
# https://arxiv.org/abs/2305.04091


# ── SECTION 2: The Planner (the core insight) ─────────────────────────────────
#
# The planner prompt is intentionally tool-free. By telling the model it cannot
# search the web during planning, we force it into pure strategic thinking:
#
#   "Given this goal, what ordered steps would a smart human take?"
#
# The output is a JSON plan like:
#   {
#     "goal": "understand battery tech for EVs",
#     "steps": [
#       "Research current leading EV battery chemistries",
#       "Compare energy density and cost for each chemistry",
#       "Identify which manufacturers use which chemistry",
#       "Summarize the winner for 2026 and why"
#     ]
#   }
#
# Notice: no "Step 1: search for X" — that's the executor's job.
# The planner thinks in goals. The executor figures out how.


# ── SECTION 3: The Executor (per-step, tool-aware) ───────────────────────────
#
# The executor gets one step at a time plus the results of all previous steps.
# It decides: can I complete this step from existing context, or do I need to
# search the web?
#
# Key design decision: executor gets PREVIOUS RESULTS, not the original task.
# This means each step is informed by what we already know — no redundant searches.
#
# When a step fails (tool error, empty result), the agent calls the REPLANNER:
# it only replans the REMAINING steps (not the completed ones). Max 2 replans
# to prevent infinite loops.


# ── SECTION 4: Using it via EZAgent ──────────────────────────────────────────

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from AgenT import EZAgent


async def main():
    print("=" * 60)
    print("Plan-and-Execute Agent — Live Demo")
    print("=" * 60)

    # One-line switch from ReAct to Plan-and-Execute:
    agent = EZAgent(architecture="plan_execute")

    # This task benefits from structured decomposition:
    # research → compare → synthesize is a natural 3-step plan.
    task = "What are the top 3 battery technologies for electric vehicles in 2026, and which manufacturers use each?"

    print(f"\nTask: {task}\n")
    print("Running Plan-and-Execute agent...\n")

    result = await agent.ask_async(task, max_steps=8)

    # plan_execute returns an AgentResult with .answer and .metrics
    print("─" * 60)
    print("ANSWER:")
    print("─" * 60)
    print(result.answer)

    print("\n─" * 60)
    print("METRICS:")
    print("─" * 60)
    m = result.metrics
    print(f"  Architecture:     {result.architecture}")
    print(f"  Total latency:    {m.total_latency_ms / 1000:.2f}s")
    print(f"  LLM calls:        {m.llm_calls}")
    print(f"  Tokens (est):     {m.total_tokens}")
    print(f"  Steps taken:      {m.steps_taken}")
    print(f"  Latency per step: {' → '.join(f'{ms:.0f}ms' for ms in m.latency_per_step)}")


# ── SECTION 5: When to use Plan-and-Execute ───────────────────────────────────
#
# USE Plan-and-Execute when:
#   ✓ The task decomposes naturally into sequential steps
#   ✓ You need predictable token cost (plan upfront = no wandering)
#   ✓ Steps are relatively independent (step 2 doesn't invalidate step 1)
#   ✓ Speed matters more than exploring multiple solution paths
#
# AVOID Plan-and-Execute when:
#   ✗ The task is highly dynamic (environment changes mid-execution)
#   ✗ You don't know how many steps are needed upfront
#   ✗ Early steps might completely change what later steps should do
#   ✗ You need to backtrack and try different approaches
#
# For those cases, try Tree of Thoughts (cookbook 02).
#
# Benchmark comparison:
#   ReAct          → 4–6s, 3–5 LLM calls, ~1800 tokens
#   Plan-and-Execute → 5–8s, 4–7 LLM calls, ~2500 tokens  (better quality)
#   Tree of Thoughts → 10–20s, 10–20 LLM calls, ~5000 tokens (best quality)


if __name__ == "__main__":
    asyncio.run(main())
