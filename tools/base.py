"""Base tool interface."""
from abc import ABC, abstractmethod
from typing import Any
from models.agent import ToolResult


class BaseTool(ABC):
    """Base class for all tools."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for AI to understand when to use it."""
        pass
    
    @abstractmethod
    async def execute(self, query: str) -> ToolResult:
        """Execute the tool with given query."""
        pass