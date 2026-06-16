"""
Plan-and-Execute agent.

Key design decision: planner and executor are separate LLM calls with separate
system prompts. The planner never sees tools — it thinks in goals. The executor
never sees the full task — it executes one concrete step. This separation
prevents the model from trying to do everything in one shot.
"""
import time
import json
import re
from typing import List, Optional
from memory.hybrid import HybridMemory
from core.base_agent import BaseAgent, AgentResult, MetricsCollector


# ── Prompts ───────────────────────────────────────────────────────────────────

PLANNER_PROMPT = """\
You are a strategic planner. Your only job is to decompose a task into an ordered
execution plan. You do NOT execute anything — only plan.

RULES:
- 3 to 6 concrete, sequential steps
- Each step is a specific action: search for X, analyze Y, calculate Z, summarize W
- Steps must build on each other — later steps can reference earlier results
- Do not include tool calls — the executor handles that

TASK: {task}

Respond with valid JSON only:
{{"goal": "one-sentence goal", "steps": ["step 1", "step 2", "step 3"]}}"""


EXECUTOR_PROMPT = """\
You are a precise executor. Complete exactly ONE step of a plan.

OVERALL TASK: {task}
CURRENT STEP ({step_num} of {total_steps}): {step}

COMPLETED STEPS SO FAR:
{previous_results}

AVAILABLE TOOLS:
{tools}

AGENT ACTIONS (always available):
- final_answer: Deliver this step's result directly (no tool needed)

Decide: do you need to search the web, or can you complete this step from existing context?

Respond with valid JSON only:
{{"reasoning": "...", "action": "web_search|final_answer", "query": "search query if web_search", "result": "step result if final_answer"}}"""


REPLAN_PROMPT = """\
A step failed. Revise the remaining plan.

TASK: {task}
ORIGINAL STEPS: {original_steps}
COMPLETED SO FAR:
{completed}
FAILED STEP: {failed_step}
FAILURE REASON: {error}

Produce revised steps for the REMAINING work only (do not re-include completed steps).
Respond with valid JSON only:
{{"steps": ["revised step 1", "revised step 2"]}}"""


SYNTHESIS_PROMPT = """\
Synthesize a clear, comprehensive final answer from the completed work below.

TASK: {task}

COMPLETED STEPS AND RESULTS:
{results}

Provide a well-structured final answer:"""


# ── Agent ─────────────────────────────────────────────────────────────────────

class PlanAndExecuteAgent(BaseAgent):

    ARCHITECTURE = "plan_execute"

    def __init__(
        self,
        memory: HybridMemory,
        model: str = "",
        system_prompt: str | None = None,
        tools: list | None = None,
        max_replan_attempts: int = 2,
    ):
        super().__init__(memory, model, system_prompt, tools)
        self.max_replan_attempts = max_replan_attempts

    async def run(self, task: str, max_steps: int = 10) -> AgentResult:
        collector = MetricsCollector(self.model)
        wall_start = time.perf_counter()

        # Phase 1: Plan
        collector.start_step()
        plan = await self._generate_plan(task, collector)
        steps: List[str] = plan.get("steps", [task])[:max_steps]
        collector.end_step()

        completed_results: List[str] = []
        replan_count = 0
        i = 0

        # Phase 2: Execute step by step
        while i < len(steps):
            step = steps[i]
            collector.start_step()
            result, error = await self._execute_step(
                task, step, i + 1, len(steps), completed_results, collector
            )

            if error and replan_count < self.max_replan_attempts:
                replan_count += 1
                new_steps = await self._replan(
                    task, steps, completed_results, step, error, collector
                )
                if new_steps:
                    steps = steps[:i] + new_steps
                    collector.end_step()
                    continue

            completed_results.append(f"Step {i+1} [{step}]: {result or 'no result'}")
            collector.end_step()
            i += 1

        # Phase 3: Synthesize
        collector.start_step()
        answer = await self._synthesize(task, completed_results, collector)
        collector.end_step()

        self.memory.save_session(task, answer[:300], time.perf_counter() - wall_start)
        return AgentResult(
            answer=answer,
            metrics=collector.finalize(wall_start),
            architecture=self.ARCHITECTURE,
        )

    async def _generate_plan(self, task: str, c: MetricsCollector) -> dict:
        response = await c.llm_call(PLANNER_PROMPT.format(task=task), max_tokens=600)
        return self._parse_json(response) or {"steps": [task]}

    async def _execute_step(
        self,
        task: str,
        step: str,
        step_num: int,
        total: int,
        previous: List[str],
        c: MetricsCollector,
    ):
        prompt = EXECUTOR_PROMPT.format(
            task=task,
            step_num=step_num,
            total_steps=total,
            step=step,
            previous_results="\n".join(previous) if previous else "None yet",
            tools=self._format_tools(),
        )
        response = await c.llm_call(prompt, max_tokens=800)
        data = self._parse_json(response)

        if not data:
            return step, None

        if data.get("action") == "web_search":
            query = data.get("query") or step
            tool_result = await self._execute_tool("web_search", query)
            if tool_result.success:
                return str(tool_result.data)[:600], None
            return None, tool_result.error

        return data.get("result") or data.get("reasoning") or step, None

    async def _replan(
        self,
        task: str,
        original: List[str],
        completed: List[str],
        failed_step: str,
        error: str,
        c: MetricsCollector,
    ) -> List[str]:
        prompt = REPLAN_PROMPT.format(
            task=task,
            original_steps=json.dumps(original),
            completed="\n".join(completed) if completed else "None",
            failed_step=failed_step,
            error=error,
        )
        response = await c.llm_call(prompt, max_tokens=400)
        data = self._parse_json(response)
        return data.get("steps", []) if data else []

    async def _synthesize(self, task: str, results: List[str], c: MetricsCollector) -> str:
        prompt = SYNTHESIS_PROMPT.format(
            task=task,
            results="\n".join(results) if results else "No steps completed",
        )
        return await c.llm_call(prompt, max_tokens=1000)

    @staticmethod
    def _parse_json(response: str) -> Optional[dict]:
        for fn in [
            lambda r: json.loads(r.strip()),
            lambda r: json.loads(re.sub(r'```(?:json)?\s*|\s*```', '', r).strip()),
            lambda r: json.loads(re.search(r'\{.*?\}', r, re.DOTALL).group(0)),
        ]:
            try:
                return fn(response)
            except Exception:
                pass
        return None
