"""
ConflictService — contradiction detection and resolution.

When a new reflection or semantic record is created, it is scanned against existing
active semantic memory for potential contradictions. Conflicts are stored in an open
queue and block promotion until resolved.

Resolution is explicit: a human or orchestrator decides which record to keep. The
losing record is deprecated and linked to the winner via superseded_by.

Detection is heuristic (keyword antonym pairs + shared entity overlap). A real system
would also use embedding cosine similarity or an LLM judge, but that's optional.
"""

import json
import time
from typing import List, Optional

from ..models import AuditEntry, ConflictRecord, MemoryStatus
from ..store import MemoryStore

# Pairs where one side contradicts the other
_ANTONYM_PAIRS = [
    ("always", "never"),
    ("must", "must not"),
    ("should", "should not"),
    ("enable", "disable"),
    ("increase", "decrease"),
    ("allow", "block"),
    ("recommended", "not recommended"),
]


def _likely_contradicts(text_a: str, text_b: str) -> bool:
    a, b = text_a.lower(), text_b.lower()
    for pos, neg in _ANTONYM_PAIRS:
        if (pos in a and neg in b) or (neg in a and pos in b):
            return True
    return False


def _shares_entities(entities_a: List[str], entities_b: List[str]) -> bool:
    set_a = {e.lower() for e in entities_a}
    set_b = {e.lower() for e in entities_b}
    return bool(set_a & set_b)


class ConflictService:
    def __init__(self, store: MemoryStore, agent_name: str = "conflict"):
        self.store      = store
        self.agent_name = agent_name

    def scan_for_conflicts(self, new_record_id: str) -> List[ConflictRecord]:
        """
        Compare a new candidate/semantic record against active semantic records.
        Returns a list of ConflictRecords that were flagged (already saved to store).
        """
        new_row = self.store.get_by_id(new_record_id)
        if not new_row:
            return []

        existing      = self.store.query_semantic(min_confidence=0.0, active_only=True, limit=200)
        new_entities  = json.loads(new_row.get("entities") or "[]")
        new_content   = new_row["content"]
        conflicts: List[ConflictRecord] = []

        for row in existing:
            if row["id"] == new_record_id:
                continue

            existing_entities = json.loads(row.get("entities") or "[]")
            same_scope = row.get("applicability_scope") == new_row.get("applicability_scope")

            # Only bother comparing records that share context
            if not (_shares_entities(new_entities, existing_entities) or same_scope):
                continue

            if _likely_contradicts(new_content, row["content"]):
                conflict = ConflictRecord(
                    record_a_id=new_record_id,
                    record_b_id=row["id"],
                    conflict_type="contradiction",
                )
                self.store.save_conflict(conflict)
                self.store.log_audit(AuditEntry(
                    memory_id=new_record_id,
                    action="conflict_flagged",
                    from_status=new_row.get("status"),
                    to_status=new_row.get("status"),
                    agent=self.agent_name,
                    reason=f"contradicts:{row['id']}",
                ))
                conflicts.append(conflict)

        return conflicts

    def resolve(
        self,
        conflict_id:     str,
        keep_id:         str,
        discard_id:      str,
        resolution_note: str = "",
    ):
        """
        Resolve a conflict by deprecating the losing record.
        Both the conflict queue entry and the losing record are updated atomically.
        """
        from .promotion import PromotionService
        PromotionService(self.store, agent_name=self.agent_name).deprecate_semantic(
            discard_id,
            reason=f"conflict_resolved:superseded_by={keep_id}",
            superseded_by=keep_id,
        )
        self.store.resolve_conflict(
            conflict_id,
            resolution=f"kept={keep_id} discarded={discard_id}. {resolution_note}".strip(),
        )

    def get_open_conflicts(self) -> List[dict]:
        return self.store.get_open_conflicts()

    def conflict_summary(self) -> str:
        open_c = self.get_open_conflicts()
        if not open_c:
            return "No open conflicts."
        lines = [f"Open conflicts: {len(open_c)}"]
        for c in open_c[:5]:
            lines.append(f"  {c['id'][:8]}: {c['record_a_id'][:8]} vs {c['record_b_id'][:8]} ({c['conflict_type']})")
        return "\n".join(lines)
