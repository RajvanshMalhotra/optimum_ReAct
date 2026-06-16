"""
Benchmark CLI — compare ReAct, Plan-and-Execute, and Tree of Thoughts.

Usage:
    python benchmark.py --query "What is the state of nuclear fusion?"
    python benchmark.py --all
    python benchmark.py --query "..." --agents react,tot
    python benchmark.py --all --output results/run_001.json
    python benchmark.py --query "..." --no-jury    # skip jury evaluation (faster)
"""
import asyncio
import argparse
import json
import time
import os
import sys
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv()

from memory.hybrid import HybridMemory
from core.base_agent import AgentResult
from evaluation.jury import JuryEvaluator, JuryVerdict
from evaluation.test_queries import TEST_QUERIES


# ── Colour helpers ────────────────────────────────────────────────────────────

def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"

def green(t):  return _c(t, "92")
def yellow(t): return _c(t, "93")
def cyan(t):   return _c(t, "96")
def bold(t):   return _c(t, "1")
def dim(t):    return _c(t, "2")
def red(t):    return _c(t, "91")


# ── Agent factory ─────────────────────────────────────────────────────────────

def _make_agent(arch: str, memory: HybridMemory, model: str = ""):
    from AgenT import EZAgent
    return EZAgent(memory_path=memory.store.db_path, architecture=arch, model=model)


# ── Single run ────────────────────────────────────────────────────────────────

async def run_single(
    query: str,
    architectures: List[str],
    model: str = "",
    run_jury: bool = True,
    jury_model: str = "",
) -> dict:
    results = {}

    for arch in architectures:
        print(f"\n{cyan(f'Running [{arch}]...')}")
        mem = HybridMemory(f"benchmark_{arch}.db")
        agent = _make_agent(arch, mem, model)

        try:
            result: AgentResult = await agent.ask_async(query)
            results[arch] = {
                "answer": result.answer if hasattr(result, "answer") else result,
                "metrics": None,
            }
            if hasattr(result, "metrics"):
                m = result.metrics
                results[arch]["metrics"] = {
                    "total_latency_ms": m.total_latency_ms,
                    "llm_calls": m.llm_calls,
                    "total_tokens": m.total_tokens,
                    "steps_taken": m.steps_taken,
                    "latency_per_step": m.latency_per_step,
                }
            print(green(f"  ✓ {arch} done"))
        except Exception as e:
            results[arch] = {"answer": f"ERROR: {e}", "metrics": None}
            print(red(f"  ✗ {arch} failed: {e}"))

    # Jury evaluation
    verdicts = {}
    if run_jury:
        print(f"\n{cyan('Running jury evaluation...')}")
        jury = JuryEvaluator(model=jury_model or model)
        for arch, data in results.items():
            if not data["answer"].startswith("ERROR"):
                try:
                    verdict = await jury.evaluate(query, data["answer"])
                    verdicts[arch] = verdict
                    print(green(f"  ✓ jury scored [{arch}]: {verdict.final_score}/10"))
                except Exception as e:
                    print(red(f"  ✗ jury failed for [{arch}]: {e}"))

    return {"query": query, "results": results, "verdicts": verdicts}


# ── Pretty print ──────────────────────────────────────────────────────────────

def _print_run(run: dict):
    query = run["query"]
    results = run["results"]
    verdicts = run["verdicts"]

    print(f"\n{bold('Query:')} {query}")
    print("─" * 72)
    print(f"{'Architecture':<18} {'Latency':>9} {'LLM Calls':>10} {'Tokens':>8} {'Jury':>8}")
    print("─" * 72)

    for arch, data in results.items():
        m = data.get("metrics") or {}
        v = verdicts.get(arch)

        latency = f"{m.get('total_latency_ms', 0)/1000:.1f}s" if m else "—"
        calls   = str(m.get("llm_calls", "—")) if m else "—"
        tokens  = str(m.get("total_tokens", "—")) if m else "—"
        score   = f"{v.final_score:.1f}/10" if v else "—"

        # Colour-code the score
        if v:
            score_str = (
                green(score) if v.final_score >= 7.5
                else yellow(score) if v.final_score >= 5.5
                else red(score)
            )
        else:
            score_str = score

        print(f"{arch:<18} {latency:>9} {calls:>10} {tokens:>8} {score_str:>18}")

    print("─" * 72)

    # Per-architecture details
    for arch, v in verdicts.items():
        print(f"\n{bold(arch)} jury breakdown:")
        print(f"  Accuracy:    {v.accuracy:.1f}/10")
        print(f"  Relevance:   {v.relevance:.1f}/10")
        print(f"  Conciseness: {v.conciseness:.1f}/10")
        print(f"  Score delta: {v.score_delta:.2f}  {dim('(how much adversary moved scores)')}")
        print(f"  {dim('Adversary:')} {v.adversary_critique[:200]}{'...' if len(v.adversary_critique) > 200 else ''}")

    # Latency-per-step detail
    for arch, data in results.items():
        m = data.get("metrics") or {}
        if m.get("latency_per_step"):
            steps = [f"{ms:.0f}ms" for ms in m["latency_per_step"]]
            print(f"\n{dim(arch + ' step latencies:')} {' → '.join(steps)}")


# ── CLI ───────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Benchmark Optimum ReAct agent architectures")
    parser.add_argument("--query", type=str, help="Single query to benchmark")
    parser.add_argument("--all", action="store_true", help="Run all 10 test queries")
    parser.add_argument(
        "--agents",
        type=str,
        default="react,plan_execute,tot",
        help="Comma-separated architectures (default: react,plan_execute,tot)",
    )
    parser.add_argument("--model", type=str, default="", help="Groq model override")
    parser.add_argument("--output", type=str, help="Save results to JSON file")
    parser.add_argument("--no-jury", action="store_true", help="Skip jury evaluation")
    args = parser.parse_args()

    if not args.query and not args.all:
        parser.error("Provide --query or --all")

    architectures = [a.strip() for a in args.agents.split(",")]
    run_jury = not args.no_jury

    queries = []
    if args.all:
        queries = [q["query"] for q in TEST_QUERIES]
        print(f"{bold('Running all 10 benchmark queries across:')} {', '.join(architectures)}\n")
    else:
        queries = [args.query]

    all_runs = []
    for i, query in enumerate(queries, 1):
        if len(queries) > 1:
            print(f"\n{bold(f'[{i}/{len(queries)}]')} {query[:70]}{'...' if len(query) > 70 else ''}")
        run = await run_single(
            query=query,
            architectures=architectures,
            model=args.model,
            run_jury=run_jury,
        )
        _print_run(run)
        all_runs.append(run)

    # Save to JSON if requested
    if args.output:
        os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
        serializable = []
        for run in all_runs:
            row = {"query": run["query"], "results": {}, "verdicts": {}}
            for arch, data in run["results"].items():
                row["results"][arch] = {
                    "answer": data["answer"],
                    "metrics": data.get("metrics"),
                }
            for arch, v in run["verdicts"].items():
                row["verdicts"][arch] = {
                    "final_score": v.final_score,
                    "accuracy": v.accuracy,
                    "relevance": v.relevance,
                    "conciseness": v.conciseness,
                    "score_delta": v.score_delta,
                    "adversary_critique": v.adversary_critique,
                }
            serializable.append(row)

        with open(args.output, "w") as f:
            json.dump({
                "run_at": datetime.utcnow().isoformat(),
                "architectures": architectures,
                "runs": serializable,
            }, f, indent=2)
        print(f"\n{green('Results saved to')} {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
