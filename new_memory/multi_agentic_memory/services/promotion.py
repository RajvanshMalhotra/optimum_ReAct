"""
PromotionService — lifecycle transitions (manage layer).

Governs the critical path from reflection → semantic memory. A reflection is only
promoted when it meets the evidence threshold, confidence floor, strength floor,
and has no open conflicts. This gate prevents reflective summaries from hardening
into false rules prematurely.

Lifecycle transitions managed here:
  CANDIDATE → (promote) → VERIFIED (reflection) + ACTIVE (new SemanticRecord)
  ACTIVE    → (deprecate) → DEPRECATED (semantic)
  CANDIDATE → (reject) → REJECTED (reflection)
"""

import json
from typing import Optional

from ..models import AuditEntry, MemoryScope, MemoryStatus, SemanticRecord
from ..store import MemoryStore

_MIN_EVIDENCE_COUNT = 2
_MIN_CONFIDENCE     = 0.60
_MIN_STRENGTH       = 0.55


class PromotionService:
    def __init__(self, store: MemoryStore, agent_name: str = "promotion"):
        self.store      = store
        self.agent_name = agent_name

    # ── promotion ─────────────────────────────────────────────────────────────

    def evaluate_candidate(self, reflection_id: str) -> Optional[SemanticRecord]:
        """Check a reflection against promotion criteria; promote if it passes."""
        row = self.store.get_by_id(reflection_id)
        if not row or row["memory_type"] != "reflection":
            return None
        if row["status"] not in (MemoryStatus.CANDIDATE.value, MemoryStatus.VERIFIED.value):
            return None

        evidence   = json.loads(row.get("supporting_episodic_ids") or "[]")
        confidence = float(row.get("confidence") or 0)
        strength   = float(row.get("strength") or 0)

        if len(evidence) < _MIN_EVIDENCE_COUNT:
            return None
        if confidence < _MIN_CONFIDENCE:
            return None
        if strength < _MIN_STRENGTH:
            return None
        if self._has_open_conflict(reflection_id):
            return None

        return self._promote(row, evidence)

    def _promote(self, row: dict, evidence: list) -> SemanticRecord:
        semantic = SemanticRecord(
            content=row["content"],
            applicability_scope=row.get("applicability_scope") or "general",
            derived_from=[row["id"]] + evidence,
            verification_evidence=evidence,
            # Small confidence bump on promotion — it survived the gate
            confidence=min(0.95, float(row.get("confidence") or 0.6) + 0.15),
            project_id=row.get("project_id", ""),
            user_id=row.get("user_id", ""),
            source_agent=self.agent_name,
            scope=MemoryScope(row.get("scope") or "global"),
            scope_id=row.get("scope_id", ""),
            provenance=f"promoted_from:{row['id']}",
        )

        self.store.save_semantic(semantic)

        # Advance reflection to VERIFIED (version bump = new revision)
        self.store.update_status(row["id"], MemoryStatus.VERIFIED, version_bump=True)
        self.store.log_audit(AuditEntry(
            memory_id=row["id"],
            action="promoted",
            from_status=row["status"],
            to_status=MemoryStatus.VERIFIED.value,
            agent=self.agent_name,
            reason=f"promoted_to_semantic:{semantic.id}",
        ))
        self.store.log_audit(AuditEntry(
            memory_id=semantic.id,
            action="semantic_created",
            from_status=None,
            to_status=MemoryStatus.ACTIVE.value,
            agent=self.agent_name,
            reason=f"source_reflection:{row['id']}",
        ))
        return semantic

    # ── deprecation ───────────────────────────────────────────────────────────

    def deprecate_semantic(
        self,
        semantic_id:    str,
        reason:         str = "",
        superseded_by:  str = "",
    ):
        self.store.update_status(semantic_id, MemoryStatus.DEPRECATED, version_bump=True)
        if superseded_by:
            self.store.update_field(semantic_id, "superseded_by", superseded_by)
            self.store.update_field(semantic_id, "is_active", 0)
        self.store.log_audit(AuditEntry(
            memory_id=semantic_id,
            action="deprecated",
            from_status=MemoryStatus.ACTIVE.value,
            to_status=MemoryStatus.DEPRECATED.value,
            agent=self.agent_name,
            reason=reason,
        ))

    def reject_reflection(self, reflection_id: str, reason: str = ""):
        self.store.update_status(reflection_id, MemoryStatus.REJECTED, version_bump=True)
        self.store.log_audit(AuditEntry(
            memory_id=reflection_id,
            action="rejected",
            from_status=MemoryStatus.CANDIDATE.value,
            to_status=MemoryStatus.REJECTED.value,
            agent=self.agent_name,
            reason=reason,
        ))

    # ── batch ─────────────────────────────────────────────────────────────────

    def run_batch_promotions(self) -> int:
        """Promote all eligible candidate reflections. Returns count promoted."""
        rows     = self.store.query_reflections(status=MemoryStatus.CANDIDATE.value, limit=200)
        promoted = 0
        for row in rows:
            if self.evaluate_candidate(row["id"]):
                promoted += 1
        return promoted

    # ── helpers ───────────────────────────────────────────────────────────────

    def _has_open_conflict(self, record_id: str) -> bool:
        return any(
            c["record_a_id"] == record_id or c["record_b_id"] == record_id
            for c in self.store.get_open_conflicts()
        )
