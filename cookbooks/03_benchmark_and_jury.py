"""
╔══════════════════════════════════════════════════════════════════════╗
║  OPTIMUM REACT — COOKBOOK 3: Benchmarking + Adversarial Jury        ║
║  How to measure what actually matters                               ║
╚══════════════════════════════════════════════════════════════════════╝

Run this script:
    python cookbooks/03_benchmark_and_jury.py

Requirements: GROQ_API_KEY and TAVILY_API_KEY in your .env file.
"""

# ── SECTION 1: Why LLM-as-judge fails ────────────────────────────────────────
#
# The naive evaluation approach: ask an LLM to score an answer 1–10.
# Problem: it's systematically biased.
#
# Observed biases in LLM judges (Zheng et al., 2023):
#   - Verbosity bias: longer answers score higher even when they're padded
#   - Sycophancy bias: confident-sounding answers score higher regardless of accuracy
#   - Self-similarity bias: models prefer answers that sound like themselves
#
# A single judge comparing "ReAct" vs "ToT" will consistently favour the ToT
# answer because it's longer and more elaborate — even if ReAct gave the right
# answer more efficiently.
#
# The result: your benchmark tells you which architecture produces the most
# verbose output, not which one is actually better.


# ── SECTION 2: The adversarial jury design ────────────────────────────────────
#
# Fix: 3 independent jurors + 1 adversary + a revision round.
#
#   Round 1: 3 jurors score independently (parallel)
#     - Accuracy juror:    is it factually correct?
#     - Conciseness juror: is it appropriately concise?
#     - Relevance juror:   does it answer the actual question?
#
#   Round 2: Adversary attacks
#     The adversary sees the answer AND all 3 initial scores.
#     Its job: find every flaw, gap, and unverified claim.
#     Crucially, it also challenges the JURORS ("are they being too lenient?")
#     This prevents the jurors from all agreeing on a mediocre answer.
#
#   Round 3: Revision
#     Each juror reads the adversary's critique and may revise their score.
#     They must justify any change. This filters out weak adversary arguments
#     (if the critique is vague, the juror won't move).
#
# The result: verbosity bias is broken (conciseness juror penalises padding),
# sycophancy is broken (adversary explicitly attacks confident-sounding claims).
#
# score_delta = average absolute shift in scores after adversarial challenge.
# High delta → jurors were initially too soft, adversary found real problems.
# Low delta  → jurors held their ground, answer was genuinely good.


# ── SECTION 3: Running a head-to-head benchmark ──────────────────────────────

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from AgenT import EZAgent
from evaluation.jury import JuryEvaluator


async def benchmark_query(query: str):
    print(f"\nQuery: {query}")
    print("─" * 64)

    jury = JuryEvaluator()
    architectures = ["react", "plan_execute", "tot"]
    results = {}

    # Run all three agents
    for arch in architectures:
        print(f"  Running [{arch}]...", end="", flush=True)
        agent = EZAgent(architecture=arch)
        try:
            result = await agent.ask_async(query, max_steps=6)
            answer = result.answer if hasattr(result, "answer") else result
            metrics = result.metrics if hasattr(result, "metrics") else None
            results[arch] = {"answer": answer, "metrics": metrics}
            print(f" done ({metrics.total_latency_ms/1000:.1f}s)" if metrics else " done")
        except Exception as e:
            results[arch] = {"answer": f"ERROR: {e}", "metrics": None}
            print(f" FAILED: {e}")

    # Run jury on all answers
    print("\n  Running adversarial jury...")
    verdicts = {}
    for arch, data in results.items():
        if not data["answer"].startswith("ERROR"):
            verdict = await jury.evaluate(query, data["answer"])
            verdicts[arch] = verdict

    # Print comparison table
    print(f"\n{'Architecture':<18} {'Latency':>9} {'LLM Calls':>10} {'Jury Score':>11}")
    print("─" * 52)
    for arch in architectures:
        data = results.get(arch, {})
        m = data.get("metrics")
        v = verdicts.get(arch)
        latency = f"{m.total_latency_ms/1000:.1f}s" if m else "—"
        calls   = str(m.llm_calls) if m else "—"
        score   = f"{v.final_score:.1f}/10" if v else "—"
        print(f"{arch:<18} {latency:>9} {calls:>10} {score:>11}")

    print("\n  Jury breakdown:")
    for arch, v in verdicts.items():
        print(f"    [{arch}] accuracy={v.accuracy:.1f} relevance={v.relevance:.1f} "
              f"conciseness={v.conciseness:.1f} delta={v.score_delta:.2f}")

    # Show adversary critique for the best-scoring architecture
    if verdicts:
        best_arch = max(verdicts, key=lambda a: verdicts[a].final_score)
        best_v = verdicts[best_arch]
        print(f"\n  Adversary critique on best answer [{best_arch}]:")
        print(f"  {best_v.adversary_critique[:300]}{'...' if len(best_v.adversary_critique) > 300 else ''}")

    return results, verdicts


async def main():
    print("=" * 64)
    print("Optimum ReAct — Benchmark + Adversarial Jury Demo")
    print("=" * 64)

    # A reasoning task where architecture choice meaningfully impacts quality
    query = "What are the key tradeoffs between RAG and fine-tuning for a customer support AI?"
    await benchmark_query(query)


# ── SECTION 4: Reading score_delta — calibrating your jury ───────────────────
#
# score_delta is the calibration signal for your jury setup.
#
# If score_delta is consistently 0.0 or very low:
#   → Your adversary is too weak. It's not finding real problems.
#   → Fix: Strengthen the adversary prompt. Add specific attack vectors:
#          "What data would disprove this claim? Is any of it verifiable?"
#
# If score_delta is consistently > 3.0:
#   → Your jurors are too soft. They move at any criticism.
#   → Fix: Strengthen the revision prompt. Add: "Only change your score
#          if the adversary cited a SPECIFIC, VERIFIABLE problem."
#
# A healthy score_delta range is 0.5–1.5.
# This means the adversary found real issues, but jurors pushed back on weak arguments.


# ── SECTION 5: When each architecture wins ───────────────────────────────────
#
# Based on benchmarking across the 10 standard queries:
#
#  Task type               │ Winner         │ Why
#  ────────────────────────┼────────────────┼──────────────────────────────────
#  Factual lookup          │ plan_execute   │ Clean decomposition: search → extract → summarize
#  Multi-step reasoning    │ tot            │ Explores multiple analytical angles
#  Current events          │ react          │ Fast, single search is enough
#  Open-ended analysis     │ tot            │ Strategic diversity matters here
#  Simple Q&A              │ react          │ Overkill to plan or branch
#
# General rule:
#   If jury_score(tot) - jury_score(plan_execute) < 0.5 → use plan_execute
#   If latency matters for your use case → use react or plan_execute
#   If quality is the only thing that matters → use tot


if __name__ == "__main__":
    asyncio.run(main())
