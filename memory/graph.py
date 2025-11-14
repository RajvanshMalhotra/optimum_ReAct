"""In-memory graph for fast memory access."""
from typing import Dict, List
from models.memory import MemoryNode
from config import MEMORY_MAX_GRAPH_NODES


class MemoryGraph:
    """In-memory graph for fast access."""
    
    def __init__(self, max_nodes: int = MEMORY_MAX_GRAPH_NODES):
        self.nodes: Dict[str, MemoryNode] = {}
        self.max_nodes = max_nodes
        
    def add_node(self, node: MemoryNode):
        """Add node to graph."""
        self.nodes[node.id] = node
        
    def connect(self, from_id: str, to_id: str):
        """Create edge between nodes."""
        if from_id in self.nodes and to_id in self.nodes:
            if to_id not in self.nodes[from_id].connections:
                self.nodes[from_id].connections.append(to_id)
    
    def get_node(self, node_id: str) -> MemoryNode | None:
        """Get single node by ID."""
        return self.nodes.get(node_id)
    
    def get_related(self, node_id: str, depth: int = 2) -> List[MemoryNode]:
        """Get related nodes up to depth."""
        visited = set()
        result = []
        
        def traverse(nid: str, d: int):
            if d > depth or nid in visited:
                return
            visited.add(nid)
            
            if nid in self.nodes:
                node = self.nodes[nid]
                node.access_count += 1
                result.append(node)
                
                for conn in node.connections:
                    traverse(conn, d + 1)
        
        traverse(node_id, 0)
        return result
    
    def search(self, query: str, limit: int = 5) -> List[MemoryNode]:
        """Semantic search in graph (keyword matching)."""
        query_lower = query.lower()
        matches = []
        
        for node in self.nodes.values():
            content_lower = node.content.lower()
            score = sum(1 for word in query_lower.split() if word in content_lower)
            if score > 0:
                matches.append((score, node))
        
        matches.sort(reverse=True, key=lambda x: x[0])
        return [node for _, node in matches[:limit]]
    
    def should_persist(self) -> bool:
        """Check if graph is too large."""
        return len(self.nodes) >= self.max_nodes
    
    def get_least_important(self, count: int = 20) -> List[str]:
        """Get least important nodes to persist."""
        sorted_nodes = sorted(
            self.nodes.values(),
            key=lambda n: (n.importance * 0.7 + (n.access_count / 10) * 0.3)
        )
        return [n.id for n in sorted_nodes[:count]]
    
    def remove_node(self, node_id: str):
        """Remove node from graph."""
        if node_id in self.nodes:
            del self.nodes[node_id]
    
    def size(self) -> int:
        """Get current graph size."""
        return len(self.nodes)# add basic graph memory structure (2025-11-09)
# add node linking logic (2025-11-14)
