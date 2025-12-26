
# """Memory models."""
# from typing import List, Dict, Any
# from pydantic import BaseModel, Field


# class MemoryNode(BaseModel):
#     """Node in the memory graph."""
#     id: str
#     type: str  # "thought", "fact", "preference", "result"
#     content: str
#     metadata: Dict[str, Any] = Field(default_factory=dict)
#     timestamp: float
#     connections: List[str] = Field(default_factory=list)
#     importance: float = 0.5
#     access_count: int = 0
    
#     class Config:
#         arbitrary_types_allowed = True# define base memory abstraction (2025-11-12)
# # add read/write memory contracts (2025-11-18)
# # add basic validation checks (2025-11-24)
# # document memory lifecycle (2025-12-01)
# # tighten memory interface (2025-12-06)
# # cleanup unused imports (2025-12-12)



"""Memory models with enhanced fields."""
from typing import List, Dict, Any, Union, Tuple
from pydantic import BaseModel, Field
import time


class MemoryNode(BaseModel):
    """Node in the memory graph with temporal and access tracking."""
    id: str
    type: str  # "thought", "fact", "preference", "result", "tool_output"
    content: str  # Full content, no truncation at storage
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float  # Creation time
    last_accessed: float = Field(default_factory=lambda: time.time())  # Last access time
    connections: List[Union[str, Tuple[str, float]]] = Field(default_factory=list)  # [(node_id, weight), ...] or ["node_id", ...]
    importance: float = 0.5  # 0-1 score
    access_count: int = 0
    
    class Config:
        arbitrary_types_allowed = True