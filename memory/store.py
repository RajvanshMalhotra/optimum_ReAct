# """SQLite persistent storage for memories."""
# import sqlite3
# import json
# from typing import List
# from models.memory import MemoryNode


# class MemoryStore:
#     """SQLite persistent storage."""
    
#     def __init__(self, db_path: str):
#         self.db_path = db_path
#         self._init_db()
    
#     def _init_db(self):
#         """Initialize database schema."""
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         c.execute("""
#             CREATE TABLE IF NOT EXISTS memories (
#                 id TEXT PRIMARY KEY,
#                 type TEXT,
#                 content TEXT,
#                 metadata TEXT,
#                 timestamp REAL,
#                 connections TEXT,
#                 importance REAL,
#                 access_count INTEGER
#             )
#         """)
        
#         c.execute("""
#             CREATE TABLE IF NOT EXISTS sessions (
#                 id TEXT PRIMARY KEY,
#                 task TEXT,
#                 timestamp REAL,
#                 result TEXT,
#                 duration REAL
#             )
#         """)
        
#         c.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON memories(timestamp)")
#         c.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(type)")
#         c.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)")
        
#         conn.commit()
#         conn.close()
    
#     def save_node(self, node: MemoryNode):
#         """Persist node to SQLite."""
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         c.execute("""
#             INSERT OR REPLACE INTO memories 
#             (id, type, content, metadata, timestamp, connections, importance, access_count)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#         """, (
#             node.id,
#             node.type,
#             node.content,
#             json.dumps(node.metadata),
#             node.timestamp,
#             json.dumps(node.connections),
#             node.importance,
#             node.access_count
#         ))
        
#         conn.commit()
#         conn.close()
    
#     def save_nodes(self, nodes: List[MemoryNode]):
#         """Batch save nodes."""
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         data = [
#             (n.id, n.type, n.content, json.dumps(n.metadata), n.timestamp,
#              json.dumps(n.connections), n.importance, n.access_count)
#             for n in nodes
#         ]
        
#         c.executemany("""
#             INSERT OR REPLACE INTO memories 
#             (id, type, content, metadata, timestamp, connections, importance, access_count)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#         """, data)
        
#         conn.commit()
#         conn.close()
    
#     def load_nodes(self, node_ids: List[str]) -> List[MemoryNode]:
#         """Load specific nodes from SQLite."""
#         if not node_ids:
#             return []
        
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         placeholders = ','.join('?' * len(node_ids))
#         c.execute(f"""
#             SELECT id, type, content, metadata, timestamp, connections, importance, access_count
#             FROM memories WHERE id IN ({placeholders})
#         """, node_ids)
        
#         nodes = []
#         for row in c.fetchall():
#             nodes.append(MemoryNode(
#                 id=row[0],
#                 type=row[1],
#                 content=row[2],
#                 metadata=json.loads(row[3]),
#                 timestamp=row[4],
#                 connections=json.loads(row[5]),
#                 importance=row[6],
#                 access_count=row[7]
#             ))
        
#         conn.close()
#         return nodes
    
#     def search_similar(self, query: str, limit: int = 5) -> List[MemoryNode]:
#         """Search for similar memories (keyword matching)."""
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         keywords = query.lower().split()
#         conditions = ' OR '.join(['LOWER(content) LIKE ?' for _ in keywords])
#         params = [f'%{kw}%' for kw in keywords]
        
#         c.execute(f"""
#             SELECT id, type, content, metadata, timestamp, connections, importance, access_count
#             FROM memories 
#             WHERE {conditions}
#             ORDER BY importance DESC, access_count DESC
#             LIMIT ?
#         """, params + [limit])
        
#         nodes = []
#         for row in c.fetchall():
#             nodes.append(MemoryNode(
#                 id=row[0],
#                 type=row[1],
#                 content=row[2],
#                 metadata=json.loads(row[3]),
#                 timestamp=row[4],
#                 connections=json.loads(row[5]),
#                 importance=row[6],
#                 access_count=row[7]
#             ))
        
#         conn.close()
#         return nodes
    
#     def save_session(self, session_id: str, task: str, result: str, duration: float, timestamp: float):
#         """Save completed session."""
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         c.execute("""
#             INSERT INTO sessions (id, task, timestamp, result, duration)
#             VALUES (?, ?, ?, ?, ?)
#         """, (session_id, task, timestamp, result, duration))
        
#         conn.commit()
#         conn.close()
    
#     def get_stats(self) -> dict:
#         """Get database statistics."""
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         c.execute("SELECT COUNT(*) FROM memories")
#         memory_count = c.fetchone()[0]
        
#         c.execute("SELECT COUNT(*) FROM sessions")
#         session_count = c.fetchone()[0]
        
#         conn.close()
        
#         return {
#             "total_memories": memory_count,
#             "total_sessions": session_count
#         }# implement initial memory store interface (2025-11-10)
# # add simple in-memory backend (2025-11-17)
# # handle memory overwrite cases (2025-11-23)
# # add persistence hooks (stub) (2025-11-29)
# # refactor storage API naming (2025-12-04)
# # add lightweight caching (2025-12-09)

# """SQLite persistent storage with FTS and session linking - FIXED."""
# import sqlite3
# import json
# import time
# from typing import List, Dict, Optional
# from models.memory import MemoryNode


# class MemoryStore:
#     """SQLite persistent storage with Full-Text Search."""
    
#     def __init__(self, db_path: str):
#         self.db_path = db_path
#         self._init_db()
    
#     def _init_db(self):
#         """Initialize database schema with FTS."""
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         # Main memory table
#         c.execute("""
#             CREATE TABLE IF NOT EXISTS memories (
#                 id TEXT PRIMARY KEY,
#                 type TEXT,
#                 content TEXT,
#                 metadata TEXT,
#                 timestamp REAL,
#                 last_accessed REAL,
#                 connections TEXT,
#                 importance REAL,
#                 access_count INTEGER,
#                 session_id TEXT
#             )
#         """)
        
#         # Check if FTS5 is available
#         try:
#             # Full-Text Search virtual table
#             c.execute("""
#                 CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts 
#                 USING fts5(id UNINDEXED, content, tokenize='porter ascii')
#             """)
            
#             # Triggers to keep FTS in sync
#             c.execute("""
#                 CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
#                     INSERT INTO memories_fts(id, content) 
#                     VALUES (new.id, new.content);
#                 END
#             """)
            
#             c.execute("""
#                 CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
#                     DELETE FROM memories_fts WHERE id = old.id;
#                 END
#             """)
            
#             c.execute("""
#                 CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
#                     UPDATE memories_fts SET content = new.content WHERE id = new.id;
#                 END
#             """)
            
#             self.fts_available = True
#         except Exception as e:
#             print(f"Warning: FTS5 not available: {e}")
#             self.fts_available = False
        
#         # Sessions table with memory links
#         c.execute("""
#             CREATE TABLE IF NOT EXISTS sessions (
#                 id TEXT PRIMARY KEY,
#                 task TEXT,
#                 timestamp REAL,
#                 result TEXT,
#                 duration REAL,
#                 memory_count INTEGER DEFAULT 0
#             )
#         """)
        
#         # Indexes for performance
#         c.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON memories(timestamp)")
#         c.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(type)")
#         c.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)")
#         c.execute("CREATE INDEX IF NOT EXISTS idx_session ON memories(session_id)")
#         c.execute("CREATE INDEX IF NOT EXISTS idx_last_accessed ON memories(last_accessed)")
        
#         conn.commit()
#         conn.close()
    
#     def save_node(self, node: MemoryNode, session_id: Optional[str] = None):
#         """Persist node to SQLite."""
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         c.execute("""
#             INSERT OR REPLACE INTO memories 
#             (id, type, content, metadata, timestamp, last_accessed, connections, 
#              importance, access_count, session_id)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """, (
#             node.id,
#             node.type,
#             node.content,
#             json.dumps(node.metadata),
#             node.timestamp,
#             node.last_accessed,
#             json.dumps(node.connections),
#             node.importance,
#             node.access_count,
#             session_id
#         ))
        
#         conn.commit()
#         conn.close()
    
#     def save_nodes(self, nodes: List[MemoryNode], session_id: Optional[str] = None):
#         """Batch save nodes."""
#         if not nodes:
#             return
        
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         data = [
#             (n.id, n.type, n.content, json.dumps(n.metadata), n.timestamp,
#              n.last_accessed, json.dumps(n.connections), n.importance, 
#              n.access_count, session_id)
#             for n in nodes
#         ]
        
#         c.executemany("""
#             INSERT OR REPLACE INTO memories 
#             (id, type, content, metadata, timestamp, last_accessed, connections, 
#              importance, access_count, session_id)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """, data)
        
#         conn.commit()
#         conn.close()
    
#     def load_nodes(self, node_ids: List[str]) -> List[MemoryNode]:
#         """Load specific nodes from SQLite."""
#         if not node_ids:
#             return []
        
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         placeholders = ','.join('?' * len(node_ids))
#         c.execute(f"""
#             SELECT id, type, content, metadata, timestamp, last_accessed, 
#                    connections, importance, access_count
#             FROM memories WHERE id IN ({placeholders})
#         """, node_ids)
        
#         nodes = []
#         for row in c.fetchall():
#             nodes.append(MemoryNode(
#                 id=row[0],
#                 type=row[1],
#                 content=row[2],
#                 metadata=json.loads(row[3]),
#                 timestamp=row[4],
#                 last_accessed=row[5],
#                 connections=json.loads(row[6]),
#                 importance=row[7],
#                 access_count=row[8]
#             ))
        
#         conn.close()
#         return nodes
    
#     def search_fts(self, query: str, limit: int = 5) -> List[MemoryNode]:
#         """Full-Text Search using SQLite FTS5."""
#         if not self.fts_available or not query or not query.strip():
#             return []
        
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         try:
#             # Escape special FTS5 characters
#             safe_query = query.replace('"', '""')
            
#             # Use subquery approach which is more compatible
#             c.execute("""
#                 SELECT m.id, m.type, m.content, m.metadata, m.timestamp, m.last_accessed,
#                        m.connections, m.importance, m.access_count
#                 FROM memories m
#                 WHERE m.id IN (
#                     SELECT id FROM memories_fts WHERE content MATCH ?
#                 )
#                 ORDER BY 
#                     m.importance DESC,
#                     m.last_accessed DESC
#                 LIMIT ?
#             """, (safe_query, limit))
            
#             nodes = []
#             for row in c.fetchall():
#                 nodes.append(MemoryNode(
#                     id=row[0],
#                     type=row[1],
#                     content=row[2],
#                     metadata=json.loads(row[3]),
#                     timestamp=row[4],
#                     last_accessed=row[5],
#                     connections=json.loads(row[6]),
#                     importance=row[7],
#                     access_count=row[8]
#                 ))
            
#             conn.close()
#             return nodes
            
#         except Exception as e:
#             print(f"FTS search failed: {e}")
#             conn.close()
#             return []
    
#     def search_similar(self, query: str, limit: int = 5) -> List[MemoryNode]:
#         """Hybrid search: FTS + keyword fallback."""
#         # Try FTS first if available
#         if self.fts_available:
#             fts_results = self.search_fts(query, limit=limit)
#             if len(fts_results) >= limit:
#                 return fts_results
#         else:
#             fts_results = []
        
#         # Fallback to keyword search
#         if not query or not query.strip():
#             return fts_results
        
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         keywords = query.lower().split()
#         conditions = ' OR '.join(['LOWER(content) LIKE ?' for _ in keywords])
#         params = [f'%{kw}%' for kw in keywords]
        
#         try:
#             c.execute(f"""
#                 SELECT id, type, content, metadata, timestamp, last_accessed,
#                        connections, importance, access_count
#                 FROM memories 
#                 WHERE {conditions}
#                 ORDER BY importance DESC, last_accessed DESC
#                 LIMIT ?
#             """, params + [limit - len(fts_results)])
            
#             for row in c.fetchall():
#                 # Avoid duplicates from FTS results
#                 if not any(n.id == row[0] for n in fts_results):
#                     fts_results.append(MemoryNode(
#                         id=row[0],
#                         type=row[1],
#                         content=row[2],
#                         metadata=json.loads(row[3]),
#                         timestamp=row[4],
#                         last_accessed=row[5],
#                         connections=json.loads(row[6]),
#                         importance=row[7],
#                         access_count=row[8]
#                     ))
#         except Exception as e:
#             print(f"Keyword search failed: {e}")
        
#         conn.close()
#         return fts_results[:limit]
    
#     def get_session_memories(self, session_id: str) -> List[MemoryNode]:
#         """Get all memories from a specific session."""
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         try:
#             c.execute("""
#                 SELECT id, type, content, metadata, timestamp, last_accessed,
#                        connections, importance, access_count
#                 FROM memories 
#                 WHERE session_id = ?
#                 ORDER BY timestamp ASC
#             """, (session_id,))
            
#             nodes = []
#             for row in c.fetchall():
#                 nodes.append(MemoryNode(
#                     id=row[0],
#                     type=row[1],
#                     content=row[2],
#                     metadata=json.loads(row[3]),
#                     timestamp=row[4],
#                     last_accessed=row[5],
#                     connections=json.loads(row[6]),
#                     importance=row[7],
#                     access_count=row[8]
#                 ))
#         except Exception as e:
#             print(f"Error loading session memories: {e}")
#             nodes = []
        
#         conn.close()
#         return nodes
    
#     def find_similar_sessions(self, task: str, limit: int = 3) -> List[Dict]:
#         """Find sessions with similar tasks."""
#         if not task or not task.strip():
#             return []
        
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         keywords = task.lower().split()
#         if not keywords:
#             conn.close()
#             return []
        
#         conditions = ' OR '.join(['LOWER(task) LIKE ?' for _ in keywords])
#         params = [f'%{kw}%' for kw in keywords]
        
#         try:
#             # Check if memory_count column exists
#             c.execute("PRAGMA table_info(sessions)")
#             columns = [col[1] for col in c.fetchall()]
            
#             if 'memory_count' in columns:
#                 c.execute(f"""
#                     SELECT id, task, timestamp, result, duration, memory_count
#                     FROM sessions 
#                     WHERE {conditions}
#                     ORDER BY timestamp DESC
#                     LIMIT ?
#                 """, params + [limit])
#             else:
#                 c.execute(f"""
#                     SELECT id, task, timestamp, result, duration, 0 as memory_count
#                     FROM sessions 
#                     WHERE {conditions}
#                     ORDER BY timestamp DESC
#                     LIMIT ?
#                 """, params + [limit])
            
#             sessions = []
#             for row in c.fetchall():
#                 sessions.append({
#                     'id': row[0],
#                     'task': row[1],
#                     'timestamp': row[2],
#                     'result': row[3],
#                     'duration': row[4],
#                     'memory_count': row[5] if len(row) > 5 else 0
#                 })
            
#             conn.close()
#             return sessions
            
#         except Exception as e:
#             print(f"Error finding similar sessions: {e}")
#             conn.close()
#             return []
    
#     def save_session(self, session_id: str, task: str, result: str, 
#                     duration: float, timestamp: float, memory_count: int = 0):
#         """Save completed session with memory count."""
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         try:
#             c.execute("""
#                 INSERT OR REPLACE INTO sessions 
#                 (id, task, timestamp, result, duration, memory_count)
#                 VALUES (?, ?, ?, ?, ?, ?)
#             """, (session_id, task, timestamp, result, duration, memory_count))
            
#             conn.commit()
#         except Exception as e:
#             print(f"Error saving session: {e}")
        
#         conn.close()
    
#     def cleanup_old_memories(self, days: int = 30):
#         """Remove memories older than specified days with low importance."""
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         cutoff_time = time.time() - (days * 24 * 3600)
        
#         try:
#             c.execute("""
#                 DELETE FROM memories 
#                 WHERE last_accessed < ? 
#                 AND importance < 0.5
#                 AND access_count < 3
#             """, (cutoff_time,))
            
#             deleted = c.rowcount
#             conn.commit()
#         except Exception as e:
#             print(f"Error cleaning up memories: {e}")
#             deleted = 0
        
#         conn.close()
#         return deleted
    
#     def get_stats(self) -> dict:
#         """Get database statistics."""
#         conn = sqlite3.connect(self.db_path)
#         c = conn.cursor()
        
#         try:
#             c.execute("SELECT COUNT(*) FROM memories")
#             memory_count = c.fetchone()[0]
            
#             c.execute("SELECT COUNT(*) FROM sessions")
#             session_count = c.fetchone()[0]
            
#             c.execute("""
#                 SELECT type, COUNT(*) 
#                 FROM memories 
#                 GROUP BY type
#             """)
#             type_counts = dict(c.fetchall())
            
#             c.execute("""
#                 SELECT AVG(importance), AVG(access_count)
#                 FROM memories
#             """)
#             avg_stats = c.fetchone()
            
#             stats = {
#                 "total_memories": memory_count,
#                 "total_sessions": session_count,
#                 "memory_types": type_counts,
#                 "avg_importance": avg_stats[0] or 0,
#                 "avg_access_count": avg_stats[1] or 0,
#                 "fts_available": self.fts_available
#             }
#         except Exception as e:
#             print(f"Error getting stats: {e}")
#             stats = {
#                 "total_memories": 0,
#                 "total_sessions": 0,
#                 "memory_types": {},
#                 "avg_importance": 0,
#                 "avg_access_count": 0,
#                 "fts_available": self.fts_available
#             }
        
#         conn.close()
#         return stats


"""SQLite persistent storage with FTS and session linking - FIXED."""
import sqlite3
import json
import time
import re
from typing import List, Dict, Optional
from models.memory import MemoryNode


class MemoryStore:
    """SQLite persistent storage with Full-Text Search."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema with FTS."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Main memory table
        c.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                type TEXT,
                content TEXT,
                metadata TEXT,
                timestamp REAL,
                last_accessed REAL,
                connections TEXT,
                importance REAL,
                access_count INTEGER,
                session_id TEXT
            )
        """)
        
        # Check if FTS5 is available
        try:
            # Full-Text Search virtual table
            c.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts 
                USING fts5(id UNINDEXED, content, tokenize='porter ascii')
            """)
            
            # Triggers to keep FTS in sync
            c.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(id, content) 
                    VALUES (new.id, new.content);
                END
            """)
            
            c.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                    DELETE FROM memories_fts WHERE id = old.id;
                END
            """)
            
            c.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                    UPDATE memories_fts SET content = new.content WHERE id = new.id;
                END
            """)
            
            self.fts_available = True
        except Exception as e:
            print(f"Warning: FTS5 not available: {e}")
            self.fts_available = False
        
        # Sessions table with memory links
        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                task TEXT,
                timestamp REAL,
                result TEXT,
                duration REAL,
                memory_count INTEGER DEFAULT 0
            )
        """)
        
        # Indexes for performance
        c.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON memories(timestamp)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(type)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_session ON memories(session_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_last_accessed ON memories(last_accessed)")
        
        conn.commit()
        conn.close()
    
    def _sanitize_fts_query(self, query: str) -> Optional[str]:
        """Sanitize query for FTS5 MATCH to avoid syntax errors."""
        if not query or not query.strip():
            return None
        
        # Remove or escape special FTS5 characters that cause issues
        # FTS5 special chars: " * ( ) AND OR NOT
        query = query.strip()
        
        # Remove quotes and other problematic characters
        query = re.sub(r'["\*\(\)]', ' ', query)
        
        # Split into words and filter out FTS5 operators and short words
        words = query.split()
        fts_operators = {'AND', 'OR', 'NOT', 'NEAR', 'and', 'or', 'not', 'near'}
        words = [w for w in words if w not in fts_operators and len(w) > 1]
        
        if not words:
            return None
        
        # Join words with OR operator for broader matching
        # Each word is treated as a separate term
        sanitized = ' OR '.join(words)
        
        return sanitized
    
    def save_node(self, node: MemoryNode, session_id: Optional[str] = None):
        """Persist node to SQLite."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT OR REPLACE INTO memories 
            (id, type, content, metadata, timestamp, last_accessed, connections, 
             importance, access_count, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            node.id,
            node.type,
            node.content,
            json.dumps(node.metadata),
            node.timestamp,
            node.last_accessed,
            json.dumps(node.connections),
            node.importance,
            node.access_count,
            session_id
        ))
        
        conn.commit()
        conn.close()
    
    def save_nodes(self, nodes: List[MemoryNode], session_id: Optional[str] = None):
        """Batch save nodes."""
        if not nodes:
            return
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        data = [
            (n.id, n.type, n.content, json.dumps(n.metadata), n.timestamp,
             n.last_accessed, json.dumps(n.connections), n.importance, 
             n.access_count, session_id)
            for n in nodes
        ]
        
        c.executemany("""
            INSERT OR REPLACE INTO memories 
            (id, type, content, metadata, timestamp, last_accessed, connections, 
             importance, access_count, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        
        conn.commit()
        conn.close()
    
    def load_nodes(self, node_ids: List[str]) -> List[MemoryNode]:
        """Load specific nodes from SQLite."""
        if not node_ids:
            return []
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        placeholders = ','.join('?' * len(node_ids))
        c.execute(f"""
            SELECT id, type, content, metadata, timestamp, last_accessed, 
                   connections, importance, access_count
            FROM memories WHERE id IN ({placeholders})
        """, node_ids)
        
        nodes = []
        for row in c.fetchall():
            nodes.append(MemoryNode(
                id=row[0],
                type=row[1],
                content=row[2],
                metadata=json.loads(row[3]),
                timestamp=row[4],
                last_accessed=row[5],
                connections=json.loads(row[6]),
                importance=row[7],
                access_count=row[8]
            ))
        
        conn.close()
        return nodes
    
    def search_fts(self, query: str, limit: int = 5) -> List[MemoryNode]:
        """Full-Text Search using SQLite FTS5."""
        if not self.fts_available:
            return []
        
        sanitized_query = self._sanitize_fts_query(query)
        if not sanitized_query:
            return []
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Use parameterized query properly with FTS5
            # The MATCH clause requires the query as a bound parameter
            c.execute("""
                SELECT m.id, m.type, m.content, m.metadata, m.timestamp, m.last_accessed,
                       m.connections, m.importance, m.access_count
                FROM memories m
                JOIN memories_fts f ON m.id = f.id
                WHERE memories_fts MATCH ?
                ORDER BY 
                    m.importance DESC,
                    m.last_accessed DESC
                LIMIT ?
            """, (sanitized_query, limit))
            
            nodes = []
            for row in c.fetchall():
                nodes.append(MemoryNode(
                    id=row[0],
                    type=row[1],
                    content=row[2],
                    metadata=json.loads(row[3]),
                    timestamp=row[4],
                    last_accessed=row[5],
                    connections=json.loads(row[6]),
                    importance=row[7],
                    access_count=row[8]
                ))
            
            conn.close()
            return nodes
            
        except Exception as e:
            print(f"FTS search failed: {e}")
            print(f"Query was: {sanitized_query}")
            conn.close()
            return []
    
    def search_similar(self, query: str, limit: int = 5) -> List[MemoryNode]:
        """Hybrid search: FTS + keyword fallback."""
        # Try FTS first if available
        if self.fts_available:
            fts_results = self.search_fts(query, limit=limit)
            if len(fts_results) >= limit:
                return fts_results
        else:
            fts_results = []
        
        # Fallback to keyword search
        if not query or not query.strip():
            return fts_results
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        keywords = query.lower().split()
        conditions = ' OR '.join(['LOWER(content) LIKE ?' for _ in keywords])
        params = [f'%{kw}%' for kw in keywords]
        
        try:
            c.execute(f"""
                SELECT id, type, content, metadata, timestamp, last_accessed,
                       connections, importance, access_count
                FROM memories 
                WHERE {conditions}
                ORDER BY importance DESC, last_accessed DESC
                LIMIT ?
            """, params + [limit - len(fts_results)])
            
            for row in c.fetchall():
                # Avoid duplicates from FTS results
                if not any(n.id == row[0] for n in fts_results):
                    fts_results.append(MemoryNode(
                        id=row[0],
                        type=row[1],
                        content=row[2],
                        metadata=json.loads(row[3]),
                        timestamp=row[4],
                        last_accessed=row[5],
                        connections=json.loads(row[6]),
                        importance=row[7],
                        access_count=row[8]
                    ))
        except Exception as e:
            print(f"Keyword search failed: {e}")
        
        conn.close()
        return fts_results[:limit]
    
    def get_session_memories(self, session_id: str) -> List[MemoryNode]:
        """Get all memories from a specific session."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute("""
                SELECT id, type, content, metadata, timestamp, last_accessed,
                       connections, importance, access_count
                FROM memories 
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """, (session_id,))
            
            nodes = []
            for row in c.fetchall():
                nodes.append(MemoryNode(
                    id=row[0],
                    type=row[1],
                    content=row[2],
                    metadata=json.loads(row[3]),
                    timestamp=row[4],
                    last_accessed=row[5],
                    connections=json.loads(row[6]),
                    importance=row[7],
                    access_count=row[8]
                ))
        except Exception as e:
            print(f"Error loading session memories: {e}")
            nodes = []
        
        conn.close()
        return nodes
    
    def find_similar_sessions(self, task: str, limit: int = 3) -> List[Dict]:
        """Find sessions with similar tasks."""
        if not task or not task.strip():
            return []
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        keywords = task.lower().split()
        if not keywords:
            conn.close()
            return []
        
        conditions = ' OR '.join(['LOWER(task) LIKE ?' for _ in keywords])
        params = [f'%{kw}%' for kw in keywords]
        
        try:
            # Check if memory_count column exists
            c.execute("PRAGMA table_info(sessions)")
            columns = [col[1] for col in c.fetchall()]
            
            if 'memory_count' in columns:
                c.execute(f"""
                    SELECT id, task, timestamp, result, duration, memory_count
                    FROM sessions 
                    WHERE {conditions}
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, params + [limit])
            else:
                c.execute(f"""
                    SELECT id, task, timestamp, result, duration, 0 as memory_count
                    FROM sessions 
                    WHERE {conditions}
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, params + [limit])
            
            sessions = []
            for row in c.fetchall():
                sessions.append({
                    'id': row[0],
                    'task': row[1],
                    'timestamp': row[2],
                    'result': row[3],
                    'duration': row[4],
                    'memory_count': row[5] if len(row) > 5 else 0
                })
            
            conn.close()
            return sessions
            
        except Exception as e:
            print(f"Error finding similar sessions: {e}")
            conn.close()
            return []
    
    def save_session(self, session_id: str, task: str, result: str, 
                    duration: float, timestamp: float, memory_count: int = 0):
        """Save completed session with memory count."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute("""
                INSERT OR REPLACE INTO sessions 
                (id, task, timestamp, result, duration, memory_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, task, timestamp, result, duration, memory_count))
            
            conn.commit()
        except Exception as e:
            print(f"Error saving session: {e}")
        
        conn.close()
    
    def cleanup_old_memories(self, days: int = 30):
        """Remove memories older than specified days with low importance."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        cutoff_time = time.time() - (days * 24 * 3600)
        
        try:
            c.execute("""
                DELETE FROM memories 
                WHERE last_accessed < ? 
                AND importance < 0.5
                AND access_count < 3
            """, (cutoff_time,))
            
            deleted = c.rowcount
            conn.commit()
        except Exception as e:
            print(f"Error cleaning up memories: {e}")
            deleted = 0
        
        conn.close()
        return deleted
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute("SELECT COUNT(*) FROM memories")
            memory_count = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM sessions")
            session_count = c.fetchone()[0]
            
            c.execute("""
                SELECT type, COUNT(*) 
                FROM memories 
                GROUP BY type
            """)
            type_counts = dict(c.fetchall())
            
            c.execute("""
                SELECT AVG(importance), AVG(access_count)
                FROM memories
            """)
            avg_stats = c.fetchone()
            
            stats = {
                "total_memories": memory_count,
                "total_sessions": session_count,
                "memory_types": type_counts,
                "avg_importance": avg_stats[0] or 0,
                "avg_access_count": avg_stats[1] or 0,
                "fts_available": self.fts_available
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            stats = {
                "total_memories": 0,
                "total_sessions": 0,
                "memory_types": {},
                "avg_importance": 0,
                "avg_access_count": 0,
                "fts_available": self.fts_available
            }
        
        conn.close()
        return stats