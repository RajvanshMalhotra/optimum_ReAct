"""
IngestService — Observer role (write layer).

Records raw events faithfully as EpisodicRecords without over-interpreting them.
All writes are append-only: existing records are never mutated here.
"""

import re
import time
from typing import List, Optional

from ..models import AuditEntry, EpisodicRecord, EventType, MemoryScope, MemoryStatus
from ..store import MemoryStore

_ENTITY_RE = re.compile(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*\b")

_SALIENCE_BASE = {
    EventType.FAILURE:        0.90,
    EventType.AGENT_DECISION: 0.80,
    EventType.TASK_COMPLETE:  0.75,
    EventType.USER_REQUEST:   0.70,
    EventType.TOOL_OUTPUT:    0.60,
    EventType.TOOL_CALL:      0.50,
    EventType.OBSERVATION:    0.40,
}

_ERROR_KEYWORDS = frozenset(("error", "fail", "exception", "crash", "critical", "fatal"))


def _extract_entities(text: str) -> List[str]:
    return list(dict.fromkeys(_ENTITY_RE.findall(text)))[:10]


def _score_salience(event_type: EventType, content: str) -> float:
    base = _SALIENCE_BASE.get(event_type, 0.5)
    if any(kw in content.lower() for kw in _ERROR_KEYWORDS):
        base = min(1.0, base + 0.15)
    return base


class IngestService:
    """Observer: converts raw agent events into structured EpisodicRecords."""

    def __init__(self, store: MemoryStore, agent_name: str = "system"):
        self.store      = store
        self.agent_name = agent_name

    def record(
        self,
        content:    str,
        event_type: EventType,
        session_id:  str = "",
        task_id:     str = "",
        project_id:  str = "",
        user_id:     str = "",
        raw_input:   str = "",
        raw_output:  str = "",
        tool_names:  Optional[List[str]] = None,
        tags:        Optional[List[str]] = None,
        confidence:  float = 0.9,
        scope:       MemoryScope = MemoryScope.SESSION,
        scope_id:    str = "",
    ) -> EpisodicRecord:
        entities  = _extract_entities(content)
        salience  = _score_salience(event_type, content)
        scope_id  = scope_id or session_id

        rec = EpisodicRecord(
            content=content,
            event_type=event_type,
            session_id=session_id,
            task_id=task_id,
            project_id=project_id,
            user_id=user_id,
            source_agent=self.agent_name,
            provenance=self.agent_name,
            raw_input=raw_input,
            raw_output=raw_output,
            tool_names=tool_names or [],
            entities=entities,
            tags=tags or [],
            salience=salience,
            confidence=confidence,
            scope=scope,
            scope_id=scope_id,
        )

        self.store.save_episodic(rec)
        self.store.log_audit(AuditEntry(
            memory_id=rec.id,
            action="record",
            from_status=None,
            to_status=rec.status.value,
            agent=self.agent_name,
            reason=f"event_type={event_type.value}",
        ))
        return rec

    def record_tool_call(
        self,
        tool_name:  str,
        input_str:  str,
        output_str: str,
        session_id:  str = "",
        task_id:     str = "",
        project_id:  str = "",
        failed:     bool = False,
    ) -> EpisodicRecord:
        event_type = EventType.FAILURE if failed else EventType.TOOL_OUTPUT
        content = (
            f"Tool '{tool_name}' FAILED: {output_str[:300]}"
            if failed
            else f"Tool '{tool_name}': {output_str[:500]}"
        )
        return self.record(
            content=content,
            event_type=event_type,
            session_id=session_id,
            task_id=task_id,
            project_id=project_id,
            raw_input=input_str,
            raw_output=output_str,
            tool_names=[tool_name],
        )

    def record_decision(
        self,
        reasoning:  str,
        session_id:  str = "",
        task_id:     str = "",
        project_id:  str = "",
        confidence: float = 0.8,
    ) -> EpisodicRecord:
        return self.record(
            content=reasoning,
            event_type=EventType.AGENT_DECISION,
            session_id=session_id,
            task_id=task_id,
            project_id=project_id,
            confidence=confidence,
        )

    def record_failure(
        self,
        description: str,
        session_id:   str = "",
        task_id:      str = "",
        project_id:   str = "",
        raw_input:   str = "",
        raw_output:  str = "",
    ) -> EpisodicRecord:
        return self.record(
            content=description,
            event_type=EventType.FAILURE,
            session_id=session_id,
            task_id=task_id,
            project_id=project_id,
            raw_input=raw_input,
            raw_output=raw_output,
            confidence=0.95,  # failures are high-confidence observations
        )
