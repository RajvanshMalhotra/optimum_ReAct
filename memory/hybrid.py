# """Hybrid memory system combining graph and SQLite."""
# import time
# from typing import List, Dict
# from datetime import datetime

# from models.memory import MemoryNode
# from memory.graph import MemoryGraph
# from memory.store import MemoryStore
# from config import MEMORY_PERSIST_BATCH_SIZE, MEMORY_SEARCH_LIMIT


# class HybridMemory:
#     """Hybrid memory system combining graph and SQLite."""
    
#     def __init__(self, db_path: str):
#         self.graph = MemoryGraph()
#         self.store = MemoryStore(db_path)
#         self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
#     def remember(
#         self, 
#         content: str, 
#         mem_type: str = "thought", 
#         importance: float = 0.5, 
#         metadata: Dict = None
#     ) -> str:
#         """Store new memory."""
#         node_id = f"{mem_type}_{self.graph.size()}_{int(time.time() * 1000)}"
        
#         node = MemoryNode(
#             id=node_id,
#             type=mem_type,
#             content=content,
#             metadata=metadata or {},
#             timestamp=time.time(),
#             importance=importance
#         )
        
#         self.graph.add_node(node)
        
#         # Auto-persist if graph is too large
#         if self.graph.should_persist():
#             self._persist_old_memories()
        
#         return node_id
    
#     def relate(self, from_id: str, to_id: str):
#         """Create relationship between memories."""
#         self.graph.connect(from_id, to_id)
    
#     def recall(self, query: str, limit: int = MEMORY_SEARCH_LIMIT) -> List[MemoryNode]:
#         """Retrieve relevant memories (hybrid search)."""
#         # Search in-memory graph first
#         graph_results = self.graph.search(query, limit=limit)
        
#         # If not enough, search SQLite
#         if len(graph_results) < limit:
#             db_results = self.store.search_similar(query, limit=limit - len(graph_results))
            
#             # Load them into graph for faster future access
#             for node in db_results:
#                 if node.id not in self.graph.nodes:
#                     self.graph.add_node(node)
            
#             graph_results.extend(db_results)
        
#         return graph_results[:limit]
    
#     def _persist_old_memories(self):
#         """Move old/unimportant memories to SQLite."""
#         to_persist_ids = self.graph.get_least_important(count=MEMORY_PERSIST_BATCH_SIZE)
        
#         nodes_to_save = []
#         for node_id in to_persist_ids:
#             node = self.graph.get_node(node_id)
#             if node:
#                 nodes_to_save.append(node)
#                 self.graph.remove_node(node_id)
        
#         if nodes_to_save:
#             self.store.save_nodes(nodes_to_save)
    
#     def save_session(self, task: str, result: str, duration: float):
#         """Save completed session."""
#         self.store.save_session(
#             self.session_id, 
#             task, 
#             result, 
#             duration,
#             time.time()
#         )
    
#     def get_context_summary(self) -> str:
#         """Get summary of current memory state."""
#         stats = self.store.get_stats()
#         return (f"Memory: {self.graph.size()} in RAM, "
#                 f"{stats['total_memories']} in DB | "
#                 f"Session: {self.session_id}")# introduce hybrid memory placeholder (2025-11-13)
# # combine graph and store strategies (2025-11-19)
# # prioritize recent memories (2025-11-26)
# # improve fallback strategy (2025-12-02)
# # tune memory merge logic (2025-12-08)

"""Hybrid memory system with proper graph utilization and session linking."""
import time
from typing import List, Dict, Optional
from datetime import datetime

from models.memory import MemoryNode
from memory.graph import MemoryGraph
from memory.store import MemoryStore
from config import MEMORY_PERSIST_BATCH_SIZE, MEMORY_SEARCH_LIMIT


class HybridMemory:
    """Hybrid memory system with enhanced search and session tracking."""
    
    def __init__(self, db_path: str):
        self.graph = MemoryGraph()
        self.store = MemoryStore(db_path)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_memory_count = 0
        self._load_recent_context()
    
    def _load_recent_context(self):
        """Load recent important memories from last session into graph."""
        # Find similar past sessions
        # This is a placeholder - will be called with actual task after agent starts
        pass
    
    def load_past_session_context(self, task: str):
        """Load relevant context from similar past sessions."""
        similar_sessions = self.store.find_similar_sessions(task, limit=3)
        
        if similar_sessions:
            print(f"💡 Found {len(similar_sessions)} similar past sessions")
            
            # Load memories from most recent relevant sessions
            loaded_count = 0
            for session in similar_sessions[:2]:  # Check top 2 sessions
                memories = self.store.get_session_memories(session['id'])
                
                # Load ALL memories from past sessions (not just high importance)
                # This ensures we recall user preferences, facts, etc.
                for mem in memories:
                    if mem.id not in self.graph.nodes:
                        self.graph.add_node(mem)
                        loaded_count += 1
            
            if loaded_count > 0:
                print(f"   Loaded {loaded_count} memories from past sessions")
    
    def remember(
        self, 
        content: str, 
        mem_type: str = "thought", 
        importance: float = 0.5, 
        metadata: Dict = None
    ) -> str:
        """Store new memory with full content."""
        current_time = time.time()
        node_id = f"{mem_type}_{self.graph.size()}_{int(current_time * 1000)}"
        
        node = MemoryNode(
            id=node_id,
            type=mem_type,
            content=content,  # Store full content, no truncation
            metadata=metadata or {},
            timestamp=current_time,
            last_accessed=current_time,  # Set last_accessed to now
            importance=importance
        )
        
        self.graph.add_node(node)
        self.session_memory_count += 1
        
        # Auto-persist if graph is too large
        if self.graph.should_persist():
            self._persist_old_memories()
        
        return node_id
    
    def relate(self, from_id: str, to_id: str, weight: float = 1.0):
        """Create weighted relationship between memories."""
        self.graph.connect(from_id, to_id, weight)
    
    def recall(
        self, 
        query: str, 
        limit: int = MEMORY_SEARCH_LIMIT,
        use_graph_traversal: bool = True
    ) -> List[MemoryNode]:
        """Retrieve relevant memories using multiple strategies."""
        results: List[MemoryNode] = []
        seen_ids: set = set()
        
        # Strategy 1: Search in-memory graph (keyword-based)
        # graph_results = self.graph.search(query, limit=limit)
        # for node in graph_results:
        #     if node.id not in seen_ids:
        #         results.append(node)
        #         seen_ids.add(node.id)
        
        graph_results = self.graph.search(query, limit=limit * 2)  # Get more results
        for node in graph_results:
            if node.id not in seen_ids:
                results.append(node)
                seen_ids.add(node.id)
    
    # If query mentions "me", "my", "I" - prioritize preference/fact types
        if any(word in query.lower() for word in ["me", "my", "i", "about me"]):
            # Add all fact/preference memories
            for node in self.graph.nodes.values():
                if node.type in ["fact", "preference"] and node.id not in seen_ids:
                    results.append(node)
                    seen_ids.add(node.id)
        # Strategy 2: If we have graph results, get related nodes via graph traversal
        if use_graph_traversal and graph_results and len(results) < limit:
            for node in graph_results[:2]:  # Use top 2 matches as seeds
                related = self.graph.get_related(node.id, depth=2, limit=5)
                for rel_node in related:
                    if rel_node.id not in seen_ids and len(results) < limit:
                        results.append(rel_node)
                        seen_ids.add(rel_node.id)
        
        # Strategy 3: Search SQLite with FTS if still need more
        if len(results) < limit:
            db_results = self.store.search_similar(query, limit=limit - len(results))
            
            # Load DB results into graph for faster future access
            for node in db_results:
                if node.id not in seen_ids:
                    if node.id not in self.graph.nodes:
                        self.graph.add_node(node)
                    results.append(node)
                    seen_ids.add(node.id)
        
        return results[:limit]
    
    def recall_context(self, query: str, max_tokens: int = 1000) -> str:
        """Recall memories and format for context window with token limit."""
        memories = self.recall(query, limit=10)
        
        if not memories:
            return "No relevant memories found."
        
        # Build context with token approximation (rough: 1 token ≈ 4 chars)
        context_parts = []
        current_tokens = 0
        
        for mem in memories:
            # Format: [TYPE] content (truncate if needed)
            mem_text = f"[{mem.type.upper()}] {mem.content}"
            mem_tokens = len(mem_text) // 4
            
            if current_tokens + mem_tokens > max_tokens:
                # Truncate to fit
                remaining_chars = (max_tokens - current_tokens) * 4
                if remaining_chars > 50:  # Only add if meaningful
                    mem_text = mem_text[:remaining_chars] + "..."
                    context_parts.append(mem_text)
                break
            
            context_parts.append(mem_text)
            current_tokens += mem_tokens
        
        return "\n".join(context_parts)
    
    def get_conversation_thread(self, node_id: str, max_depth: int = 5) -> List[MemoryNode]:
        """Get conversation thread by following connections."""
        return self.graph.get_related(node_id, depth=max_depth, limit=20)
    
    def find_memory_clusters(self) -> List[List[str]]:
        """Find clusters of related memories (useful for summarization)."""
        return self.graph.find_clusters(min_cluster_size=3)
    
    def _persist_old_memories(self):
        """Move old/unimportant memories to SQLite with session tracking."""
        to_persist_ids = self.graph.get_nodes_to_evict(count=MEMORY_PERSIST_BATCH_SIZE)
        
        nodes_to_save = []
        for node_id in to_persist_ids:
            node = self.graph.get_node(node_id)
            if node:
                nodes_to_save.append(node)
                self.graph.remove_node(node_id)
        
        if nodes_to_save:
            self.store.save_nodes(nodes_to_save, session_id=self.session_id)
            print(f"📦 Persisted {len(nodes_to_save)} memories to disk")
    
    def save_session(self, task: str, result: str, duration: float):
        """Save completed session with all remaining memories."""
        # Persist all remaining graph memories with session link
        all_nodes = list(self.graph.nodes.values())
        if all_nodes:
            self.store.save_nodes(all_nodes, session_id=self.session_id)
        
        # Save session metadata
        self.store.save_session(
            self.session_id, 
            task, 
            result, 
            duration,
            time.time(),
            self.session_memory_count
        )
        
        print(f"💾 Session saved: {self.session_memory_count} memories")
    
    def get_context_summary(self) -> str:
        """Get summary of current memory state."""
        stats = self.store.get_stats()
        graph_stats = self.graph.get_context_summary()
        
        return (
            f"Memory: {graph_stats['total_nodes']} in RAM "
            f"({graph_stats.get('types', {})}), "
            f"{stats['total_memories']} in DB | "
            f"Session: {self.session_id} ({self.session_memory_count} created)"
        )
    
    def cleanup_old_data(self, days: int = 30):
        """Cleanup old low-value memories."""
        deleted = self.store.cleanup_old_memories(days)
        print(f"🧹 Cleaned up {deleted} old memories")
        return deleted
    
    def get_statistics(self) -> Dict:
        """Get detailed statistics for debugging/monitoring."""
        store_stats = self.store.get_stats()
        graph_stats = self.graph.get_context_summary()
        
        return {
            "session_id": self.session_id,
            "session_memory_count": self.session_memory_count,
            "graph": graph_stats,
            "store": store_stats,
            "total_memories": graph_stats['total_nodes'] + store_stats['total_memories']
        }
