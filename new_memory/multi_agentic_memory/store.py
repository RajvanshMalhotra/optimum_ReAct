"""
SQLite-backed storage layer for the multi-agent memory subsystem.

Schema design:
  - One flat table (memory_records) for all memory types — keeps JOINs simple
    and lets us add new types without schema migrations.
  - Separate audit_log (append-only) and conflicts tables.
  - Secondary indexes on the most common query dimensions.
  - Thread-local connections so the store is safe from multiple agent threads.
"""

import json
import sqlite3
import threading
import time
from typing import Dict, List, Optional

from .models import (
    AuditEntry,
    ConflictRecord,
    EpisodicRecord,
    MemoryStatus,
    ReflectionRecord,
    SemanticRecord,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_records (
    id                    TEXT PRIMARY KEY,
    memory_type           TEXT    NOT NULL,
    status                TEXT    NOT NULL,
    content               TEXT    NOT NULL,
    created_at            REAL    NOT NULL,
    updated_at            REAL    NOT NULL,
    version               INTEGER DEFAULT 1,
    confidence            REAL    DEFAULT 0.5,
    scope                 TEXT    NOT NULL DEFAULT 'session',
    scope_id              TEXT    DEFAULT '',
    provenance            TEXT    DEFAULT '',
    session_id            TEXT    DEFAULT '',
    task_id               TEXT    DEFAULT '',
    project_id            TEXT    DEFAULT '',
    user_id               TEXT    DEFAULT '',
    source_agent          TEXT    DEFAULT '',
    -- episodic
    event_type            TEXT    DEFAULT '',
    raw_input             TEXT    DEFAULT '',
    raw_output            TEXT    DEFAULT '',
    tool_names            TEXT    DEFAULT '[]',
    entities              TEXT    DEFAULT '[]',
    tags                  TEXT    DEFAULT '[]',
    salience              REAL    DEFAULT 0.5,
    -- reflection
    cluster_id            TEXT    DEFAULT '',
    reflection_type       TEXT    DEFAULT '',
    strength              REAL    DEFAULT 0.5,
    supporting_episodic_ids TEXT  DEFAULT '[]',
    counterevidence_refs  TEXT    DEFAULT '[]',
    -- semantic
    applicability_scope   TEXT    DEFAULT 'general',
    is_active             INTEGER DEFAULT 1,
    superseded_by         TEXT    DEFAULT NULL,
    derived_from          TEXT    DEFAULT '[]',
    verification_evidence TEXT    DEFAULT '[]',
    -- shared
    evidence_links        TEXT    DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_type_status ON memory_records(memory_type, status);
CREATE INDEX IF NOT EXISTS idx_session     ON memory_records(session_id);
CREATE INDEX IF NOT EXISTS idx_task        ON memory_records(task_id);
CREATE INDEX IF NOT EXISTS idx_project     ON memory_records(project_id);
CREATE INDEX IF NOT EXISTS idx_scope       ON memory_records(scope, scope_id);
CREATE INDEX IF NOT EXISTS idx_created     ON memory_records(created_at DESC);

-- Append-only audit trail: every lifecycle transition is recorded here.
CREATE TABLE IF NOT EXISTS audit_log (
    id          TEXT PRIMARY KEY,
    memory_id   TEXT NOT NULL,
    action      TEXT NOT NULL,
    from_status TEXT,
    to_status   TEXT,
    agent       TEXT DEFAULT '',
    reason      TEXT DEFAULT '',
    timestamp   REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_memory ON audit_log(memory_id);

-- Open conflict queue: pairs of records that contradict each other.
CREATE TABLE IF NOT EXISTS conflicts (
    id            TEXT PRIMARY KEY,
    record_a_id   TEXT NOT NULL,
    record_b_id   TEXT NOT NULL,
    conflict_type TEXT DEFAULT 'contradiction',
    status        TEXT DEFAULT 'open',
    resolution    TEXT DEFAULT '',
    created_at    REAL NOT NULL,
    resolved_at   REAL
);
CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(status);
"""


class MemoryStore:
    def __init__(self, db_path: str = "multi_agent_memory.db"):
        self.db_path = db_path
        self._local  = threading.local()
        self._init_db()

    # ── connection ────────────────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        if not getattr(self._local, "conn", None):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def _init_db(self):
        conn = self._conn()
        conn.executescript(_SCHEMA)
        conn.commit()

    # ── serialization helpers ─────────────────────────────────────────────────

    @staticmethod
    def _j(v) -> str:
        return json.dumps(v) if isinstance(v, (list, dict)) else (v or "")

    @staticmethod
    def _uj(v, default=None):
        if v is None:
            return [] if default is None else default
        try:
            return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return [] if default is None else default

    # ── writes (idempotent — INSERT OR REPLACE) ───────────────────────────────

    def save_episodic(self, r: EpisodicRecord):
        self._conn().execute(
            """INSERT OR REPLACE INTO memory_records
               (id, memory_type, status, content, created_at, updated_at, version,
                confidence, scope, scope_id, provenance,
                session_id, task_id, project_id, user_id, source_agent,
                event_type, raw_input, raw_output, tool_names, entities, tags,
                salience, evidence_links)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r.id, r.memory_type.value, r.status.value, r.content,
             r.created_at, r.updated_at, r.version,
             r.confidence, r.scope.value, r.scope_id, r.provenance,
             r.session_id, r.task_id, r.project_id, r.user_id, r.source_agent,
             r.event_type.value, r.raw_input, r.raw_output,
             self._j(r.tool_names), self._j(r.entities), self._j(r.tags),
             r.salience, self._j(r.evidence_links)),
        )
        self._conn().commit()

    def save_reflection(self, r: ReflectionRecord):
        self._conn().execute(
            """INSERT OR REPLACE INTO memory_records
               (id, memory_type, status, content, created_at, updated_at, version,
                confidence, scope, scope_id, provenance,
                session_id, task_id, project_id, user_id, source_agent,
                cluster_id, reflection_type, strength,
                supporting_episodic_ids, counterevidence_refs, evidence_links)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r.id, r.memory_type.value, r.status.value, r.content,
             r.created_at, r.updated_at, r.version,
             r.confidence, r.scope.value, r.scope_id, r.provenance,
             r.session_id, r.task_id, r.project_id, r.user_id, r.source_agent,
             r.cluster_id, r.reflection_type.value, r.strength,
             self._j(r.supporting_episodic_ids),
             self._j(r.counterevidence_refs),
             self._j(r.evidence_links)),
        )
        self._conn().commit()

    def save_semantic(self, r: SemanticRecord):
        self._conn().execute(
            """INSERT OR REPLACE INTO memory_records
               (id, memory_type, status, content, created_at, updated_at, version,
                confidence, scope, scope_id, provenance,
                session_id, task_id, project_id, user_id, source_agent,
                applicability_scope, is_active, superseded_by,
                derived_from, verification_evidence, evidence_links, tags, entities)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r.id, r.memory_type.value, r.status.value, r.content,
             r.created_at, r.updated_at, r.version,
             r.confidence, r.scope.value, r.scope_id, r.provenance,
             r.session_id, r.task_id, r.project_id, r.user_id, r.source_agent,
             r.applicability_scope, int(r.is_active), r.superseded_by,
             self._j(r.derived_from), self._j(r.verification_evidence),
             self._j(r.evidence_links), self._j(r.tags), self._j(r.entities)),
        )
        self._conn().commit()

    def update_status(self, record_id: str, new_status: MemoryStatus, version_bump: bool = False):
        now = time.time()
        sql = (
            "UPDATE memory_records SET status=?, updated_at=?, version=version+1 WHERE id=?"
            if version_bump
            else "UPDATE memory_records SET status=?, updated_at=? WHERE id=?"
        )
        self._conn().execute(sql, (new_status.value, now, record_id))
        self._conn().commit()

    def update_field(self, record_id: str, column: str, value):
        # column is internal — callers must only pass known column names
        self._conn().execute(
            f"UPDATE memory_records SET {column}=?, updated_at=? WHERE id=?",
            (value, time.time(), record_id),
        )
        self._conn().commit()

    # ── reads ─────────────────────────────────────────────────────────────────

    def get_by_id(self, record_id: str) -> Optional[Dict]:
        row = self._conn().execute(
            "SELECT * FROM memory_records WHERE id=?", (record_id,)
        ).fetchone()
        return dict(row) if row else None

    def query_episodic(
        self,
        session_id:   str   = "",
        task_id:      str   = "",
        project_id:   str   = "",
        event_type:   str   = "",
        status:       str   = MemoryStatus.OBSERVED.value,
        min_salience: float = 0.0,
        since:        float = 0.0,
        limit:        int   = 50,
    ) -> List[Dict]:
        clauses, params = ["memory_type='episodic'"], []
        if session_id:   clauses.append("session_id=?");  params.append(session_id)
        if task_id:      clauses.append("task_id=?");     params.append(task_id)
        if project_id:   clauses.append("project_id=?");  params.append(project_id)
        if event_type:   clauses.append("event_type=?");  params.append(event_type)
        if status:       clauses.append("status=?");      params.append(status)
        if min_salience: clauses.append("salience>=?");   params.append(min_salience)
        if since:        clauses.append("created_at>=?"); params.append(since)
        params.append(limit)
        sql = f"SELECT * FROM memory_records WHERE {' AND '.join(clauses)} ORDER BY created_at DESC LIMIT ?"
        return [dict(r) for r in self._conn().execute(sql, params).fetchall()]

    def query_reflections(
        self,
        project_id:     str   = "",
        status:         str   = MemoryStatus.CANDIDATE.value,
        min_confidence: float = 0.0,
        limit:          int   = 20,
    ) -> List[Dict]:
        clauses, params = ["memory_type='reflection'"], []
        if project_id:     clauses.append("project_id=?");    params.append(project_id)
        if status:         clauses.append("status=?");        params.append(status)
        if min_confidence: clauses.append("confidence>=?");   params.append(min_confidence)
        params.append(limit)
        sql = f"SELECT * FROM memory_records WHERE {' AND '.join(clauses)} ORDER BY confidence DESC LIMIT ?"
        return [dict(r) for r in self._conn().execute(sql, params).fetchall()]

    def query_semantic(
        self,
        scope:          str   = "",
        scope_id:       str   = "",
        min_confidence: float = 0.7,
        active_only:    bool  = True,
        limit:          int   = 20,
    ) -> List[Dict]:
        clauses, params = ["memory_type='semantic'"], []
        if active_only:    clauses.append("is_active=1")
        if scope:          clauses.append("scope=?");          params.append(scope)
        if scope_id:       clauses.append("scope_id=?");       params.append(scope_id)
        if min_confidence: clauses.append("confidence>=?");    params.append(min_confidence)
        params.append(limit)
        sql = f"SELECT * FROM memory_records WHERE {' AND '.join(clauses)} ORDER BY confidence DESC LIMIT ?"
        return [dict(r) for r in self._conn().execute(sql, params).fetchall()]

    def keyword_search(
        self,
        query:        str,
        memory_types: Optional[List[str]] = None,
        limit:        int = 10,
    ) -> List[Dict]:
        terms = [t for t in query.lower().split() if len(t) > 2][:4]
        if not terms:
            return []
        term_clauses = ["LOWER(content) LIKE ?" for _ in terms]
        params: list = [f"%{t}%" for t in terms]
        type_filter = ""
        if memory_types:
            ph = ",".join("?" for _ in memory_types)
            type_filter = f" AND memory_type IN ({ph})"
            params.extend(memory_types)
        sql = (
            f"SELECT * FROM memory_records WHERE ({' OR '.join(term_clauses)})"
            f"{type_filter} ORDER BY confidence DESC, salience DESC LIMIT ?"
        )
        params.append(limit)
        return [dict(r) for r in self._conn().execute(sql, params).fetchall()]

    # ── audit ─────────────────────────────────────────────────────────────────

    def log_audit(self, entry: AuditEntry):
        self._conn().execute(
            "INSERT INTO audit_log(id,memory_id,action,from_status,to_status,agent,reason,timestamp) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (entry.id, entry.memory_id, entry.action,
             entry.from_status, entry.to_status,
             entry.agent, entry.reason, entry.timestamp),
        )
        self._conn().commit()

    def get_audit_trail(self, memory_id: str) -> List[Dict]:
        return [dict(r) for r in self._conn().execute(
            "SELECT * FROM audit_log WHERE memory_id=? ORDER BY timestamp", (memory_id,)
        ).fetchall()]

    # ── conflicts ─────────────────────────────────────────────────────────────

    def save_conflict(self, c: ConflictRecord):
        self._conn().execute(
            "INSERT OR IGNORE INTO conflicts(id,record_a_id,record_b_id,conflict_type,status,created_at) "
            "VALUES(?,?,?,?,?,?)",
            (c.id, c.record_a_id, c.record_b_id, c.conflict_type, c.status, c.created_at),
        )
        self._conn().commit()

    def get_open_conflicts(self) -> List[Dict]:
        return [dict(r) for r in self._conn().execute(
            "SELECT * FROM conflicts WHERE status='open'"
        ).fetchall()]

    def resolve_conflict(self, conflict_id: str, resolution: str):
        self._conn().execute(
            "UPDATE conflicts SET status='resolved', resolution=?, resolved_at=? WHERE id=?",
            (resolution, time.time(), conflict_id),
        )
        self._conn().commit()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def close(self):
        if getattr(self._local, "conn", None):
            self._local.conn.close()
            self._local.conn = None
