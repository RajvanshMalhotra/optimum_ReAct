"""
╔══════════════════════════════════════════════════════════════════════╗
║  OPTIMUM REACT — COOKBOOK 2: Tree of Thoughts Agent                 ║
║  Beam search over reasoning paths                                   ║
╚══════════════════════════════════════════════════════════════════════╝

Run this script:
    python cookbooks/02_tot_agent.py

Requirements: GROQ_API_KEY and TAVILY_API_KEY in your .env file.
"""

# ── SECTION 1: Why single-path reasoning fails ────────────────────────────────
#
# Both ReAct and Plan-and-Execute commit to a single reasoning path.
# Once the model takes step 1, it's locked in — even if a better path existed.
#
# This is fine for well-defined tasks ("find X, compare Y, summarize Z").
# It breaks on tasks with multiple valid approaches, where the best path
# isn't obvious upfront:
#
#   "Design a GTM strategy for a developer tool"
#   "What's the strongest argument for X?"
#   "How should we architect this system?"
#
# For these, the FIRST thought you have isn't necessarily the best one.
#
# Tree of Thoughts fixes this by exploring N paths simultaneously and keeping
# only the most promising ones — like a chess engine that evaluates multiple
# moves before committing.
#
# Paper: "Tree of Thoughts: Deliberate Problem Solving with LLMs" (Yao et al., 2023)
# https://arxiv.org/abs/2305.10601


# ── SECTION 2: The thought generator (branching) ──────────────────────────────
#
# At each depth level, for each surviving node in the beam, we generate N
# candidate next thoughts. The prompt explicitly asks for DIFFERENT angles:
#
#   "Generate 3 distinct next thoughts. Each should explore a DIFFERENT angle."
#
# This is critical — without this instruction, models generate 3 near-identical
# thoughts (high temperature alone doesn't give you genuine diversity).
#
# Example for query "Design a GTM strategy for a developer tool":
#
#   Thought 1: "Focus on open-source community first — developers trust
#               tools with public repos. Get 1000 GitHub stars before selling."
#
#   Thought 2: "Go bottom-up in enterprises: target individual developers,
#               help them succeed, let internal adoption drive the deal."
#
#   Thought 3: "Integrate with existing dev workflows first (VS Code, GitHub)
#               before any sales motion — distribution beats cold outreach."
#
# All three are legitimate approaches. Single-path reasoning would pick one.
# ToT explores all three.


# ── SECTION 3: The scorer + beam search (pruning) ────────────────────────────
#
# After generating N thoughts per node, we score ALL candidates in a single
# parallel batch call. The scorer outputs {score: 1-10, complete: bool}.
#
# "complete: true" means: this thought IS the final answer, no more expansion needed.
# This enables early exit — if a great complete answer appears at depth 2,
# we stop instead of burning tokens on depths 3 and 4.
#
# Beam search (beam_width=2) keeps only the top 2 nodes at each level.
# This is the cost control mechanism. Full BFS would keep ALL nodes, which
# with n_thoughts=3 gives you 3^depth nodes — 81 at depth 4. Too expensive.
#
# Beam width is the key tradeoff parameter:
#   beam_width=1 → greedy search (like ReAct, fast, cheap)
#   beam_width=2 → balanced (default, good quality/cost tradeoff)
#   beam_width=3 → better coverage, 50% more tokens than beam_width=2


# ── SECTION 4: Using it via EZAgent ──────────────────────────────────────────

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from AgenT import EZAgent


async def main():
    print("=" * 60)
    print("Tree of Thoughts Agent — Live Demo")
    print("=" * 60)

    # Configure ToT parameters explicitly, or just use defaults
    agent = EZAgent(
        architecture="tot",
        n_thoughts=3,    # branching factor: N candidate thoughts per node
        beam_width=2,    # beam width: nodes kept alive at each depth level
        max_depth=4,     # tree depth before forcing answer extraction
    )

    # This task benefits from exploring multiple strategic angles:
    task = "Design a go-to-market strategy for an AI developer tool that reduces LLM API costs by 60%."

    print(f"\nTask: {task}\n")
    print("Running Tree of Thoughts agent (this takes longer — exploring multiple paths)...\n")

    result = await agent.ask_async(task, max_steps=6)

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
    print(f"  LLM calls:        {m.llm_calls}  (high — parallel scoring)")
    print(f"  Tokens (est):     {m.total_tokens}")
    print(f"  Steps taken:      {m.steps_taken}")
    print(f"  Latency per step: {' → '.join(f'{ms:.0f}ms' for ms in m.latency_per_step)}")


# ── SECTION 5: Cost vs quality tradeoff table ─────────────────────────────────
#
#  n_thoughts × beam_width  │ LLM calls (depth=4) │ Quality │ Use case
#  ─────────────────────────┼────────────────────┼─────────┼──────────────────
#  3 × 1  (greedy)          │ ~8                 │  ★★★☆☆  │ Fast tasks, budget constrained
#  3 × 2  (default)         │ ~16                │  ★★★★☆  │ General use, good balance
#  3 × 3  (wide beam)       │ ~24                │  ★★★★★  │ High-stakes analysis
#  5 × 2  (wide branch)     │ ~24                │  ★★★★★  │ Creative/open-ended tasks
#
# Rule of thumb: if the jury score difference between tot and plan_execute
# is < 0.5 points, use plan_execute — the cost isn't worth it.


# ── SECTION 6: When to use Tree of Thoughts ──────────────────────────────────
#
# USE Tree of Thoughts when:
#   ✓ Multiple valid solution strategies exist and you don't know which is best
#   ✓ Quality matters more than speed or cost
#   ✓ Tasks are open-ended: strategy, design, analysis, creative work
#   ✓ You want the model to explore before committing
#
# AVOID Tree of Thoughts when:
#   ✗ The task is factual and well-defined (Plan-and-Execute is better)
#   ✗ You need a response in < 5 seconds
#   ✗ Token cost is tightly constrained
#   ✗ The task is short (single question, simple lookup)


if __name__ == "__main__":
    asyncio.run(main())
