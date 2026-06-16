"""
RetrievalService — Executor role (read layer).

Assembles a compact WorkingMemory for the current task by:
  1. Collecting verified semantic facts (global + project scope).
  2. Pulling recent episodic traces (narrow scope first: task → session → project).
  3. Keyword-matching goal terms against the store for anything missed.
  4. Optionally appending provisional reflection hints.
  5. Trimming to a token budget.

The retrieval order is intentional: narrowest scope first prevents context pollution
from unrelated tasks or other users' sessions.
"""

import json
from typing import Dict, List, Optional

from ..models import (
    EpisodicRecord,
    EventType,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    ReflectionRecord,
    ReflectionType,
    SemanticRecord,
    WorkingMemory,
)
from ..store import MemoryStore


# ── row → dataclass helpers ───────────────────────────────────────────────────

def _to_episodic(row: Dict) -> EpisodicRecord:
    r = EpisodicRecord(
        id=row["id"],
        content=row["content"],
        event_type=EventType(row.get("event_type") or "observation"),
        session_id=row.get("session_id", ""),
        task_id=row.get("task_id", ""),
        project_id=row.get("project_id", ""),
        salience=float(row.get("salience") or 0.5),
        confidence=float(row.get("confidence") or 0.5),
        source_agent=row.get("source_agent", ""),
    )
    r.status     = MemoryStatus(row["status"])
    r.created_at = float(row["created_at"])
    return r


def _to_reflection(row: Dict) -> ReflectionRecord:
    r = ReflectionRecord(
        id=row["id"],
        content=row["content"],
        reflection_type=ReflectionType(row.get("reflection_type") or "summary"),
        supporting_episodic_ids=json.loads(row.get("supporting_episodic_ids") or "[]"),
        confidence=float(row.get("confidence") or 0.5),
        strength=float(row.get("strength") or 0.5),
    )
    r.status = MemoryStatus(row["status"])
    return r


def _to_semantic(row: Dict) -> SemanticRecord:
    r = SemanticRecord(
        id=row["id"],
        content=row["content"],
        applicability_scope=row.get("applicability_scope") or "general",
        confidence=float(row.get("confidence") or 0.85),
        is_active=bool(row.get("is_active", 1)),
        superseded_by=row.get("superseded_by"),
    )
    r.status = MemoryStatus(row["status"])
    return r


# ── service ───────────────────────────────────────────────────────────────────

class RetrievalService:
    """Executor: scoped, ranked, budget-aware working-memory assembly."""

    def __init__(self, store: MemoryStore):
        self.store = store

    def assemble(
        self,
        goal:                   str,
        task_id:                str   = "",
        session_id:             str   = "",
        project_id:             str   = "",
        user_id:                str   = "",
        token_budget:           int   = 2000,
        include_reflections:    bool  = True,
        min_semantic_confidence: float = 0.7,
    ) -> WorkingMemory:
        wm = WorkingMemory(task_id=task_id, goal=goal)

        # 1. Verified semantic facts — global scope first, then project-scoped
        global_rows  = self.store.query_semantic(min_confidence=min_semantic_confidence, limit=8)
        project_rows = (
            self.store.query_semantic(
                scope=MemoryScope.PROJECT.value, scope_id=project_id,
                min_confidence=min_semantic_confidence - 0.1, limit=5,
            ) if project_id else []
        )
        seen_ids: set = set()
        for row in global_rows + project_rows:
            if row["id"] not in seen_ids:
                wm.semantic_facts.append(_to_semantic(row))
                seen_ids.add(row["id"])

        # 2. Recent episodic traces — narrow scope first
        wm.recent_episodes = self._get_scoped_episodes(task_id, session_id, project_id, limit=15)

        # 3. Keyword boost: find goal-relevant episodes we may have missed
        if goal and len(wm.recent_episodes) < 8:
            kw_rows = self.store.keyword_search(goal, memory_types=["episodic"], limit=6)
            ep_ids  = {e.id for e in wm.recent_episodes}
            for row in kw_rows:
                if row["id"] not in ep_ids:
                    wm.recent_episodes.append(_to_episodic(row))

        # Sort episodes by salience descending
        wm.recent_episodes.sort(key=lambda e: e.salience, reverse=True)

        # 4. Provisional reflection hints (treat with caution in prompts)
        if include_reflections and project_id:
            ref_rows = self.store.query_reflections(
                project_id=project_id,
                status=MemoryStatus.CANDIDATE.value,
                min_confidence=0.5,
                limit=4,
            )
            wm.reflection_hints = [_to_reflection(r) for r in ref_rows]

        # 5. Trim to token budget (rough estimate: 4 chars ≈ 1 token)
        wm.token_budget_used = len(wm.to_context_string()) // 4
        while wm.token_budget_used > token_budget and (wm.recent_episodes or wm.reflection_hints):
            if wm.reflection_hints:
                wm.reflection_hints.pop()
            elif wm.recent_episodes:
                wm.recent_episodes.pop()
            wm.token_budget_used = len(wm.to_context_string()) // 4

        return wm

    def _get_scoped_episodes(
        self, task_id: str, session_id: str, project_id: str, limit: int
    ) -> List[EpisodicRecord]:
        rows: List[Dict] = []

        # Scope expansion: task → session → project
        if task_id:
            rows += self.store.query_episodic(task_id=task_id, status="", limit=limit)
        if session_id and len(rows) < limit:
            rows += self.store.query_episodic(session_id=session_id, status="", limit=limit - len(rows))
        if project_id and len(rows) < limit:
            rows += self.store.query_episodic(project_id=project_id, status="", limit=limit - len(rows))

        # Deduplicate while preserving insertion order
        seen, result = set(), []
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                result.append(_to_episodic(r))
        return result[:limit]

    def search(
        self,
        query:        str,
        memory_types: Optional[List[str]] = None,
        limit:        int = 10,
    ) -> List[Dict]:
        """Raw keyword search across memory types. Returns store dicts."""
        return self.store.keyword_search(query, memory_types=memory_types, limit=limit)
