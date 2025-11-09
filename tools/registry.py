"""Tool registry for dynamic tool discovery."""
from typing import Dict, List
from tools.base import BaseTool


class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool):
        """Register a new tool."""
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> BaseTool | None:
        """Get tool by name."""
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())
    
    def get_tool_descriptions(self) -> Dict[str, str]:
        """Get all tool descriptions for prompting."""
        return {tool.name: tool.description for tool in self._tools.values()}
    
    def has_tool(self, name: str) -> bool:
        """Check if tool exists."""
        return name in self._tools


# Global registry
tool_registry = ToolRegistry()