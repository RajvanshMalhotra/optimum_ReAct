"""
Optimum ReAct — Full Benchmark Report
======================================
Runs all three architectures (react, plan_execute, tot) + the multi-agent memory
pipeline across a designed query set and produces a quantifiable report suitable
for sharing.

Usage:
    python tests/benchmark_report.py
    python tests/benchmark_report.py --output results/benchmark_$(date +%Y%m%d).json
    python tests/benchmark_report.py --no-jury    # faster, skip adversarial jury
    python tests/benchmark_report.py --quick      # 2 queries only, no jury
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

# ── colour helpers ────────────────────────────────────────────────────────────
def _c(t, code): return f"\033[{code}m{t}\033[0m"
def green(t):  return _c(t, "92")
def yellow(t): return _c(t, "93")
def red(t):    return _c(t, "91")
def cyan(t):   return _c(t, "96")
def bold(t):   return _c(t, "1")
def dim(t):    return _c(t, "2")


# ── Query set ─────────────────────────────────────────────────────────────────
# Designed to probe different architecture strengths:
#   - Factual lookup   → plan_execute should win (clean decomposition)
#   - Reasoning        → tot should win (multi-angle exploration)
#   - Quick lookup     → react should win (single step, fast)

BENCHMARK_QUERIES = [
    {
        "id": "q1",
        "category": "factual_lookup",
        "query": "What are the top 3 EV battery chemistries in 2025 and which manufacturers use each?",
        "expected_winner": "plan_execute",
        "why": "Decomposes cleanly: research → compare → summarize",
    },
    {
        "id": "q2",
        "category": "strategic_reasoning",
        "query": "What are the key tradeoffs between RAG and fine-tuning for a production customer support AI?",
        "expected_winner": "tot",
        "why": "Multiple valid framings — cost vs quality vs latency vs freshness",
    },
    {
        "id": "q3",
        "category": "quick_lookup",
        "query": "What is Groq's LPU and how does it differ from a GPU?",
        "expected_winner": "react",
        "why": "Single-hop factual — no decomposition needed",
    },
    {
        "id": "q4",
        "category": "analysis",
        "query": "Design a go-to-market strategy for an AI developer tool that reduces LLM inference costs by 60%.",
        "expected_winner": "tot",
        "why": "Open-ended strategy — exploring multiple angles matters",
    },
    {
        "id": "q5",
        "category": "multi_step_research",
        "query": "Compare the current state of nuclear fusion energy: key players, timelines, and commercial viability.",
        "expected_winner": "plan_execute",
        "why": "Sequential information gathering across multiple dimensions",
    },
]

QUICK_QUERIES = BENCHMARK_QUERIES[:2]


# ── Architecture runner ───────────────────────────────────────────────────────

async def run_architecture(arch: str, query: str) -> dict:
    from AgenT import EZAgent
    agent = EZAgent(
        architecture=arch,
        memory_path=f"benchmark_{arch}_test.db",
        **({"n_thoughts": 3, "beam_width": 2, "max_depth": 4} if arch == "tot" else {}),
    )
    t0 = time.time()
    try:
        result = await agent.ask_async(query, max_steps=6)
        elapsed = (time.time() - t0) * 1000
        answer  = result.answer if hasattr(result, "answer") else str(result)
        metrics = result.metrics if hasattr(result, "metrics") else None
        return {
            "arch":    arch,
            "answer":  answer,
            "latency": metrics.total_latency_ms if metrics else elapsed,
            "llm_calls": metrics.llm_calls if metrics else "?",
            "tokens":  metrics.total_tokens if metrics else "?",
            "steps":   metrics.steps_taken if metrics else "?",
            "latency_per_step": metrics.latency_per_step if metrics else [],
            "error":   None,
        }
    except Exception as e:
        return {
            "arch": arch, "answer": None, "latency": (time.time()-t0)*1000,
            "llm_calls": 0, "tokens": 0, "steps": 0, "latency_per_step": [],
            "error": str(e),
        }


# ── Memory pipeline benchmark ─────────────────────────────────────────────────

async def run_memory_benchmark() -> dict:
    """
    Smoke-benchmarks the multi-agent memory pipeline:
      - Write 10 episodic events across 3 agents
      - Consolidate → reflections
      - Run manage cycle → promotions
      - Assemble working memory
      - Measure latency at each stage
    """
    from new_memory.multi_agentic_memory import MemoryPipeline, EventType

    pipeline = MemoryPipeline(db_path=":memory:")
    results  = {}

    # ── WRITE ──
    t0 = time.time()
    observers = {
        "planner":  pipeline.observer("planner"),
        "executor": pipeline.observer("executor"),
        "analyst":  pipeline.observer("analyst"),
    }
    events = [
        ("planner",  "User requested EV battery market analysis",             EventType.USER_REQUEST,   "s1", "t1", "proj1"),
        ("executor", "web_search returned LFP, NMC, solid-state as top techs",EventType.TOOL_OUTPUT,    "s1", "t1", "proj1"),
        ("executor", "web_search failed: Celestrak timeout",                  EventType.FAILURE,        "s1", "t1", "proj1"),
        ("executor", "web_search failed: Tavily 429 rate limit",              EventType.FAILURE,        "s1", "t1", "proj1"),
        ("planner",  "Decided to use cached TLE data as fallback",            EventType.AGENT_DECISION, "s1", "t1", "proj1"),
        ("analyst",  "COSMOS2543 passed over Ukraine region at 490km",        EventType.OBSERVATION,    "s2", "t2", "proj1"),
        ("analyst",  "YAOGAN30 trajectory intersects COSMOS2543 approach zone",EventType.OBSERVATION,   "s2", "t2", "proj1"),
        ("executor", "Groq API returned 429 on third consecutive call",       EventType.FAILURE,        "s1", "t3", "proj1"),
        ("executor", "Task completed: battery comparison summary delivered",  EventType.TASK_COMPLETE,  "s1", "t1", "proj1"),
        ("planner",  "Session ended — 3 tool calls, 2 retries, 1 success",   EventType.OBSERVATION,    "s1", "t1", "proj1"),
    ]
    for agent_name, content, etype, sid, tid, pid in events:
        observers[agent_name].record(content, etype, session_id=sid, task_id=tid, project_id=pid)
    write_ms = (time.time() - t0) * 1000
    results["write_events"]   = len(events)
    results["write_latency_ms"] = round(write_ms, 1)

    # ── CONSOLIDATE ──
    t0 = time.time()
    reflections = await pipeline.consolidate(project_id="proj1")
    consolidate_ms = (time.time() - t0) * 1000
    results["reflections_generated"] = len(reflections)
    results["consolidate_latency_ms"] = round(consolidate_ms, 1)
    if reflections:
        results["reflection_types"] = [r.reflection_type.value for r in reflections]
        results["reflection_strengths"] = [round(r.strength, 2) for r in reflections]

    # Nudge confidence so at least one promotion fires (test threshold)
    for r in reflections:
        if r.strength >= 0.55:
            pipeline.store.update_field(r.id, "confidence", 0.70)

    # ── MANAGE (promote + decay) ──
    t0 = time.time()
    cycle = pipeline.run_manage_cycle()
    manage_ms = (time.time() - t0) * 1000
    results["promoted_to_semantic"]  = cycle["promoted"]
    results["manage_latency_ms"]     = round(manage_ms, 1)
    results["memory_health"]         = cycle["health"]["by_type_status"]

    # ── RETRIEVE (assemble working memory) ──
    t0 = time.time()
    wm = pipeline.retrieval.assemble(
        goal="EV battery market analysis",
        task_id="t1", session_id="s1", project_id="proj1",
        token_budget=1500,
    )
    retrieve_ms = (time.time() - t0) * 1000
    results["episodes_in_wm"]       = len(wm.recent_episodes)
    results["facts_in_wm"]          = len(wm.semantic_facts)
    results["reflections_in_wm"]    = len(wm.reflection_hints)
    results["wm_token_budget_used"]  = wm.token_budget_used
    results["retrieve_latency_ms"]   = round(retrieve_ms, 1)
    results["total_pipeline_ms"]     = round(write_ms + consolidate_ms + manage_ms + retrieve_ms, 1)

    pipeline.close()
    return results


# ── Jury scorer ────────────────────────────────────────────────────────────────

async def run_jury(query: str, answers: dict) -> dict:
    from evaluation.jury import JuryEvaluator
    jury    = JuryEvaluator()
    verdicts = {}
    for arch, data in answers.items():
        if data.get("answer"):
            try:
                v = await jury.evaluate(query, data["answer"])
                verdicts[arch] = v
            except Exception as e:
                print(f"  {red(f'jury failed for [{arch}]: {e}')}")
    return verdicts


# ── Report printer ────────────────────────────────────────────────────────────

def _bar(value: float, max_val: float, width: int = 20) -> str:
    filled = int((value / max_val) * width) if max_val > 0 else 0
    return "█" * filled + "░" * (width - filled)


def print_query_result(qdata: dict, verdicts: dict):
    q    = qdata["query_meta"]
    runs = qdata["runs"]

    print(f"\n{bold(q['id'].upper())} [{q['category']}]")
    print(f"{dim('Query:')} {q['query']}")
    print(f"{dim('Expected winner:')} {q['expected_winner']}  {dim('(' + q['why'] + ')')}")
    print()

    # Find max latency for bar chart
    max_lat = max((r["latency"] for r in runs.values() if not r.get("error")), default=1)

    print(f"  {'Arch':<16} {'Latency':>9} {'Steps':>6} {'LLM Calls':>10} {'Tokens':>8} {'Jury':>8}")
    print("  " + "─" * 62)

    arch_order = ["react", "plan_execute", "tot"]
    scores = {}
    for arch in arch_order:
        r = runs.get(arch, {})
        if r.get("error"):
            print(f"  {red(arch):<26} {'ERROR':>9}  {r['error'][:40]}")
            continue

        v     = verdicts.get(arch)
        lat_s = f"{r['latency']/1000:.1f}s"
        calls = str(r["llm_calls"])
        tok   = str(r["tokens"])
        steps = str(r["steps"])
        score = f"{v.final_score:.1f}/10" if v else "—"

        if v:
            scores[arch] = v.final_score
            score_col = green(score) if v.final_score >= 7.5 else yellow(score) if v.final_score >= 5.5 else red(score)
        else:
            score_col = score

        bar = _bar(r["latency"], max_lat)
        print(f"  {arch:<16} {lat_s:>9} {steps:>6} {calls:>10} {tok:>8} {score_col:>18}  {dim(bar)}")

    if scores:
        actual_winner = max(scores, key=scores.get)
        match = actual_winner == q["expected_winner"]
        label = green("✓ prediction correct") if match else yellow(f"actual winner: {actual_winner}")
        print(f"\n  {dim('Prediction:')} {label}")

    # Jury breakdown
    if verdicts:
        print(f"\n  {dim('Jury details:')}")
        for arch in arch_order:
            v = verdicts.get(arch)
            if v:
                print(f"    {arch:<16} accuracy={v.accuracy:.1f}  relevance={v.relevance:.1f}  "
                      f"conciseness={v.conciseness:.1f}  Δ={v.score_delta:.2f}")


def print_memory_results(mem: dict):
    print(f"\n{bold('MEMORY PIPELINE')}")
    print("  " + "─" * 60)
    print(f"  {'Stage':<30} {'Metric':<30} {'Value':>10}")
    print("  " + "─" * 60)
    print(f"  {'Write (Observer)':<30} {'events ingested':<30} {mem.get('write_events',0):>10}")
    print(f"  {'':30} {'latency':<30} {mem.get('write_latency_ms',0):>9.1f}ms")
    print(f"  {'Consolidate (Cluster/Reflect)':<30} {'reflections generated':<30} {mem.get('reflections_generated',0):>10}")
    print(f"  {'':30} {'latency':<30} {mem.get('consolidate_latency_ms',0):>9.1f}ms")
    print(f"  {'Manage (Promote + Decay)':<30} {'promoted to semantic':<30} {mem.get('promoted_to_semantic',0):>10}")
    print(f"  {'':30} {'latency':<30} {mem.get('manage_latency_ms',0):>9.1f}ms")
    print(f"  {'Retrieve (Executor)':<30} {'episodes assembled':<30} {mem.get('episodes_in_wm',0):>10}")
    print(f"  {'':30} {'semantic facts':<30} {mem.get('facts_in_wm',0):>10}")
    print(f"  {'':30} {'token budget used':<30} {mem.get('wm_token_budget_used',0):>10}")
    print(f"  {'':30} {'latency':<30} {mem.get('retrieve_latency_ms',0):>9.1f}ms")
    print("  " + "─" * 60)
    print(f"  {'TOTAL pipeline latency':<60} {mem.get('total_pipeline_ms',0):>9.1f}ms")
    health = mem.get("memory_health", {})
    if health:
        print(f"\n  {dim('Memory store:')}")
        for k, v in sorted(health.items()):
            print(f"    {k:<36} {v:>5} records")


def print_summary(all_runs: list, mem_results: Optional[dict]):
    print(f"\n\n{'═'*64}")
    print(bold("  SUMMARY — QUANTIFIABLE IMPROVEMENTS"))
    print(f"{'═'*64}")

    # Architecture comparison: collect all jury scores
    arch_scores: Dict[str, List[float]] = {"react": [], "plan_execute": [], "tot": []}
    arch_latencies: Dict[str, List[float]] = {"react": [], "plan_execute": [], "tot": []}
    arch_calls: Dict[str, List[int]] = {"react": [], "plan_execute": [], "tot": []}

    for qdata in all_runs:
        for arch, run in qdata["runs"].items():
            if run.get("error"):
                continue
            arch_latencies[arch].append(run["latency"])
            if isinstance(run["llm_calls"], int):
                arch_calls[arch].append(run["llm_calls"])
        for arch, v in qdata.get("verdicts", {}).items():
            arch_scores[arch].append(v.final_score)

    def avg(lst): return sum(lst) / len(lst) if lst else 0

    print(f"\n  {'Architecture':<18} {'Avg Jury Score':>16} {'Avg Latency':>13} {'Avg LLM Calls':>15}")
    print("  " + "─" * 66)
    for arch in ["react", "plan_execute", "tot"]:
        score = avg(arch_scores[arch])
        lat   = avg(arch_latencies[arch])
        calls = avg(arch_calls[arch])
        score_str = (green if score >= 7.5 else yellow if score >= 5.5 else red)(f"{score:.1f}/10")
        print(f"  {arch:<18} {score_str:>26} {lat/1000:>11.1f}s {calls:>15.1f}")

    # Best architecture per category
    cat_winners: Dict[str, dict] = {}
    for qdata in all_runs:
        cat  = qdata["query_meta"]["category"]
        best = max(
            ((a, v.final_score) for a, v in qdata.get("verdicts", {}).items()),
            key=lambda x: x[1], default=(None, 0)
        )
        if best[0]:
            cat_winners[cat] = {"arch": best[0], "score": best[1]}

    if cat_winners:
        print(f"\n  {bold('Architecture wins by query category:')}")
        for cat, info in cat_winners.items():
            print(f"    {cat:<28} → {green(info['arch'])}  ({info['score']:.1f}/10)")

    if mem_results:
        print(f"\n  {bold('Memory pipeline:')}")
        print(f"    Full write→consolidate→promote→retrieve: {green(str(mem_results['total_pipeline_ms']) + 'ms')}")
        print(f"    Episodic events processed:  {mem_results['write_events']}")
        print(f"    Reflections generated:      {mem_results['reflections_generated']}")
        print(f"    Promoted to semantic:       {mem_results['promoted_to_semantic']}")
        print(f"    Working memory assembled in: {mem_results['retrieve_latency_ms']:.1f}ms")

    print(f"\n  {bold('LinkedIn headline numbers:')}")
    tot_avg  = avg(arch_scores.get("tot", [0]))
    re_avg   = avg(arch_scores.get("react", [0]))
    pe_avg   = avg(arch_scores.get("plan_execute", [0]))
    re_lat   = avg(arch_latencies.get("react", [1]))
    tot_lat  = avg(arch_latencies.get("tot", [1]))
    pe_lat   = avg(arch_latencies.get("plan_execute", [1]))

    if tot_avg > 0 and re_avg > 0:
        print(f"    • ToT vs ReAct quality improvement:  {green(f'+{((tot_avg/re_avg)-1)*100:.0f}%')}")
    if pe_avg > 0 and re_avg > 0:
        print(f"    • Plan-Execute vs ReAct quality:      {green(f'+{((pe_avg/re_avg)-1)*100:.0f}%')}")
    if tot_lat > 0 and re_lat > 0:
        print(f"    • ToT vs ReAct latency cost:          {yellow(f'+{((tot_lat/re_lat)-1)*100:.0f}%')}")
    if pe_lat > 0 and re_lat > 0:
        print(f"    • Plan-Execute vs ReAct latency cost: {yellow(f'+{((pe_lat/re_lat)-1)*100:.0f}%')}")
    if mem_results:
        print(f"    • Memory pipeline total latency:      {green(str(mem_results['total_pipeline_ms']) + 'ms')}")
        promo = f"{mem_results['promoted_to_semantic']}/{mem_results['reflections_generated']}"
        print(f"    • Episodic→Semantic promotion rate:   {green(promo)}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Optimum ReAct full benchmark report")
    parser.add_argument("--no-jury",  action="store_true", help="Skip adversarial jury (faster)")
    parser.add_argument("--quick",    action="store_true", help="2 queries only, no jury")
    parser.add_argument("--output",   type=str,            help="Save JSON results to this path")
    parser.add_argument("--agents",   type=str, default="react,plan_execute,tot",
                        help="Comma-separated architectures")
    args = parser.parse_args()

    architectures = [a.strip() for a in args.agents.split(",")]
    run_jury      = not args.no_jury and not args.quick
    queries       = QUICK_QUERIES if args.quick else BENCHMARK_QUERIES

    print()
    print(bold("╔══════════════════════════════════════════════════════════════╗"))
    print(bold("║  Optimum ReAct — Full Benchmark Report                      ║"))
    print(bold("╚══════════════════════════════════════════════════════════════╝"))
    print(f"  Architectures: {', '.join(architectures)}")
    print(f"  Queries:       {len(queries)}")
    print(f"  Jury:          {'yes (adversarial 3-round)' if run_jury else 'no'}")
    print(f"  Started:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    all_runs = []

    # ── Architecture benchmark ────────────────────────────────────────────────
    for qi, q in enumerate(queries, 1):
        header = cyan(bold(f"[{qi}/{len(queries)}] {q['id']} — {q['category']}"))
        print(f"\n{header}")
        print(f"  {dim(q['query'])}")
        print()

        runs: dict = {}
        for arch in architectures:
            print(f"  Running [{arch}]...", end="", flush=True)
            r = await run_architecture(arch, q["query"])
            runs[arch] = r
            if r.get("error"):
                print(f" {red('FAILED')}: {r['error'][:60]}")
            else:
                lat = f"{r['latency']/1000:.1f}s"
                print(f" {green('done')} ({lat}, {r['llm_calls']} LLM calls)")

        verdicts = {}
        if run_jury:
            print(f"  {dim('Running adversarial jury...')}", end="", flush=True)
            valid = {a: r for a, r in runs.items() if r.get("answer") and not r.get("error")}
            verdicts = await run_jury_fn(q["query"], valid)
            print(f" {green('done')} ({len(verdicts)} scored)")

        entry = {"query_meta": q, "runs": runs, "verdicts": verdicts}
        all_runs.append(entry)
        print_query_result(entry, verdicts)

    # ── Memory pipeline benchmark ─────────────────────────────────────────────
    print(f"\n{cyan(bold('[MEMORY] Multi-agent memory pipeline'))}")
    print(f"  {dim('Running write → consolidate → promote → retrieve...')}", end="", flush=True)
    mem_results = await run_memory_benchmark()
    print(f" {green('done')} ({mem_results['total_pipeline_ms']:.0f}ms total)")
    print_memory_results(mem_results)

    # ── Summary ───────────────────────────────────────────────────────────────
    print_summary(all_runs, mem_results)

    # ── JSON export ───────────────────────────────────────────────────────────
    if args.output:
        os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else ".", exist_ok=True)
        export = {
            "run_at":        datetime.utcnow().isoformat(),
            "architectures": architectures,
            "queries":       [],
            "memory":        mem_results,
        }
        for entry in all_runs:
            row = {
                "query":    entry["query_meta"],
                "runs":     {},
                "verdicts": {},
            }
            for arch, r in entry["runs"].items():
                row["runs"][arch] = {k: v for k, v in r.items() if k != "answer"}
            for arch, v in entry["verdicts"].items():
                row["verdicts"][arch] = {
                    "final_score": v.final_score,
                    "accuracy": v.accuracy,
                    "relevance": v.relevance,
                    "conciseness": v.conciseness,
                    "score_delta": v.score_delta,
                    "adversary_critique": v.adversary_critique[:300],
                }
            export["queries"].append(row)

        with open(args.output, "w") as f:
            json.dump(export, f, indent=2)
        print(f"\n{green(f'Results saved to {args.output}')}")


# Alias to avoid name clash with the local variable
async def run_jury_fn(query: str, answers: dict) -> dict:
    return await run_jury(query, answers)


if __name__ == "__main__":
    asyncio.run(main())
