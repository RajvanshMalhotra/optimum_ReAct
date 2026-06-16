"""
ConsolidationService — Cluster/Reflect role (manage layer).

Reads batches of observed episodic records, groups them by shared entity or event
type, and generates provisional ReflectionRecords. Reflections are explicitly marked
CANDIDATE — they are not treated as truth until promoted by the PromotionService.

Clustering is intentionally simple (entity/event-type grouping, no ML) so the
system works without sentence-transformers. If an LLM function is provided, it
generates richer summary text; otherwise it falls back to a concatenation summary.
"""

import json
import uuid
from typing import Awaitable, Callable, Dict, List, Optional

from ..models import (
    AuditEntry,
    MemoryScope,
    MemoryStatus,
    ReflectionRecord,
    ReflectionType,
)
from ..store import MemoryStore

_CONSOLIDATION_PROMPT = """\
You are a memory consolidation agent. Below are {n} related episodic records from an AI agent system.

Records:
{records}

Generate a concise {reflection_type} in 2-3 sentences.
Focus on: recurring patterns, failure modes, durable lessons, or actionable rules.
Only include observations directly supported by the records above.

Output ONLY the consolidated insight, no preamble or labels."""


def _cluster_by_entity_or_type(records: List[Dict]) -> List[List[Dict]]:
    """
    Group records sharing a leading entity or the same event_type.
    Returns only clusters with ≥ 2 members.
    """
    buckets: Dict[str, List[Dict]] = {}
    for r in records:
        entities = json.loads(r.get("entities") or "[]")
        key = entities[0].lower() if entities else r.get("event_type", "observation")
        buckets.setdefault(key, []).append(r)
    return [v for v in buckets.values() if len(v) >= 2]


def _pick_reflection_type(event_types: List[str]) -> ReflectionType:
    if "failure" in event_types:
        return ReflectionType.FAILURE_PATTERN
    if len(set(event_types)) == 1:
        return ReflectionType.LESSON
    return ReflectionType.SUMMARY


class ConsolidationService:
    """Periodically clusters episodic memory and writes provisional reflections."""

    def __init__(
        self,
        store:      MemoryStore,
        llm_fn:     Optional[Callable[[str], Awaitable[str]]] = None,
        agent_name: str = "consolidation",
    ):
        self.store      = store
        self.llm_fn     = llm_fn
        self.agent_name = agent_name

    async def consolidate(
        self,
        project_id:  str   = "",
        session_id:  str   = "",
        since:       float = 0.0,
        max_records: int   = 50,
    ) -> List[ReflectionRecord]:
        rows = self.store.query_episodic(
            project_id=project_id,
            session_id=session_id,
            status=MemoryStatus.OBSERVED.value,
            since=since,
            limit=max_records,
        )
        if len(rows) < 2:
            return []

        clusters     = _cluster_by_entity_or_type(rows)
        reflections: List[ReflectionRecord] = []

        for cluster in clusters:
            reflection = await self._reflect(cluster, project_id, session_id)
            if reflection:
                self.store.save_reflection(reflection)
                for r in cluster:
                    self.store.update_status(r["id"], MemoryStatus.CLUSTERED)
                    self.store.log_audit(AuditEntry(
                        memory_id=r["id"],
                        action="clustered",
                        from_status=MemoryStatus.OBSERVED.value,
                        to_status=MemoryStatus.CLUSTERED.value,
                        agent=self.agent_name,
                        reason=f"cluster_id={reflection.cluster_id}",
                    ))
                reflections.append(reflection)

        return reflections

    async def _reflect(
        self, cluster: List[Dict], project_id: str, session_id: str
    ) -> Optional[ReflectionRecord]:
        if not cluster:
            return None

        cluster_id      = str(uuid.uuid4())[:8]
        event_types     = [r.get("event_type", "") for r in cluster]
        reflection_type = _pick_reflection_type(event_types)

        record_texts = "\n".join(
            f"[{i+1}] ({r.get('event_type', '')}): {r['content'][:300]}"
            for i, r in enumerate(cluster)
        )
        content = await self._call_llm(record_texts, reflection_type, len(cluster))
        if not content:
            # Fallback: deterministic concatenation summary
            content = (
                f"Observed pattern across {len(cluster)} events"
                + (" (includes failures)" if "failure" in event_types else "")
                + ": "
                + "; ".join(r["content"][:80] for r in cluster[:3])
            )

        reflection = ReflectionRecord(
            content=content,
            reflection_type=reflection_type,
            supporting_episodic_ids=[r["id"] for r in cluster],
            cluster_id=cluster_id,
            confidence=0.5,
            strength=min(0.9, 0.4 + len(cluster) * 0.1),
            project_id=project_id,
            session_id=session_id,
            source_agent=self.agent_name,
            scope=MemoryScope.PROJECT if project_id else MemoryScope.SESSION,
            scope_id=project_id or session_id,
            provenance=self.agent_name,
        )

        self.store.log_audit(AuditEntry(
            memory_id=reflection.id,
            action="reflect",
            from_status=None,
            to_status=reflection.status.value,
            agent=self.agent_name,
            reason=f"clustered {len(cluster)} episodes into {reflection_type.value}",
        ))
        return reflection

    async def _call_llm(self, records_text: str, rtype: ReflectionType, n: int) -> str:
        if not self.llm_fn:
            return ""
        prompt = _CONSOLIDATION_PROMPT.format(
            n=n, records=records_text, reflection_type=rtype.value
        )
        try:
            return (await self.llm_fn(prompt)).strip()
        except Exception:
            return ""
