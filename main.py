# """Main entry point for the autonomous agent."""
# import asyncio
# import time
# import sys
# from pathlib import Path

# # Add project root to path
# sys.path.insert(0, str(Path(__file__).parent))

# from config import MEMORY_DB_PATH
# from memory.hybrid import HybridMemory
# from core.agent import AutonomousAgent
# from tools.registry import tool_registry
# from ui.console import (
#     print_intro,
#     print_result,
#     print_success,
#     print_warning,
#     print_error,
#     print_info,
#     print_dim,
#     get_input,
#     console
# )

# # Import and register tools
# try:
#     from tools.search_tool import SearchTool
    
#     # Create async wrapper for SearchTool
#     class AsyncSearchTool:
#         def __init__(self):
#             self.search_tool = SearchTool()
        
#         @property
#         def name(self):
#             return "web_search"
        
#         @property
#         def description(self):
#             return "Search the internet for current information, prices, news, facts"
        
#         async def execute(self, query: str):
#             from models.agent import ToolResult
#             try:
#                 result = self.search_tool.run(query)
#                 return ToolResult(tool="web_search", success=True, data=result)
#             except Exception as e:
#                 return ToolResult(tool="web_search", success=False, error=str(e))
    
#     tool_registry.register(AsyncSearchTool())
#     SEARCH_AVAILABLE = True
# except ImportError:
#     SEARCH_AVAILABLE = False


# async def main():
#     """Main entry point."""
#     try:
#         print_intro()
        
#         # Get inputs
#         theme = get_input("Theme [hacker/matrix/fire/minimal]:", "hacker")
#         if theme not in ["hacker", "matrix", "fire", "minimal"]:
#             theme = "hacker"
        
#         task = get_input("\n🎯 TASK:\n>")
        
#         if not task:
#             print_error("No task provided.")
#             return

#         # Initialize memory
#         memory = HybridMemory(str(MEMORY_DB_PATH))
#         print_dim(f"\n{memory.get_context_summary()}\n")
        
#         # Show available tools
#         if SEARCH_AVAILABLE:
#             print_success("Tavily search available")
#         else:
#             print_warning("Tavily search unavailable")

#         # Create and run agent
#         agent = AutonomousAgent(memory=memory)
        
#         print_info("Agent running with full autonomy...\n")
#         start = time.perf_counter()
        
#         result = await agent.run(task)
#         elapsed = time.perf_counter() - start

#         # Display result
#         print_result(result, theme)
#         console.print(
#             f"\n⏱  {elapsed:.2f}s | {memory.get_context_summary()}\n",
#             style="bold green"
#         )

#     except KeyboardInterrupt:
#         print_warning("\nInterrupted by user.")
#     except Exception as e:
#         print_error(f"Error: {e}")
#         import traceback
#         traceback.print_exc()


# if __name__ == "__main__":
#     asyncio.run(main())

"""Main entry point for the autonomous agent."""
import asyncio
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import MEMORY_DB_PATH
from memory.hybrid import HybridMemory
from core.agent import AutonomousAgent
from tools.registry import tool_registry
from ui.console import (
    print_intro,
    print_result,
    print_success,
    print_warning,
    print_error,
    print_info,
    print_dim,
    get_input,
    console
)

# Import and register tools
try:
    from tools.search_tool import SearchTool
    
    # Create async wrapper for SearchTool
    class AsyncSearchTool:
        def __init__(self):
            try:
                self.search_tool = SearchTool()
                print("✅ SearchTool initialized successfully")
            except Exception as e:
                print(f"❌ SearchTool init failed: {e}")
                raise
        
        @property
        def name(self):
            return "web_search"
        
        @property
        def description(self):
            return "Search the internet for current information, prices, news, facts"
        
        async def execute(self, query: str):
            from models.agent import ToolResult
            try:
                print(f"🔍 Executing search for: {query[:50]}...")
                result = self.search_tool.run(query)
                print(f"✅ Search completed, got {len(result)} chars")
                return ToolResult(tool="web_search", success=True, data=result)
            except Exception as e:
                print(f"❌ Search execution failed: {e}")
                import traceback
                traceback.print_exc()
                return ToolResult(tool="web_search", success=False, error=str(e))
    
    tool_registry.register(AsyncSearchTool())
    SEARCH_AVAILABLE = True
    print("✅ Web search tool registered")
except ImportError as e:
    print(f"❌ Cannot import SearchTool: {e}")
    SEARCH_AVAILABLE = False
except Exception as e:
    print(f"❌ Search tool registration failed: {e}")
    import traceback
    traceback.print_exc()
    SEARCH_AVAILABLE = False


async def main():
    """Main entry point."""
    try:
        print_intro()
        
        # Get inputs
        theme = get_input("Theme [hacker/matrix/fire/minimal]:", "hacker")
        if theme not in ["hacker", "matrix", "fire", "minimal"]:
            theme = "hacker"
        
        task = get_input("\n🎯 TASK:\n>")
        
        if not task:
            print_error("No task provided.")
            return

        # Initialize memory
        memory = HybridMemory(str(MEMORY_DB_PATH))
        print_dim(f"\n{memory.get_context_summary()}\n")
        
        # Show available tools
        if SEARCH_AVAILABLE:
            print_success("Tavily search available")
        else:
            print_warning("Tavily search unavailable")

        # Create and run agent
        agent = AutonomousAgent(memory=memory)
        
        print_info("Agent running with full autonomy...\n")
        start = time.perf_counter()
        
        result = await agent.run(task)
        elapsed = time.perf_counter() - start

        # Display result
        print_result(result, theme)
        console.print(
            f"\n⏱  {elapsed:.2f}s | {memory.get_context_summary()}\n",
            style="bold green"
        )

    except KeyboardInterrupt:
        print_warning("\nInterrupted by user.")
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())