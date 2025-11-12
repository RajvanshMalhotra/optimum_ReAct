
"""Memory models."""
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class MemoryNode(BaseModel):
    """Node in the memory graph."""
    id: str
    type: str  # "thought", "fact", "preference", "result"
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float
    connections: List[str] = Field(default_factory=list)
    importance: float = 0.5
    access_count: int = 0
    
    class Config:
        arbitrary_types_allowed = True# define base memory abstraction (2025-11-12)
