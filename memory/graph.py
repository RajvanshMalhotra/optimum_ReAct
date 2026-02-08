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


# class MemoryGraph:
#     """In-memory graph with actual graph algorithms and smart eviction."""
    
#     def __init__(self, max_nodes: int = MEMORY_MAX_GRAPH_NODES):
#         self.nodes: Dict[str, MemoryNode] = {}
#         self.max_nodes = max_nodes
#         self._last_cleanup = time.time()
        
#     def add_node(self, node: MemoryNode):
#         """Add node to graph."""
#         self.nodes[node.id] = node
        
#     def connect(self, from_id: str, to_id: str, weight: float = 1.0):
#         """Create weighted edge between nodes."""
#         if from_id in self.nodes and to_id in self.nodes:
#             # Store connections as tuples: (target_id, weight)
#             from_node = self.nodes[from_id]
#             # Update or add connection
#             connections = [(cid, w) for cid, w in from_node.connections if cid != to_id]
#             connections.append((to_id, weight))
#             from_node.connections = connections
    
#     def get_node(self, node_id: str) -> MemoryNode | None:
#         """Get single node by ID."""
#         node = self.nodes.get(node_id)
#         if node:
#             node.access_count += 1
#             node.last_accessed = time.time()
#         return node
    
#     def get_related(self, node_id: str, depth: int = 2, limit: int = 10) -> List[MemoryNode]:
#         """Get related nodes using BFS with importance scoring."""
#         if node_id not in self.nodes:
#             return []
        
#         visited: Set[str] = set()
#         queue: List[Tuple[str, int, float]] = [(node_id, 0, 1.0)]  # (id, depth, relevance_score)
#         results: List[Tuple[float, MemoryNode]] = []
        
#         while queue and len(results) < limit * 2:
#             current_id, current_depth, relevance = queue.pop(0)
            
#             if current_id in visited or current_depth > depth:
#                 continue
            
#             visited.add(current_id)
            
#             if current_id in self.nodes:
#                 node = self.nodes[current_id]
#                 node.access_count += 1
#                 node.last_accessed = time.time()
                
#                 # Score = importance * relevance * recency
#                 recency = self._recency_score(node.last_accessed)
#                 score = node.importance * relevance * recency
                
#                 if current_id != node_id:  # Don't include the query node itself
#                     results.append((score, node))
                
#                 # Add connected nodes to queue with decayed relevance
#                 for conn_data in node.connections:
#                     if isinstance(conn_data, tuple):
#                         conn_id, weight = conn_data
#                     else:
#                         # Backward compatibility if connections are just strings
#                         conn_id, weight = conn_data, 1.0
                    
#                     if conn_id not in visited:
#                         # Decay relevance by depth and edge weight
#                         new_relevance = relevance * weight * 0.7
#                         queue.append((conn_id, current_depth + 1, new_relevance))
        
#         # Sort by score and return top nodes
#         results.sort(reverse=True, key=lambda x: x[0])
#         return [node for _, node in results[:limit]]
    
#     def search(self, query: str, limit: int = 5) -> List[MemoryNode]:
#         """Enhanced keyword search with TF-IDF-like scoring."""
#         if not query.strip():
#             return []
        
#         query_terms = set(query.lower().split())
#         matches: List[Tuple[float, MemoryNode]] = []
        
#         # Build term frequency across all documents (simple IDF)
#         doc_count = len(self.nodes)
#         if doc_count == 0:
#             return []
        
#         term_doc_freq: Dict[str, int] = {}
        
#         for node in self.nodes.values():
#             content_terms = set(node.content.lower().split())
#             for term in content_terms:
#                 term_doc_freq[term] = term_doc_freq.get(term, 0) + 1
        
#         # Score each document
#         for node in self.nodes.values():
#             content_lower = node.content.lower()
#             content_terms = content_lower.split()
            
#             if not content_terms:  # Skip empty content
#                 continue
            
#             # TF-IDF scoring
#             tf_idf_score = 0.0
#             for term in query_terms:
#                 if term in content_lower:
#                     # Term frequency in this document
#                     tf = content_terms.count(term) / len(content_terms)
#                     # Inverse document frequency (add 1 to numerator to prevent 0)
#                     idf = math.log((doc_count + 1) / (term_doc_freq.get(term, 0) + 1))
#                     tf_idf_score += tf * idf
            
#             if tf_idf_score > 0:
#                 # Combine with importance and recency
#                 recency = self._recency_score(node.last_accessed)
#                 access_boost = min(node.access_count / 10, 2.0)  # Cap at 2x boost
                
#                 final_score = (
#                     tf_idf_score * 0.5 +
#                     node.importance * 0.3 +
#                     recency * 0.1 +
#                     access_boost * 0.1
#                 )
                
#                 matches.append((final_score, node))
        
#         matches.sort(reverse=True, key=lambda x: x[0])
        
#         # Update access for returned nodes
#         for _, node in matches[:limit]:
#             node.access_count += 1
#             node.last_accessed = time.time()
        
#         return [node for _, node in matches[:limit]]
    
#     def _recency_score(self, timestamp: float) -> float:
#         """Calculate recency score with exponential decay."""
#         age_seconds = time.time() - timestamp
#         age_hours = age_seconds / 3600
        
#         # Exponential decay: half-life of 24 hours
#         decay_rate = math.log(2) / 24
#         return math.exp(-decay_rate * age_hours)
    
#     def should_persist(self) -> bool:
#         """Check if graph is too large."""
#         return len(self.nodes) >= self.max_nodes
    
#     def get_nodes_to_evict(self, count: int = 20) -> List[str]:
#         """Get least valuable nodes to persist using multi-factor scoring."""
#         current_time = time.time()
#         scored_nodes: List[Tuple[float, str]] = []
        
#         for node in self.nodes.values():
#             # Multi-factor eviction score (lower = more likely to evict)
#             recency = self._recency_score(node.last_accessed)
#             access_score = min(node.access_count / 20, 1.0)  # Normalize to 0-1
            
#             # Eviction score components:
#             # - Importance (0-1): Base importance set by system
#             # - Recency (0-1): How recently accessed
#             # - Access (0-1): How frequently accessed
#             # - Connection weight: Nodes with many connections are more valuable
#             connection_score = min(len(node.connections) / 5, 1.0)
            
#             retention_score = (
#                 node.importance * 0.4 +
#                 recency * 0.3 +
#                 access_score * 0.2 +
#                 connection_score * 0.1
#             )
            
#             scored_nodes.append((retention_score, node.id))
        
#         # Sort by retention score (ascending) - lowest scores evicted first
#         scored_nodes.sort(key=lambda x: x[0])
        
#         # Return IDs of nodes to evict
#         return [node_id for _, node_id in scored_nodes[:count]]
    
#     def remove_node(self, node_id: str):
#         """Remove node from graph and clean up connections."""
#         if node_id in self.nodes:
#             # Remove the node
#             del self.nodes[node_id]
            
#             # Remove references to this node from other nodes' connections
#             for node in self.nodes.values():
#                 node.connections = [
#                     conn for conn in node.connections
#                     if (conn[0] if isinstance(conn, tuple) else conn) != node_id
#                 ]
    
#     def find_clusters(self, min_cluster_size: int = 3) -> List[List[str]]:
#         """Find connected clusters of memories (for context grouping)."""
#         visited: Set[str] = set()
#         clusters: List[List[str]] = []
        
#         def dfs(node_id: str, cluster: List[str]):
#             if node_id in visited or node_id not in self.nodes:
#                 return
            
#             visited.add(node_id)
#             cluster.append(node_id)
            
#             node = self.nodes[node_id]
#             for conn_data in node.connections:
#                 conn_id = conn_data[0] if isinstance(conn_data, tuple) else conn_data
#                 dfs(conn_id, cluster)
        
#         for node_id in self.nodes:
#             if node_id not in visited:
#                 cluster: List[str] = []
#                 dfs(node_id, cluster)
#                 if len(cluster) >= min_cluster_size:
#                     clusters.append(cluster)
        
#         return clusters
    
#     def get_context_summary(self) -> Dict[str, int]:
#         """Get summary statistics for debugging."""
#         type_counts: Dict[str, int] = {}
#         for node in self.nodes.values():
#             type_counts[node.type] = type_counts.get(node.type, 0) + 1
        
#         return {
#             "total_nodes": len(self.nodes),
#             "types": type_counts,
#             "avg_connections": sum(len(n.connections) for n in self.nodes.values()) / max(len(self.nodes), 1)
#         }
    
#     def size(self) -> int:
#         """Get current graph size."""
#         return len(self.nodes)


"""In-memory graph for fast memory access with proper graph utilization."""
import time
import math
import numpy as np
from typing import Dict, List, Set, Tuple, Optional
from models.memory import MemoryNode
from config import MEMORY_MAX_GRAPH_NODES

# Try to import sentence transformers for semantic search
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


class BM25Ranker:
    """BM25 ranking algorithm for better keyword search."""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Args:
            k1: Term frequency saturation parameter (typical: 1.2-2.0)
            b: Document length normalization (0=no norm, 1=full norm)
        """
        self.k1 = k1
        self.b = b
        self.idf_cache: Dict[str, float] = {}
        self.avg_doc_len = 0.0
        self.doc_lens: Dict[str, int] = {}
    
    def build_index(self, nodes: Dict[str, MemoryNode]):
        """Build BM25 index from nodes."""
        if not nodes:
            return
        
        # Calculate document lengths
        total_len = 0
        term_doc_freq: Dict[str, int] = {}
        
        for node_id, node in nodes.items():
            terms = node.content.lower().split()
            doc_len = len(terms)
            self.doc_lens[node_id] = doc_len
            total_len += doc_len
            
            # Count unique terms in this document
            unique_terms = set(terms)
            for term in unique_terms:
                term_doc_freq[term] = term_doc_freq.get(term, 0) + 1
        
        # Average document length
        self.avg_doc_len = total_len / len(nodes) if nodes else 0
        
        # Calculate IDF for each term
        num_docs = len(nodes)
        self.idf_cache.clear()
        
        for term, df in term_doc_freq.items():
            # BM25 IDF formula
            idf = math.log((num_docs - df + 0.5) / (df + 0.5) + 1.0)
            self.idf_cache[term] = idf
    
    def score_document(self, node: MemoryNode, query_terms: List[str]) -> float:
        """Calculate BM25 score for a document."""
        if node.id not in self.doc_lens:
            return 0.0
        
        doc_terms = node.content.lower().split()
        doc_len = self.doc_lens[node.id]
        
        # Avoid division by zero
        if self.avg_doc_len == 0:
            return 0.0
        
        score = 0.0
        term_freqs: Dict[str, int] = {}
        
        # Count term frequencies in document
        for term in doc_terms:
            term_freqs[term] = term_freqs.get(term, 0) + 1
        
        # Calculate BM25 score
        for term in query_terms:
            if term not in term_freqs:
                continue
            
            tf = term_freqs[term]
            idf = self.idf_cache.get(term, 0.0)
            
            # Document length normalization factor
            norm = 1 - self.b + self.b * (doc_len / self.avg_doc_len)
            
            # BM25 formula
            term_score = idf * (tf * (self.k1 + 1)) / (tf + self.k1 * norm)
            score += term_score
        
        return score


class EmbeddingSearcher:
    """Semantic search using sentence embeddings."""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Args:
            model_name: HuggingFace model name
                - 'all-MiniLM-L6-v2': Fast, 384 dims, ~80MB
                - 'all-mpnet-base-v2': Better quality, 768 dims, ~420MB
        """
        if not EMBEDDINGS_AVAILABLE:
            raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")
        
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        # Store embeddings: node_id -> embedding vector
        self.embeddings: Dict[str, np.ndarray] = {}
    
    def encode(self, text: str) -> np.ndarray:
        """Convert text to embedding vector."""
        return self.model.encode(text, convert_to_numpy=True)
    
    def add_node(self, node_id: str, content: str):
        """Add node embedding to index."""
        embedding = self.encode(content)
        self.embeddings[node_id] = embedding
    
    def remove_node(self, node_id: str):
        """Remove node embedding."""
        if node_id in self.embeddings:
            del self.embeddings[node_id]
    
    def search(self, query: str, limit: int = 10) -> List[Tuple[str, float]]:
        """Search by semantic similarity.
        
        Returns:
            List of (node_id, similarity_score) tuples
        """
        if not self.embeddings:
            return []
        
        # Encode query
        query_embedding = self.encode(query)
        
        # Calculate cosine similarity with all embeddings
        results: List[Tuple[str, float]] = []
        
        for node_id, node_embedding in self.embeddings.items():
            # Cosine similarity
            similarity = self._cosine_similarity(query_embedding, node_embedding)
            results.append((node_id, similarity))
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:limit]
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot_product / (norm_a * norm_b))
    
    def clear(self):
        """Clear all embeddings."""
        self.embeddings.clear()


class MemoryGraph:
    """In-memory graph with actual graph algorithms and smart eviction."""
    
    def __init__(self, max_nodes: int = MEMORY_MAX_GRAPH_NODES):
        self.nodes: Dict[str, MemoryNode] = {}
        self.max_nodes = max_nodes
        self._last_cleanup = time.time()
        
        # Inverted index for efficient search: term -> set of node_ids
        self._term_index: Dict[str, Set[str]] = {}
        # Cached IDF scores: term -> idf_score
        self._idf_cache: Dict[str, float] = {}
        # Track if cache needs rebuild
        self._index_dirty = False
        
        # BM25 ranker for better keyword search
        self.bm25 = BM25Ranker(k1=1.5, b=0.75)
        
        # Embeddings for semantic search
        try:
            self.embeddings = EmbeddingSearcher(model_name='all-MiniLM-L6-v2')
            self._embeddings_enabled = True
            print("✅ Semantic search enabled (all-MiniLM-L6-v2)")
        except Exception as e:
            self._embeddings_enabled = False
            print(f"⚠️  Semantic search disabled: {e}")
            print("   Install with: pip install sentence-transformers")
        
    def add_node(self, node: MemoryNode):
        """Add node to graph and update search indices."""
        self.nodes[node.id] = node
        
        # Update inverted index
        terms = node.content.lower().split()
        for term in terms:
            if term not in self._term_index:
                self._term_index[term] = set()
            self._term_index[term].add(node.id)
        
        # Add embedding for semantic search
        if self._embeddings_enabled:
            try:
                self.embeddings.add_node(node.id, node.content)
            except Exception as e:
                print(f"⚠️  Failed to add embedding for {node.id}: {e}")
        
        # Mark index as dirty (needs IDF recalculation)
        self._index_dirty = True
        
    def connect(self, from_id: str, to_id: str, weight: float = 1.0, bidirectional: bool = True, strengthen: bool = True):
        """Create weighted edge between nodes with temporal strengthening.
        
        Args:
            from_id: Source node ID
            to_id: Target node ID
            weight: Edge weight (default 1.0)
            bidirectional: If True, create edge in both directions (default True)
            strengthen: If True and edge exists, strengthen it rather than replace (default True)
        """
        if from_id not in self.nodes or to_id not in self.nodes:
            return
        
        # Create forward edge: from_id -> to_id
        self._create_or_strengthen_edge(from_id, to_id, weight, strengthen)
        
        # Create backward edge: to_id -> from_id (if bidirectional)
        if bidirectional and from_id != to_id:  # Avoid self-loop duplication
            self._create_or_strengthen_edge(to_id, from_id, weight, strengthen)
    
    def _create_or_strengthen_edge(self, from_id: str, to_id: str, weight: float, strengthen: bool):
        """Helper to create or strengthen a single edge."""
        from_node = self.nodes[from_id]
        
        # Find existing connection
        existing_idx = None
        for i, (cid, w) in enumerate(from_node.connections):
            if cid == to_id:
                existing_idx = i
                break
        
        if existing_idx is not None and strengthen:
            # Strengthen existing connection with exponential moving average
            # This makes frequently traversed paths stronger over time
            old_weight = from_node.connections[existing_idx][1]
            # 80% old weight + 20% new weight = gradual strengthening
            new_weight = old_weight * 0.8 + weight * 0.2
            # Cap at 2.0 to prevent runaway strengthening
            from_node.connections[existing_idx] = (to_id, min(new_weight, 2.0))
        elif existing_idx is not None:
            # Replace weight (old behavior)
            from_node.connections[existing_idx] = (to_id, weight)
        else:
            # New connection
            from_node.connections.append((to_id, weight))
    
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
        
        while queue and len(results) < limit:  # Stop when we have enough
            current_id, current_depth, relevance = queue.pop(0)
            
            if current_id in visited or current_depth > depth:
                continue
            
            visited.add(current_id)
            
            if current_id in self.nodes:
                node = self.nodes[current_id]
                # Don't mutate access counts during read operations
                # This prevents issues with concurrent access and keeps reads pure
                
                # Score = importance * relevance * recency
                recency = self._recency_score(node.last_accessed)
                score = node.importance * relevance * recency
                
                if current_id != node_id:  # Don't include the query node itself
                    results.append((score, node))
                    if len(results) >= limit:  # Early exit once we have enough
                        break
                
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
        """BM25 keyword search with inverted index."""
        if not query.strip():
            return []
        
        # Rebuild BM25 index if dirty
        if self._index_dirty:
            self.bm25.build_index(self.nodes)
            self._index_dirty = False
        
        query_terms = query.lower().split()
        candidate_ids = self._get_candidates(query_terms)
        
        if not candidate_ids:
            return []
        
        matches: List[Tuple[float, MemoryNode]] = []
        
        # Score candidates with BM25
        for node_id in candidate_ids:
            node = self.nodes.get(node_id)
            if not node:
                continue
            
            bm25_score = self.bm25.score_document(node, query_terms)
            
            if bm25_score > 0:
                # Combine with metadata
                recency = self._recency_score(node.last_accessed)
                access_boost = min(node.access_count / 10, 2.0)
                
                final_score = (
                    bm25_score * 0.5 +
                    node.importance * 0.3 +
                    recency * 0.1 +
                    access_boost * 0.1
                )
                
                matches.append((final_score, node))
        
        matches.sort(reverse=True, key=lambda x: x[0])
        
        # Update access counts
        for _, node in matches[:limit]:
            node.access_count += 1
            node.last_accessed = time.time()
        
        return [node for _, node in matches[:limit]]
    
    def _get_candidates(self, query_terms: List[str]) -> Set[str]:
        """Get candidate node IDs from inverted index."""
        candidate_ids: Set[str] = set()
        
        # Try intersection first (AND) - more precise
        for term in query_terms:
            if term in self._term_index:
                if not candidate_ids:
                    candidate_ids = self._term_index[term].copy()
                else:
                    candidate_ids &= self._term_index[term]
        
        # Fall back to union (OR) - broader results
        if not candidate_ids:
            for term in query_terms:
                if term in self._term_index:
                    candidate_ids |= self._term_index[term]
        
        return candidate_ids
    
    def semantic_search(self, query: str, limit: int = 5) -> List[MemoryNode]:
        """Semantic similarity search using embeddings."""
        if not self._embeddings_enabled:
            return []
        
        try:
            results = self.embeddings.search(query, limit=limit * 2)
        except Exception as e:
            print(f"⚠️  Semantic search failed: {e}")
            return []
        
        matches: List[Tuple[float, MemoryNode]] = []
        for node_id, similarity in results:
            node = self.nodes.get(node_id)
            if not node:
                continue
            
            # Combine semantic score with metadata
            recency = self._recency_score(node.last_accessed)
            
            final_score = (
                similarity * 0.6 +
                node.importance * 0.2 +
                recency * 0.2
            )
            
            matches.append((final_score, node))
        
        matches.sort(reverse=True, key=lambda x: x[0])
        return [node for _, node in matches[:limit]]
    
    def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        keyword_weight: float = 0.4,
        semantic_weight: float = 0.6,
        use_graph_expansion: bool = True
    ) -> List[MemoryNode]:
        """
        Hybrid search combining BM25, embeddings, and graph traversal.
        
        Args:
            query: Search query
            limit: Max results to return
            keyword_weight: Weight for BM25 scores (0-1)
            semantic_weight: Weight for embedding scores (0-1)
            use_graph_expansion: Whether to expand via graph traversal
        """
        # Step 1: BM25 keyword search
        bm25_results = self._bm25_search_raw(query, top_k=limit * 2)
        
        # Step 2: Semantic search (if available)
        semantic_results = {}
        if self._embeddings_enabled:
            semantic_results = self._semantic_search_raw(query, top_k=limit * 2)
        
        # Step 3: Combine scores
        combined_scores = self._combine_scores(
            bm25_results,
            semantic_results,
            keyword_weight,
            semantic_weight
        )
        
        # Step 4: Graph expansion (optional)
        if use_graph_expansion and combined_scores:
            combined_scores = self._graph_expand(combined_scores, limit)
        
        # Step 5: Final ranking with metadata
        final_results = self._final_ranking(combined_scores, limit)
        
        return final_results
    
    def _bm25_search_raw(self, query: str, top_k: int) -> Dict[str, float]:
        """BM25 search returning raw scores."""
        if self._index_dirty:
            self.bm25.build_index(self.nodes)
            self._index_dirty = False
        
        query_terms = query.lower().split()
        scores = {}
        
        candidate_ids = self._get_candidates(query_terms)
        
        for node_id in candidate_ids:
            node = self.nodes.get(node_id)
            if node:
                score = self.bm25.score_document(node, query_terms)
                if score > 0:
                    scores[node_id] = score
        
        # Normalize to 0-1 range
        if scores:
            max_score = max(scores.values())
            if max_score > 0:
                scores = {nid: s / max_score for nid, s in scores.items()}
        
        return scores
    
    def _semantic_search_raw(self, query: str, top_k: int) -> Dict[str, float]:
        """Semantic search returning raw scores."""
        try:
            results = self.embeddings.search(query, limit=top_k)
            return {node_id: score for node_id, score in results}
        except Exception as e:
            print(f"⚠️  Semantic search failed: {e}")
            return {}
    
    def _combine_scores(
        self,
        bm25_scores: Dict[str, float],
        semantic_scores: Dict[str, float],
        keyword_weight: float,
        semantic_weight: float
    ) -> Dict[str, float]:
        """Combine BM25 and semantic scores with weighted sum."""
        # Normalize weights
        total_weight = keyword_weight + semantic_weight
        if total_weight == 0:
            return {}
        
        kw = keyword_weight / total_weight
        sw = semantic_weight / total_weight
        
        # Get all node IDs from both result sets
        all_node_ids = set(bm25_scores.keys()) | set(semantic_scores.keys())
        
        combined = {}
        for node_id in all_node_ids:
            bm25_score = bm25_scores.get(node_id, 0.0)
            semantic_score = semantic_scores.get(node_id, 0.0)
            
            # Weighted combination
            combined[node_id] = kw * bm25_score + sw * semantic_score
        
        return combined
    
    def _graph_expand(self, initial_scores: Dict[str, float], limit: int) -> Dict[str, float]:
        """Expand results using graph traversal."""
        # Get top N seeds for expansion
        sorted_nodes = sorted(
            initial_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        expanded_scores = initial_scores.copy()
        
        # Expand from top 3 seeds
        for node_id, score in sorted_nodes[:3]:
            if node_id not in self.nodes:
                continue
            
            # Get related nodes via graph traversal
            related = self.get_related(node_id, depth=2, limit=5)
            
            # Add related nodes with decayed score
            for related_node in related:
                if related_node.id not in expanded_scores:
                    # Decay score based on graph distance
                    decay_factor = 0.5  # Related nodes get half the score
                    expanded_scores[related_node.id] = score * decay_factor
        
        return expanded_scores
    
    def _final_ranking(self, combined_scores: Dict[str, float], limit: int) -> List[MemoryNode]:
        """Final ranking incorporating node metadata."""
        results: List[Tuple[float, MemoryNode]] = []
        
        for node_id, search_score in combined_scores.items():
            node = self.nodes.get(node_id)
            if not node:
                continue
            
            # Incorporate metadata signals
            recency = self._recency_score(node.last_accessed)
            access_boost = min(node.access_count / 10, 1.0)
            
            # Final score combines search relevance with metadata
            final_score = (
                search_score * 0.7 +      # Search relevance (BM25 + embeddings)
                node.importance * 0.15 +  # Static importance
                recency * 0.10 +          # Recency
                access_boost * 0.05       # Access frequency
            )
            
            results.append((final_score, node))
        
        # Sort and return top results
        results.sort(reverse=True, key=lambda x: x[0])
        
        # Update access counts
        for _, node in results[:limit]:
            node.access_count += 1
            node.last_accessed = time.time()
        
        return [node for _, node in results[:limit]]
    
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
        """Remove node from graph and clean up connections and indices."""
        if node_id not in self.nodes:
            return
        
        node = self.nodes[node_id]
        
        # Remove from inverted index
        terms = node.content.lower().split()
        for term in terms:
            if term in self._term_index:
                self._term_index[term].discard(node_id)
                # Remove term from index if no nodes contain it
                if not self._term_index[term]:
                    del self._term_index[term]
        
        # Remove embedding
        if self._embeddings_enabled:
            self.embeddings.remove_node(node_id)
        
        # Remove the node
        del self.nodes[node_id]
        
        # Mark index as dirty
        self._index_dirty = True
        
        # Remove references to this node from other nodes' connections
        for n in self.nodes.values():
            n.connections = [
                conn for conn in n.connections
                if (conn[0] if isinstance(conn, tuple) else conn) != node_id
            ]
    
    def clear(self):
        """Clear all nodes from the graph and reset indices."""
        self.nodes.clear()
        self._term_index.clear()
        self._idf_cache.clear()
        self._index_dirty = False
        
        # Clear embeddings
        if self._embeddings_enabled:
            self.embeddings.clear()
    
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
