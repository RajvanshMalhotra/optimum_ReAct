"""Base agent class with built-in metrics collection for all architectures."""
import time
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from memory.hybrid import HybridMemory
from core.llm import llm_client
from tools.registry import tool_registry


@dataclass
class AgentMetrics:
    total_latency_ms: float = 0.0
    llm_calls: int = 0
    total_tokens: int = 0          # estimated: (prompt_chars + response_chars) / 4
    steps_taken: int = 0
    latency_per_step: List[float] = field(default_factory=list)   # ms
    tokens_per_step: List[int] = field(default_factory=list)


@dataclass
class AgentResult:
    answer: str
    metrics: AgentMetrics
    architecture: str = ""


class MetricsCollector:
    """
    Wraps every LLM call so agents get consistent latency + token tracking
    without instrumenting each call site manually.
    """

    def __init__(self, model: str):
        self.model = model
        self.metrics = AgentMetrics()
        self._step_start: Optional[float] = None

    def start_step(self):
        self._step_start = time.perf_counter()

    def end_step(self):
        if self._step_start is not None:
            elapsed_ms = (time.perf_counter() - self._step_start) * 1000
            self.metrics.latency_per_step.append(round(elapsed_ms, 1))
            self.metrics.steps_taken += 1
            self._step_start = None

    async def llm_call(self, prompt: str, max_tokens: int = 800) -> str:
        """Single LLM call — records token estimate and increments call count."""
        response = await llm_client.simple_prompt(prompt, max_tokens=max_tokens, model=self.model)
        est_tokens = (len(prompt) + len(response)) // 4
        self.metrics.llm_calls += 1
        self.metrics.total_tokens += est_tokens
        return response

    async def batch_llm_call(self, prompts: List[str], max_tokens: int = 500) -> List[str]:
        """Parallel LLM calls — used by ToT scorer to evaluate all nodes at once."""
        responses = await llm_client.batch_chat(prompts, max_tokens=max_tokens, model=self.model)
        for p, r in zip(prompts, responses):
            self.metrics.total_tokens += (len(p) + len(r)) // 4
        self.metrics.llm_calls += len(prompts)
        return responses

    def finalize(self, wall_start: float) -> AgentMetrics:
        self.metrics.total_latency_ms = round((time.perf_counter() - wall_start) * 1000, 1)
        return self.metrics


class BaseAgent(ABC):
    """
    Abstract base for all agent architectures.

    Subclasses implement run() and return AgentResult.
    MetricsCollector is instantiated per run() call so concurrent runs don't
    share state.
    """

    ARCHITECTURE = "base"

    def __init__(
        self,
        memory: HybridMemory,
        model: str = "",
        system_prompt: str | None = None,
        tools: list | None = None,
    ):
        self.memory = memory
        self.model = model.strip() if model.strip() else llm_client.model
        self.system_prompt = system_prompt or "You are a helpful AI agent."
        self.tools = tools or [
            {"name": "web_search", "description": "Search the internet for current information"}
        ]

    @abstractmethod
    async def run(self, task: str, max_steps: int = 10) -> AgentResult:
        ...

    def _format_tools(self) -> str:
        return "\n".join(f"- {t['name']}: {t['description']}" for t in self.tools)

    async def _execute_tool(self, tool_name: str, query: str):
        from models.agent import ToolResult
        if not tool_registry.has_tool(tool_name):
            return ToolResult(tool=tool_name, success=False, data=None, error="Tool unavailable")
        try:
            tool = tool_registry.get_tool(tool_name)
            return await tool.execute(query)
        except Exception as e:
            return ToolResult(tool=tool_name, success=False, data=None, error=str(e))
