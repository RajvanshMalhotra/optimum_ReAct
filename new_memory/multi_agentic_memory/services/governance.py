"""
GovernanceService — policy, trust calibration, decay, audit, and health.

Responsibilities:
  - Per-scope TrustPolicy (evidence thresholds, confidence floors).
  - Confidence decay for stale candidate reflections.
  - Hard purge of old rejected/deprecated records from active retrieval.
  - Health check for observability / monitoring.
  - Audit trail access.
"""

import time
from typing import Dict, List

from ..models import AuditEntry, MemoryStatus
from ..store import MemoryStore


class TrustPolicy:
    """Configurable promotion thresholds per memory scope."""

    def __init__(
        self,
        min_evidence:       int   = 2,
        min_confidence:     float = 0.60,
        min_strength:       float = 0.55,
        max_open_conflicts: int   = 0,
    ):
        self.min_evidence       = min_evidence
        self.min_confidence     = min_confidence
        self.min_strength       = min_strength
        self.max_open_conflicts = max_open_conflicts


# Defaults: stricter for widely-shared scopes, looser for task-local ones.
_DEFAULT_POLICIES: Dict[str, TrustPolicy] = {
    "global":  TrustPolicy(min_evidence=3, min_confidence=0.75, min_strength=0.65),
    "project": TrustPolicy(min_evidence=2, min_confidence=0.60, min_strength=0.55),
    "user":    TrustPolicy(min_evidence=2, min_confidence=0.60, min_strength=0.50),
    "session": TrustPolicy(min_evidence=1, min_confidence=0.50, min_strength=0.40),
    "task":    TrustPolicy(min_evidence=1, min_confidence=0.40, min_strength=0.30),
}


class GovernanceService:
    def __init__(self, store: MemoryStore):
        self.store    = store
        self.policies = dict(_DEFAULT_POLICIES)

    # ── policy ────────────────────────────────────────────────────────────────

    def set_policy(self, scope: str, **kwargs):
        self.policies[scope] = TrustPolicy(**kwargs)

    def get_policy(self, scope: str) -> TrustPolicy:
        return self.policies.get(scope, _DEFAULT_POLICIES["project"])

    # ── audit ─────────────────────────────────────────────────────────────────

    def get_audit_trail(self, memory_id: str) -> List[Dict]:
        return self.store.get_audit_trail(memory_id)

    def provenance_chain(self, memory_id: str) -> str:
        trail = self.store.get_audit_trail(memory_id)
        if not trail:
            return f"{memory_id}: no audit trail"
        lines = [f"Audit trail for {memory_id[:8]}:"]
        for entry in trail:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry["timestamp"]))
            lines.append(
                f"  {ts}  {entry['action']:<24} "
                f"{entry.get('from_status') or '—':>12} → {entry.get('to_status') or '—':<12} "
                f"[{entry.get('agent','')}]  {entry.get('reason','')[:60]}"
            )
        return "\n".join(lines)

    # ── health check ──────────────────────────────────────────────────────────

    def health_check(self) -> Dict:
        conn     = self.store._conn()
        rows     = conn.execute(
            "SELECT memory_type, status, COUNT(*) AS cnt "
            "FROM memory_records GROUP BY memory_type, status"
        ).fetchall()
        open_conflicts = len(self.store.get_open_conflicts())

        stats: Dict = {"by_type_status": {}, "open_conflicts": open_conflicts}
        for row in rows:
            key = f"{row['memory_type']}.{row['status']}"
            stats["by_type_status"][key] = row["cnt"]
        return stats

    def health_report(self) -> str:
        h = self.health_check()
        lines = ["Memory health:"]
        for k, v in sorted(h["by_type_status"].items()):
            lines.append(f"  {k:<36} {v:>5}")
        lines.append(f"  open conflicts: {h['open_conflicts']}")
        return "\n".join(lines)

    # ── decay ─────────────────────────────────────────────────────────────────

    def decay_stale_reflections(
        self,
        older_than_days: float = 30.0,
        confidence_drop: float = 0.10,
    ):
        """Reduce confidence of old unresolved candidate reflections."""
        threshold = time.time() - older_than_days * 86400
        conn      = self.store._conn()
        rows      = conn.execute(
            "SELECT id, confidence FROM memory_records "
            "WHERE memory_type='reflection' AND status='candidate' AND created_at < ?",
            (threshold,),
        ).fetchall()

        for row in rows:
            new_conf = max(0.0, float(row["confidence"]) - confidence_drop)
            self.store.update_field(row["id"], "confidence", new_conf)
            if new_conf < 0.2:
                self.store.update_status(row["id"], MemoryStatus.DEPRECATED)
                self.store.log_audit(AuditEntry(
                    memory_id=row["id"],
                    action="decayed_deprecated",
                    from_status=MemoryStatus.CANDIDATE.value,
                    to_status=MemoryStatus.DEPRECATED.value,
                    agent="governance",
                    reason=f"stale after {older_than_days:.0f} days, confidence fell to {new_conf:.2f}",
                ))

    # ── purge ─────────────────────────────────────────────────────────────────

    def purge_old_inactive(self, older_than_days: float = 90.0):
        """
        Hard-delete rejected/deprecated records older than the retention window.
        Raw episodic records are kept for auditability; only processed records
        with no active dependents are removed.
        """
        threshold = time.time() - older_than_days * 86400
        conn      = self.store._conn()
        deleted   = conn.execute(
            "DELETE FROM memory_records "
            "WHERE status IN ('rejected', 'deprecated') "
            "AND memory_type IN ('reflection', 'semantic') "
            "AND updated_at < ?",
            (threshold,),
        ).rowcount
        conn.commit()
        return deleted
