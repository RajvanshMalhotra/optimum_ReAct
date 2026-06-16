from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# ── Enumerations ──────────────────────────────────────────────────────────────

class MemoryType(str, Enum):
    EPISODIC   = "episodic"
    REFLECTION = "reflection"
    SEMANTIC   = "semantic"


class MemoryStatus(str, Enum):
    # Lifecycle: observed → clustered → candidate → verified → active
    #            ↘ rejected   ↘ deprecated / superseded
    OBSERVED   = "observed"
    CLUSTERED  = "clustered"
    CANDIDATE  = "candidate"
    VERIFIED   = "verified"
    ACTIVE     = "active"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"
    REJECTED   = "rejected"


class MemoryScope(str, Enum):
    SESSION = "session"
    TASK    = "task"
    PROJECT = "project"
    USER    = "user"
    GLOBAL  = "global"


class EventType(str, Enum):
    USER_REQUEST   = "user_request"
    TOOL_CALL      = "tool_call"
    TOOL_OUTPUT    = "tool_output"
    AGENT_DECISION = "agent_decision"
    TASK_COMPLETE  = "task_complete"
    FAILURE        = "failure"
    OBSERVATION    = "observation"


class ReflectionType(str, Enum):
    SUMMARY         = "summary"
    HYPOTHESIS      = "hypothesis"
    POST_MORTEM     = "post_mortem"
    FAILURE_PATTERN = "failure_pattern"
    LESSON          = "lesson"


def _uid() -> str:
    return str(uuid.uuid4())


# ── Memory layers ─────────────────────────────────────────────────────────────

@dataclass
class EpisodicRecord:
    """Raw observation: what happened, when, from whom, with what confidence."""
    content:        str
    event_type:     EventType

    # Scope identifiers
    session_id:     str = ""
    task_id:        str = ""
    project_id:     str = ""
    user_id:        str = ""

    # Provenance
    source_agent:   str = ""
    provenance:     str = ""

    # Optional trace data
    raw_input:      str = ""
    raw_output:     str = ""
    tool_names:     List[str] = field(default_factory=list)
    entities:       List[str] = field(default_factory=list)
    tags:           List[str] = field(default_factory=list)

    # Trust signals
    salience:       float = 0.5
    confidence:     float = 0.9

    # Memory metadata
    scope:          MemoryScope   = MemoryScope.SESSION
    scope_id:       str           = ""
    evidence_links: List[str]     = field(default_factory=list)
    id:             str           = field(default_factory=_uid)
    memory_type:    MemoryType    = MemoryType.EPISODIC
    status:         MemoryStatus  = MemoryStatus.OBSERVED
    created_at:     float         = field(default_factory=time.time)
    updated_at:     float         = field(default_factory=time.time)
    version:        int           = 1


@dataclass
class ReflectionRecord:
    """Candidate abstraction from a cluster of episodic records. Provisional — not yet truth."""
    content:                 str
    reflection_type:         ReflectionType
    supporting_episodic_ids: List[str]

    cluster_id:              str       = ""
    strength:                float     = 0.5   # how many traces support this
    confidence:              float     = 0.5   # model confidence in the abstraction
    counterevidence_refs:    List[str] = field(default_factory=list)

    session_id:              str = ""
    task_id:                 str = ""
    project_id:              str = ""
    user_id:                 str = ""
    source_agent:            str = ""
    provenance:              str = ""

    scope:          MemoryScope   = MemoryScope.PROJECT
    scope_id:       str           = ""
    evidence_links: List[str]     = field(default_factory=list)
    id:             str           = field(default_factory=_uid)
    memory_type:    MemoryType    = MemoryType.REFLECTION
    status:         MemoryStatus  = MemoryStatus.CANDIDATE
    created_at:     float         = field(default_factory=time.time)
    updated_at:     float         = field(default_factory=time.time)
    version:        int           = 1


@dataclass
class SemanticRecord:
    """Verified long-term knowledge: durable facts and rules safe for reuse across tasks."""
    content:               str

    applicability_scope:   str       = "general"
    derived_from:          List[str] = field(default_factory=list)   # reflection + episodic IDs
    verification_evidence: List[str] = field(default_factory=list)
    is_active:             bool      = True
    superseded_by:         Optional[str] = None

    confidence:            float = 0.85
    entities:              List[str] = field(default_factory=list)
    tags:                  List[str] = field(default_factory=list)

    session_id:            str = ""
    task_id:               str = ""
    project_id:            str = ""
    user_id:               str = ""
    source_agent:          str = ""
    provenance:            str = ""

    scope:          MemoryScope   = MemoryScope.GLOBAL
    scope_id:       str           = ""
    evidence_links: List[str]     = field(default_factory=list)
    id:             str           = field(default_factory=_uid)
    memory_type:    MemoryType    = MemoryType.SEMANTIC
    status:         MemoryStatus  = MemoryStatus.ACTIVE
    created_at:     float         = field(default_factory=time.time)
    updated_at:     float         = field(default_factory=time.time)
    version:        int           = 1


@dataclass
class WorkingMemory:
    """Assembled context for a single task execution. Not stored — computed on demand."""
    task_id:          str
    goal:             str
    recent_episodes:  List[EpisodicRecord]   = field(default_factory=list)
    semantic_facts:   List[SemanticRecord]   = field(default_factory=list)
    reflection_hints: List[ReflectionRecord] = field(default_factory=list)
    assembled_at:     float = field(default_factory=time.time)
    token_budget_used: int  = 0

    def to_context_string(self) -> str:
        parts = [f"Goal: {self.goal}"]
        if self.semantic_facts:
            parts.append("\nVerified facts:")
            for f in self.semantic_facts:
                parts.append(f"  • {f.content}")
        if self.recent_episodes:
            parts.append("\nRecent relevant events:")
            for e in self.recent_episodes[:5]:
                parts.append(f"  [{e.event_type.value}] {e.content[:200]}")
        if self.reflection_hints:
            parts.append("\nPatterns / lessons (provisional — treat with caution):")
            for r in self.reflection_hints:
                parts.append(f"  ⚠  {r.content[:200]}")
        return "\n".join(parts)


# ── Support records ───────────────────────────────────────────────────────────

@dataclass
class ConflictRecord:
    record_a_id:   str
    record_b_id:   str
    conflict_type: str          = "contradiction"
    status:        str          = "open"
    resolution:    str          = ""
    id:            str          = field(default_factory=_uid)
    created_at:    float        = field(default_factory=time.time)
    resolved_at:   Optional[float] = None


@dataclass
class AuditEntry:
    memory_id:   str
    action:      str
    from_status: Optional[str]
    to_status:   Optional[str]
    agent:       str  = ""
    reason:      str  = ""
    id:          str  = field(default_factory=_uid)
    timestamp:   float = field(default_factory=time.time)
