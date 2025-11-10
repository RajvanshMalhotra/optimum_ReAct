"""SQLite persistent storage for memories."""
import sqlite3
import json
from typing import List
from models.memory import MemoryNode


class MemoryStore:
    """SQLite persistent storage."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                type TEXT,
                content TEXT,
                metadata TEXT,
                timestamp REAL,
                connections TEXT,
                importance REAL,
                access_count INTEGER
            )
        """)
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                task TEXT,
                timestamp REAL,
                result TEXT,
                duration REAL
            )
        """)
        
        c.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON memories(timestamp)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(type)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)")
        
        conn.commit()
        conn.close()
    
    def save_node(self, node: MemoryNode):
        """Persist node to SQLite."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT OR REPLACE INTO memories 
            (id, type, content, metadata, timestamp, connections, importance, access_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            node.id,
            node.type,
            node.content,
            json.dumps(node.metadata),
            node.timestamp,
            json.dumps(node.connections),
            node.importance,
            node.access_count
        ))
        
        conn.commit()
        conn.close()
    
    def save_nodes(self, nodes: List[MemoryNode]):
        """Batch save nodes."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        data = [
            (n.id, n.type, n.content, json.dumps(n.metadata), n.timestamp,
             json.dumps(n.connections), n.importance, n.access_count)
            for n in nodes
        ]
        
        c.executemany("""
            INSERT OR REPLACE INTO memories 
            (id, type, content, metadata, timestamp, connections, importance, access_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            SELECT id, type, content, metadata, timestamp, connections, importance, access_count
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
                connections=json.loads(row[5]),
                importance=row[6],
                access_count=row[7]
            ))
        
        conn.close()
        return nodes
    
    def search_similar(self, query: str, limit: int = 5) -> List[MemoryNode]:
        """Search for similar memories (keyword matching)."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        keywords = query.lower().split()
        conditions = ' OR '.join(['LOWER(content) LIKE ?' for _ in keywords])
        params = [f'%{kw}%' for kw in keywords]
        
        c.execute(f"""
            SELECT id, type, content, metadata, timestamp, connections, importance, access_count
            FROM memories 
            WHERE {conditions}
            ORDER BY importance DESC, access_count DESC
            LIMIT ?
        """, params + [limit])
        
        nodes = []
        for row in c.fetchall():
            nodes.append(MemoryNode(
                id=row[0],
                type=row[1],
                content=row[2],
                metadata=json.loads(row[3]),
                timestamp=row[4],
                connections=json.loads(row[5]),
                importance=row[6],
                access_count=row[7]
            ))
        
        conn.close()
        return nodes
    
    def save_session(self, session_id: str, task: str, result: str, duration: float, timestamp: float):
        """Save completed session."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO sessions (id, task, timestamp, result, duration)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, task, timestamp, result, duration))
        
        conn.commit()
        conn.close()
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM memories")
        memory_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM sessions")
        session_count = c.fetchone()[0]
        
        conn.close()
        
        return {
            "total_memories": memory_count,
            "total_sessions": session_count
        }# implement initial memory store interface (2025-11-10)
