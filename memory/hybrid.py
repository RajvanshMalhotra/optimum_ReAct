"""Hybrid memory system combining graph and SQLite."""
import time
from typing import List, Dict
from datetime import datetime

from models.memory import MemoryNode
from memory.graph import MemoryGraph
from memory.store import MemoryStore
from config import MEMORY_PERSIST_BATCH_SIZE, MEMORY_SEARCH_LIMIT


class HybridMemory:
    """Hybrid memory system combining graph and SQLite."""
    
    def __init__(self, db_path: str):
        self.graph = MemoryGraph()
        self.store = MemoryStore(db_path)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def remember(
        self, 
        content: str, 
        mem_type: str = "thought", 
        importance: float = 0.5, 
        metadata: Dict = None
    ) -> str:
        """Store new memory."""
        node_id = f"{mem_type}_{self.graph.size()}_{int(time.time() * 1000)}"
        
        node = MemoryNode(
            id=node_id,
            type=mem_type,
            content=content,
            metadata=metadata or {},
            timestamp=time.time(),
            importance=importance
        )
        
        self.graph.add_node(node)
        
        # Auto-persist if graph is too large
        if self.graph.should_persist():
            self._persist_old_memories()
        
        return node_id
    
    def relate(self, from_id: str, to_id: str):
        """Create relationship between memories."""
        self.graph.connect(from_id, to_id)
    
    def recall(self, query: str, limit: int = MEMORY_SEARCH_LIMIT) -> List[MemoryNode]:
        """Retrieve relevant memories (hybrid search)."""
        # Search in-memory graph first
        graph_results = self.graph.search(query, limit=limit)
        
        # If not enough, search SQLite
        if len(graph_results) < limit:
            db_results = self.store.search_similar(query, limit=limit - len(graph_results))
            
            # Load them into graph for faster future access
            for node in db_results:
                if node.id not in self.graph.nodes:
                    self.graph.add_node(node)
            
            graph_results.extend(db_results)
        
        return graph_results[:limit]
    
    def _persist_old_memories(self):
        """Move old/unimportant memories to SQLite."""
        to_persist_ids = self.graph.get_least_important(count=MEMORY_PERSIST_BATCH_SIZE)
        
        nodes_to_save = []
        for node_id in to_persist_ids:
            node = self.graph.get_node(node_id)
            if node:
                nodes_to_save.append(node)
                self.graph.remove_node(node_id)
        
        if nodes_to_save:
            self.store.save_nodes(nodes_to_save)
    
    def save_session(self, task: str, result: str, duration: float):
        """Save completed session."""
        self.store.save_session(
            self.session_id, 
            task, 
            result, 
            duration,
            time.time()
        )
    
    def get_context_summary(self) -> str:
        """Get summary of current memory state."""
        stats = self.store.get_stats()
        return (f"Memory: {self.graph.size()} in RAM, "
                f"{stats['total_memories']} in DB | "
                f"Session: {self.session_id}")