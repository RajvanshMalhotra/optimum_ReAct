# """In-memory graph for fast memory access."""
# from typing import Dict, List
# from models.memory import MemoryNode
# from config import MEMORY_MAX_GRAPH_NODES


# class MemoryGraph:
#     """In-memory graph for fast access."""
    
#     def __init__(self, max_nodes: int = MEMORY_MAX_GRAPH_NODES):
#         self.nodes: Dict[str, MemoryNode] = {}
#         self.max_nodes = max_nodes
        
#     def add_node(self, node: MemoryNode):
#         """Add node to graph."""
#         self.nodes[node.id] = node
        
#     def connect(self, from_id: str, to_id: str):
#         """Create edge between nodes."""
#         if from_id in self.nodes and to_id in self.nodes:
#             if to_id not in self.nodes[from_id].connections:
#                 self.nodes[from_id].connections.append(to_id)
    
#     def get_node(self, node_id: str) -> MemoryNode | None:
#         """Get single node by ID."""
#         return self.nodes.get(node_id)
    
#     def get_related(self, node_id: str, depth: int = 2) -> List[MemoryNode]:
#         """Get related nodes up to depth."""
#         visited = set()
#         result = []
        
#         def traverse(nid: str, d: int):
#             if d > depth or nid in visited:
#                 return
#             visited.add(nid)
            
#             if nid in self.nodes:
#                 node = self.nodes[nid]
#                 node.access_count += 1
#                 result.append(node)
                
#                 for conn in node.connections:
#                     traverse(conn, d + 1)
        
#         traverse(node_id, 0)
#         return result
    
#     def search(self, query: str, limit: int = 5) -> List[MemoryNode]:
#         """Semantic search in graph (keyword matching)."""
#         query_lower = query.lower()
#         matches = []
        
#         for node in self.nodes.values():
#             content_lower = node.content.lower()
#             score = sum(1 for word in query_lower.split() if word in content_lower)
#             if score > 0:
#                 matches.append((score, node))
        
#         matches.sort(reverse=True, key=lambda x: x[0])
#         return [node for _, node in matches[:limit]]
    
#     def should_persist(self) -> bool:
#         """Check if graph is too large."""
#         return len(self.nodes) >= self.max_nodes
    
#     def get_least_important(self, count: int = 20) -> List[str]:
#         """Get least important nodes to persist."""
#         sorted_nodes = sorted(
#             self.nodes.values(),
#             key=lambda n: (n.importance * 0.7 + (n.access_count / 10) * 0.3)
#         )
#         return [n.id for n in sorted_nodes[:count]]
    
#     def remove_node(self, node_id: str):
#         """Remove node from graph."""
#         if node_id in self.nodes:
#             del self.nodes[node_id]
    
#     def size(self) -> int:
#         """Get current graph size."""
#         return len(self.nodes)# add basic graph memory structure (2025-11-09)
# # add node linking logic (2025-11-14)
# # optimize traversal logic (2025-11-20)
# # add edge weighting support (2025-11-25)
# # handle cyclic references (2025-11-30)
# # simplify node lookup (2025-12-05)
# # add comments for future optimizations (2025-12-11)


"""In-memory graph for fast memory access with proper graph utilization."""
import time
import math
from typing import Dict, List, Set, Tuple
from models.memory import MemoryNode
from config import MEMORY_MAX_GRAPH_NODES


class MemoryGraph:
    """In-memory graph with actual graph algorithms and smart eviction."""
    
    def __init__(self, max_nodes: int = MEMORY_MAX_GRAPH_NODES):
        self.nodes: Dict[str, MemoryNode] = {}
        self.max_nodes = max_nodes
        self._last_cleanup = time.time()
        
    def add_node(self, node: MemoryNode):
        """Add node to graph."""
        self.nodes[node.id] = node
        
    def connect(self, from_id: str, to_id: str, weight: float = 1.0):
        """Create weighted edge between nodes."""
        if from_id in self.nodes and to_id in self.nodes:
            # Store connections as tuples: (target_id, weight)
            from_node = self.nodes[from_id]
            # Update or add connection
            connections = [(cid, w) for cid, w in from_node.connections if cid != to_id]
            connections.append((to_id, weight))
            from_node.connections = connections
    
    def get_node(self, node_id: str) -> MemoryNode | None:
        """Get single node by ID."""
        node = self.nodes.get(node_id)
        if node:
            node.access_count += 1
            node.last_accessed = time.time()
        return node
    
    def get_related(self, node_id: str, depth: int = 2, limit: int = 10) -> List[MemoryNode]:
        """Get related nodes using BFS with importance scoring."""
        if node_id not in self.nodes:
            return []
        
        visited: Set[str] = set()
        queue: List[Tuple[str, int, float]] = [(node_id, 0, 1.0)]  # (id, depth, relevance_score)
        results: List[Tuple[float, MemoryNode]] = []
        
        while queue and len(results) < limit * 2:
            current_id, current_depth, relevance = queue.pop(0)
            
            if current_id in visited or current_depth > depth:
                continue
            
            visited.add(current_id)
            
            if current_id in self.nodes:
                node = self.nodes[current_id]
                node.access_count += 1
                node.last_accessed = time.time()
                
                # Score = importance * relevance * recency
                recency = self._recency_score(node.last_accessed)
                score = node.importance * relevance * recency
                
                if current_id != node_id:  # Don't include the query node itself
                    results.append((score, node))
                
                # Add connected nodes to queue with decayed relevance
                for conn_data in node.connections:
                    if isinstance(conn_data, tuple):
                        conn_id, weight = conn_data
                    else:
                        # Backward compatibility if connections are just strings
                        conn_id, weight = conn_data, 1.0
                    
                    if conn_id not in visited:
                        # Decay relevance by depth and edge weight
                        new_relevance = relevance * weight * 0.7
                        queue.append((conn_id, current_depth + 1, new_relevance))
        
        # Sort by score and return top nodes
        results.sort(reverse=True, key=lambda x: x[0])
        return [node for _, node in results[:limit]]
    
    def search(self, query: str, limit: int = 5) -> List[MemoryNode]:
        """Enhanced keyword search with TF-IDF-like scoring."""
        if not query.strip():
            return []
        
        query_terms = set(query.lower().split())
        matches: List[Tuple[float, MemoryNode]] = []
        
        # Build term frequency across all documents (simple IDF)
        doc_count = len(self.nodes)
        if doc_count == 0:
            return []
        
        term_doc_freq: Dict[str, int] = {}
        
        for node in self.nodes.values():
            content_terms = set(node.content.lower().split())
            for term in content_terms:
                term_doc_freq[term] = term_doc_freq.get(term, 0) + 1
        
        # Score each document
        for node in self.nodes.values():
            content_lower = node.content.lower()
            content_terms = content_lower.split()
            
            if not content_terms:  # Skip empty content
                continue
            
            # TF-IDF scoring
            tf_idf_score = 0.0
            for term in query_terms:
                if term in content_lower:
                    # Term frequency in this document
                    tf = content_terms.count(term) / len(content_terms)
                    # Inverse document frequency (add 1 to numerator to prevent 0)
                    idf = math.log((doc_count + 1) / (term_doc_freq.get(term, 0) + 1))
                    tf_idf_score += tf * idf
            
            if tf_idf_score > 0:
                # Combine with importance and recency
                recency = self._recency_score(node.last_accessed)
                access_boost = min(node.access_count / 10, 2.0)  # Cap at 2x boost
                
                final_score = (
                    tf_idf_score * 0.5 +
                    node.importance * 0.3 +
                    recency * 0.1 +
                    access_boost * 0.1
                )
                
                matches.append((final_score, node))
        
        matches.sort(reverse=True, key=lambda x: x[0])
        
        # Update access for returned nodes
        for _, node in matches[:limit]:
            node.access_count += 1
            node.last_accessed = time.time()
        
        return [node for _, node in matches[:limit]]
    
    def _recency_score(self, timestamp: float) -> float:
        """Calculate recency score with exponential decay."""
        age_seconds = time.time() - timestamp
        age_hours = age_seconds / 3600
        
        # Exponential decay: half-life of 24 hours
        decay_rate = math.log(2) / 24
        return math.exp(-decay_rate * age_hours)
    
    def should_persist(self) -> bool:
        """Check if graph is too large."""
        return len(self.nodes) >= self.max_nodes
    
    def get_nodes_to_evict(self, count: int = 20) -> List[str]:
        """Get least valuable nodes to persist using multi-factor scoring."""
        current_time = time.time()
        scored_nodes: List[Tuple[float, str]] = []
        
        for node in self.nodes.values():
            # Multi-factor eviction score (lower = more likely to evict)
            recency = self._recency_score(node.last_accessed)
            access_score = min(node.access_count / 20, 1.0)  # Normalize to 0-1
            
            # Eviction score components:
            # - Importance (0-1): Base importance set by system
            # - Recency (0-1): How recently accessed
            # - Access (0-1): How frequently accessed
            # - Connection weight: Nodes with many connections are more valuable
            connection_score = min(len(node.connections) / 5, 1.0)
            
            retention_score = (
                node.importance * 0.4 +
                recency * 0.3 +
                access_score * 0.2 +
                connection_score * 0.1
            )
            
            scored_nodes.append((retention_score, node.id))
        
        # Sort by retention score (ascending) - lowest scores evicted first
        scored_nodes.sort(key=lambda x: x[0])
        
        # Return IDs of nodes to evict
        return [node_id for _, node_id in scored_nodes[:count]]
    
    def remove_node(self, node_id: str):
        """Remove node from graph and clean up connections."""
        if node_id in self.nodes:
            # Remove the node
            del self.nodes[node_id]
            
            # Remove references to this node from other nodes' connections
            for node in self.nodes.values():
                node.connections = [
                    conn for conn in node.connections
                    if (conn[0] if isinstance(conn, tuple) else conn) != node_id
                ]
    
    def find_clusters(self, min_cluster_size: int = 3) -> List[List[str]]:
        """Find connected clusters of memories (for context grouping)."""
        visited: Set[str] = set()
        clusters: List[List[str]] = []
        
        def dfs(node_id: str, cluster: List[str]):
            if node_id in visited or node_id not in self.nodes:
                return
            
            visited.add(node_id)
            cluster.append(node_id)
            
            node = self.nodes[node_id]
            for conn_data in node.connections:
                conn_id = conn_data[0] if isinstance(conn_data, tuple) else conn_data
                dfs(conn_id, cluster)
        
        for node_id in self.nodes:
            if node_id not in visited:
                cluster: List[str] = []
                dfs(node_id, cluster)
                if len(cluster) >= min_cluster_size:
                    clusters.append(cluster)
        
        return clusters
    
    def get_context_summary(self) -> Dict[str, int]:
        """Get summary statistics for debugging."""
        type_counts: Dict[str, int] = {}
        for node in self.nodes.values():
            type_counts[node.type] = type_counts.get(node.type, 0) + 1
        
        return {
            "total_nodes": len(self.nodes),
            "types": type_counts,
            "avg_connections": sum(len(n.connections) for n in self.nodes.values()) / max(len(self.nodes), 1)
        }
    
    def size(self) -> int:
        """Get current graph size."""
        return len(self.nodes)