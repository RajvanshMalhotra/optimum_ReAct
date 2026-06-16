"""
MemoryPipeline — main entry point for the multi-agent memory subsystem.

Implements the write-manage-read loop described in the architecture spec:

  WRITE  (Observer)   → pipeline.observer("agent").record(...)
  MANAGE (Cluster/Reflect + Promote + Govern) → await pipeline.consolidate(...)
                                                  pipeline.run_manage_cycle()
  READ   (Executor)   → pipeline.retrieval.assemble(goal=..., task_id=...)

All services share a single MemoryStore. The pipeline is the only object
external code needs to construct.

Example:
    from new_memory.multi_agentic_memory import MemoryPipeline
    from new_memory.multi_agentic_memory.models import EventType

    pipeline = MemoryPipeline(db_path="my_agent.db")

    # WRITE
    obs = pipeline.observer("planner")
    obs.record("User asked about battery tech", EventType.USER_REQUEST,
               session_id="s1", task_id="t1", project_id="proj1")

    # MANAGE (async — runs consolidation + conflict scan + promotion)
    await pipeline.consolidate(project_id="proj1")
    pipeline.run_manage_cycle()

    # READ
    wm = pipeline.retrieval.assemble(goal="battery technology", task_id="t1")
    print(wm.to_context_string())
"""

from __future__ import annotations

from typing import Awaitable, Callable, List, Optional

from .models import ReflectionRecord
from .services.conflict import ConflictService
from .services.consolidation import ConsolidationService
from .services.governance import GovernanceService
from .services.ingest import IngestService
from .services.promotion import PromotionService
from .services.retrieval import RetrievalService
from .store import MemoryStore


class MemoryPipeline:
    """Wires all six services together around a shared MemoryStore."""

    def __init__(
        self,
        db_path: str = "multi_agent_memory.db",
        llm_fn:  Optional[Callable[[str], Awaitable[str]]] = None,
    ):
        """
        Args:
            db_path: Path to the SQLite database file.
            llm_fn:  Optional async callable (str) → str used by ConsolidationService
                     to generate richer reflection text. If None, falls back to
                     deterministic concatenation summaries.
        """
        self.store   = MemoryStore(db_path)
        self._llm_fn = llm_fn

        # Expose all services as named attributes so callers can reach them directly.
        self.retrieval  = RetrievalService(self.store)
        self.promotion  = PromotionService(self.store)
        self.conflict   = ConflictService(self.store)
        self.governance = GovernanceService(self.store)

        # Consolidation holds the LLM reference internally.
        self._consolidation = ConsolidationService(self.store, llm_fn=llm_fn)

    # ── write ─────────────────────────────────────────────────────────────────

    def observer(self, agent_name: str = "agent") -> IngestService:
        """Return an IngestService bound to this pipeline's store."""
        return IngestService(self.store, agent_name=agent_name)

    # ── manage (async — may call the LLM) ─────────────────────────────────────

    async def consolidate(
        self,
        project_id:  str   = "",
        session_id:  str   = "",
        since:       float = 0.0,
    ) -> List[ReflectionRecord]:
        """
        Cluster observed episodic records → reflections, then scan for conflicts.
        Returns the list of new ReflectionRecords created.
        """
        reflections = await self._consolidation.consolidate(
            project_id=project_id,
            session_id=session_id,
            since=since,
        )
        # New reflections may conflict with existing semantic facts
        for r in reflections:
            self.conflict.scan_for_conflicts(r.id)
        return reflections

    def run_manage_cycle(self) -> dict:
        """
        Synchronous manage step (no LLM calls):
          1. Promote eligible candidate reflections to semantic memory.
          2. Decay stale reflection confidence.

        Returns a summary dict suitable for logging.
        """
        promoted = self.promotion.run_batch_promotions()
        self.governance.decay_stale_reflections()
        return {
            "promoted": promoted,
            "health":   self.governance.health_check(),
        }

    # ── read ──────────────────────────────────────────────────────────────────
    # Access via pipeline.retrieval.assemble(...) or pipeline.retrieval.search(...)

    # ── teardown ──────────────────────────────────────────────────────────────

    def close(self):
        self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
