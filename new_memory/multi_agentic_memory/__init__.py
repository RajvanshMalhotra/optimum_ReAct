"""
multi_agentic_memory — production-grade memory subsystem for multi-agent LLM systems.

Architecture
────────────
  Write:   IngestService (Observer)        — raw events → EpisodicRecords
  Manage:  ConsolidationService            — episodic clusters → ReflectionRecords
           PromotionService                — reflection candidates → SemanticRecords
           ConflictService                 — contradiction detection + resolution
           GovernanceService               — policy, decay, audit, health
  Read:    RetrievalService (Executor)     — scoped, ranked WorkingMemory assembly

Memory lifecycle
────────────────
  observed → clustered → candidate → verified → active
                                   ↘ rejected
                                              ↘ deprecated / superseded

Quick start
───────────
  from new_memory.multi_agentic_memory import MemoryPipeline
  from new_memory.multi_agentic_memory.models import EventType

  pipeline = MemoryPipeline(db_path="agent.db")

  obs = pipeline.observer("planner")
  obs.record("User asked for EV battery comparison", EventType.USER_REQUEST,
             session_id="s1", task_id="t1", project_id="proj1")

  await pipeline.consolidate(project_id="proj1")
  pipeline.run_manage_cycle()

  wm = pipeline.retrieval.assemble(goal="EV battery", task_id="t1")
  print(wm.to_context_string())
"""

from .pipeline import MemoryPipeline
from .store import MemoryStore
from .models import (
    EpisodicRecord,
    ReflectionRecord,
    SemanticRecord,
    WorkingMemory,
    ConflictRecord,
    AuditEntry,
    MemoryType,
    MemoryStatus,
    MemoryScope,
    EventType,
    ReflectionType,
)
from .services import (
    IngestService,
    RetrievalService,
    ConsolidationService,
    PromotionService,
    ConflictService,
    GovernanceService,
)

__all__ = [
    "MemoryPipeline",
    "MemoryStore",
    "EpisodicRecord",
    "ReflectionRecord",
    "SemanticRecord",
    "WorkingMemory",
    "ConflictRecord",
    "AuditEntry",
    "MemoryType",
    "MemoryStatus",
    "MemoryScope",
    "EventType",
    "ReflectionType",
    "IngestService",
    "RetrievalService",
    "ConsolidationService",
    "PromotionService",
    "ConflictService",
    "GovernanceService",
]
