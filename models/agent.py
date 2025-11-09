"""Agent models."""
from typing import Optional, Any
from pydantic import BaseModel


class ToolResult(BaseModel):
    """Result from tool execution."""
    tool: str
    success: bool
    data: Any
    error: Optional[str] = None


class AgentThought(BaseModel):
    """Agent's reasoning step."""
    step: int
    reasoning: str
    action: str
    query: str = ""
    observation: Optional[str] = None
    complete: bool = False
    memory_id: Optional[str] = None