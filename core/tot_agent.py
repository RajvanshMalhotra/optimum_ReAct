"""
Tree of Thoughts agent.

Key design decision: beam search (not full BFS) keeps token cost bounded.
At each depth level, N thoughts are generated per live node, all N*beam_width
candidates are scored in parallel, and only the top beam_width survive.

This means token cost scales as: depth * beam_width * n_thoughts * 2 LLM calls
(one for generation, one batch for scoring). With defaults (depth=4, B=2, N=3)
that's 4 * 2 * 3 * 2 = 48 LLM calls worst case — expensive but bounded.
"""
import time
import json
import re
from dataclasses import dataclass, field
from typing import List, Optional
from memory.hybrid import HybridMemory
from core.base_agent import BaseAgent, AgentResult, MetricsCollector


# ── Prompts ───────────────────────────────────────────────────────────────────

THOUGHT_GEN_PROMPT = """\
You are exploring multiple reasoning approaches for a complex task.

TASK: {task}

REASONING PATH SO FAR:
{path}

Generate {n} distinct next thoughts. Each should explore a DIFFERENT angle or approach.
Make each thought concrete — not "I should think about X" but "X works because Y".

Respond with valid JSON only:
{{"thoughts": ["thought 1", "thought 2", "thought 3"]}}"""


THOUGHT_SCORE_PROMPT = """\
Evaluate this reasoning step for solving the task.

TASK: {task}

REASONING PATH:
{path}

THIS THOUGHT: {thought}

Score on:
1. Does this thought move meaningfully toward a complete answer?
2. Is the reasoning specific and grounded (not vague)?
3. If we follow this path, could we reach a full answer soon?

Respond with valid JSON only:
{{"score": <1-10>, "reasoning": "brief justification", "complete": <true if this thought IS a complete answer to the task, false otherwise>}}"""


ANSWER_EXTRACT_PROMPT = """\
Based on this reasoning path, write a clear, complete final answer.

TASK: {task}

REASONING PATH:
{path}

BEST THOUGHT: {thought}

Final answer:"""


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class ThoughtNode:
    thought: str
    path: List[str] = field(default_factory=list)
    score: float = 0.0
    complete: bool = False
    depth: int = 0


# ── Agent ─────────────────────────────────────────────────────────────────────

class TreeOfThoughtsAgent(BaseAgent):

    ARCHITECTURE = "tot"

    def __init__(
        self,
        memory: HybridMemory,
        model: str = "",
        system_prompt: str | None = None,
        tools: list | None = None,
        n_thoughts: int = 3,
        beam_width: int = 2,
        max_depth: int = 4,
    ):
        super().__init__(memory, model, system_prompt, tools)
        self.n_thoughts = n_thoughts
        self.beam_width = beam_width
        self.max_depth = max_depth

    async def run(self, task: str, max_steps: int = 10) -> AgentResult:
        collector = MetricsCollector(self.model)
        wall_start = time.perf_counter()
        effective_depth = min(self.max_depth, max_steps)

        # Depth 0: generate and score root thoughts
        collector.start_step()
        root_thoughts = await self._generate_thoughts(task, [], collector)
        beam = [ThoughtNode(thought=t, path=[t], depth=0) for t in root_thoughts]
        beam = await self._score_nodes(task, beam, collector)
        beam = sorted(beam, key=lambda n: n.score, reverse=True)[: self.beam_width]
        collector.end_step()

        best_complete: Optional[ThoughtNode] = next((n for n in beam if n.complete), None)

        # Expand beam depth by depth
        for depth in range(1, effective_depth):
            if best_complete:
                break

            collector.start_step()
            candidates: List[ThoughtNode] = []

            for node in beam:
                new_thoughts = await self._generate_thoughts(task, node.path, collector)
                for t in new_thoughts:
                    candidates.append(
                        ThoughtNode(thought=t, path=node.path + [t], depth=depth)
                    )

            scored = await self._score_nodes(task, candidates, collector)
            beam = sorted(scored, key=lambda n: n.score, reverse=True)[: self.beam_width]
            collector.end_step()

            complete_nodes = [n for n in beam if n.complete]
            if complete_nodes:
                best_complete = max(complete_nodes, key=lambda n: n.score)

        # Extract answer from best node
        collector.start_step()
        best = best_complete or max(beam, key=lambda n: n.score)
        answer = await self._extract_answer(task, best, collector)
        collector.end_step()

        self.memory.save_session(task, answer[:300], time.perf_counter() - wall_start)
        return AgentResult(
            answer=answer,
            metrics=collector.finalize(wall_start),
            architecture=self.ARCHITECTURE,
        )

    async def _generate_thoughts(
        self, task: str, path: List[str], c: MetricsCollector
    ) -> List[str]:
        path_text = (
            "\n".join(f"  → {p}" for p in path) if path else "  (starting fresh)"
        )
        prompt = THOUGHT_GEN_PROMPT.format(task=task, path=path_text, n=self.n_thoughts)
        response = await c.llm_call(prompt, max_tokens=600)
        data = self._parse_json(response)
        thoughts = data.get("thoughts", []) if data else []
        return thoughts[: self.n_thoughts] or [f"Analyze the task: {task}"]

    async def _score_nodes(
        self, task: str, nodes: List[ThoughtNode], c: MetricsCollector
    ) -> List[ThoughtNode]:
        """Score all candidate nodes in a single parallel batch."""
        if not nodes:
            return nodes

        prompts = []
        for node in nodes:
            path_text = (
                "\n".join(f"  → {p}" for p in node.path[:-1])
                if len(node.path) > 1
                else "  (first step)"
            )
            prompts.append(
                THOUGHT_SCORE_PROMPT.format(
                    task=task, path=path_text, thought=node.thought
                )
            )

        responses = await c.batch_llm_call(prompts, max_tokens=250)

        for node, response in zip(nodes, responses):
            data = self._parse_json(response)
            if data:
                node.score = float(data.get("score", 5))
                node.complete = bool(data.get("complete", False))

        return nodes

    async def _extract_answer(
        self, task: str, best: ThoughtNode, c: MetricsCollector
    ) -> str:
        path_text = "\n".join(f"  → {p}" for p in best.path)
        prompt = ANSWER_EXTRACT_PROMPT.format(
            task=task, path=path_text, thought=best.thought
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
