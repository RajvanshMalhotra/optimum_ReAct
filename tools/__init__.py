# from .base import BaseTool
# from .registry import tool_registry, ToolRegistry

# __all__ = ['BaseTool', 'tool_registry', 'ToolRegistry']# expose tool interfaces (2025-11-16)

"""
Tools module - auto-registers all available tools.
Just import from tools and everything is ready.
"""
from .base import BaseTool
from .registry import tool_registry, ToolRegistry

# Auto-register web search if available
try:
    from .search_tool import SearchTool
    from models.agent import ToolResult
    
    class AsyncSearchTool(BaseTool):
        """Async wrapper for web search."""
        
        def __init__(self):
            self.search_tool = SearchTool()
        
        @property
        def name(self) -> str:
            return "web_search"
        
        @property
        def description(self) -> str:
            return "Search the internet for current information, news, prices, facts"
        
        async def execute(self, query: str) -> ToolResult:
            try:
                result = self.search_tool.run(query)
                return ToolResult(tool="web_search", success=True, data=result)
            except Exception as e:
                return ToolResult(tool="web_search", success=False, data=None, error=str(e))
    
    # Register it
    tool_registry.register(AsyncSearchTool())
    SEARCH_AVAILABLE = True
    
except ImportError as e:
    # tavily-python not installed
    SEARCH_AVAILABLE = False
except ValueError as e:
    # TAVILY_API_KEY not set
    SEARCH_AVAILABLE = False
except Exception as e:
    # Other error
    SEARCH_AVAILABLE = False

# Export what's needed
__all__ = ['BaseTool', 'tool_registry', 'ToolRegistry', 'SEARCH_AVAILABLE']