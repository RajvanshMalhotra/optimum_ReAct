"""
EZ Agent - Simple interface for using your ReAct agent.

Usage:
    from ez_agent import EZAgent
    
    agent = EZAgent()
    result = agent.ask("What is 15 * 23?")
    print(result)
"""

import asyncio
from pathlib import Path
from memory.hybrid import HybridMemory
from core.agent import FastAgent


class EZAgent:
    """Easy-to-use agent interface."""
    
    def __init__(self, memory_path: str = "agent_memory.db"):
        """
        Initialize the agent.
        
        Args:
            memory_path: Path to SQLite database for persistent memory
        """
        self.memory = HybridMemory(memory_path)
        self.agent = FastAgent(self.memory)
        
    def ask(self, task: str, max_steps: int = 10) -> str:
        """
        Ask the agent to perform a task (synchronous).
        
        Args:
            task: The task or question for the agent
            max_steps: Maximum reasoning steps (default: 10)
            
        Returns:
            Agent's response as a string
            
        Example:
            >>> agent = EZAgent()
            >>> result = agent.ask("What is the capital of France?")
            >>> print(result)
        """
        return asyncio.run(self._async_ask(task, max_steps))
    
    async def _async_ask(self, task: str, max_steps: int) -> str:
        """Internal async implementation."""
        return await self.agent.run(task, max_steps=max_steps)
    
    async def ask_async(self, task: str, max_steps: int = 10) -> str:
        """
        Ask the agent to perform a task (async).
        
        Args:
            task: The task or question for the agent
            max_steps: Maximum reasoning steps (default: 10)
            
        Returns:
            Agent's response as a string
            
        Example:
            >>> agent = EZAgent()
            >>> result = await agent.ask_async("What is 15 * 23?")
            >>> print(result)
        """
        return await self.agent.run(task, max_steps=max_steps)
    
    def remember(self, fact: str, importance: float = 0.8) -> str:
        """
        Explicitly store a fact in memory.
        
        Args:
            fact: The information to remember
            importance: How important this fact is (0-1, default: 0.8)
            
        Returns:
            Memory ID
            
        Example:
            >>> agent = EZAgent()
            >>> agent.remember("My favorite color is blue")
        """
        return self.memory.remember(
            fact, 
            mem_type="fact", 
            importance=importance
        )
    
    def recall(self, query: str, limit: int = 5) -> list:
        """
        Retrieve memories matching a query.
        
        Args:
            query: Search query
            limit: Maximum number of memories to return (default: 5)
            
        Returns:
            List of memory contents as strings
            
        Example:
            >>> agent = EZAgent()
            >>> memories = agent.recall("favorite color")
            >>> for mem in memories:
            ...     print(mem)
        """
        memories = self.memory.recall(query, limit=limit)
        return [mem.content for mem in memories]
    
    def stats(self) -> dict:
        """
        Get agent memory statistics.
        
        Returns:
            Dictionary with memory stats
            
        Example:
            >>> agent = EZAgent()
            >>> stats = agent.stats()
            >>> print(f"Total memories: {stats['total_memories']}")
        """
        return self.memory.get_statistics()
    
    def clear_session(self):
        """
        Clear current session (keeps persistent storage).
        
        Creates a new memory session while keeping database intact.
        """
        # Just create new session - old memories stay in DB
        self.memory = HybridMemory(self.memory.store.db_path)
        self.agent = FastAgent(self.memory)
    
    async def cleanup(self):
        """Cleanup resources (call when done)."""
        await self.agent.cleanup()


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_basic():
    """Example 1: Basic question answering."""
    print("\n" + "="*60)
    print("Example 1: Basic Question")
    print("="*60)
    
    agent = EZAgent()
    result = agent.ask("What is 25 * 17? Show your work.")
    print(f"Answer: {result}")


def example_memory():
    """Example 2: Using memory."""
    print("\n" + "="*60)
    print("Example 2: Memory Usage")
    print("="*60)
    
    agent = EZAgent()
    
    # Store facts
    agent.remember("My name is Alex")
    agent.remember("I work as a data scientist")
    agent.remember("My favorite language is Python")
    
    # Ask agent to recall
    result = agent.ask("What do you know about me?")
    print(f"Agent recalls: {result}")
    
    # Query memory directly
    print("\nDirect memory query:")
    memories = agent.recall("Python")
    for mem in memories:
        print(f"  - {mem}")


def example_multi_step():
    """Example 3: Multi-step reasoning."""
    print("\n" + "="*60)
    print("Example 3: Multi-Step Reasoning")
    print("="*60)
    
    agent = EZAgent()
    
    task = """
    Sarah has 3 times as many apples as Tom.
    Tom has 5 more apples than Lisa.
    Lisa has 7 apples.
    How many apples does Sarah have?
    """
    
    result = agent.ask(task, max_steps=8)
    print(f"Solution: {result}")


def example_conversation():
    """Example 4: Multi-turn conversation."""
    print("\n" + "="*60)
    print("Example 4: Conversation")
    print("="*60)
    
    agent = EZAgent()
    
    # Turn 1
    response1 = agent.ask("Remember that I like Italian food and I'm vegetarian")
    print(f"Turn 1: {response1}")
    
    # Turn 2
    response2 = agent.ask("Suggest a restaurant for me")
    print(f"Turn 2: {response2}")


def example_web_search():
    """Example 5: Using web search (requires TAVILY_API_KEY)."""
    print("\n" + "="*60)
    print("Example 5: Web Search")
    print("="*60)
    
    agent = EZAgent()
    
    # Note: This requires TAVILY_API_KEY environment variable
    result = agent.ask("What is the current price of Bitcoin?", max_steps=5)
    print(f"Search result: {result}")


def example_async():
    """Example 6: Async usage."""
    print("\n" + "="*60)
    print("Example 6: Async Usage")
    print("="*60)
    
    async def async_main():
        agent = EZAgent()
        
        # Multiple concurrent queries
        tasks = [
            agent.ask_async("What is 10 + 20?"),
            agent.ask_async("What is 5 * 8?"),
            agent.ask_async("What is 100 / 4?")
        ]
        
        results = await asyncio.gather(*tasks)
        
        for i, result in enumerate(results, 1):
            print(f"Query {i}: {result}")
        
        await agent.cleanup()
    
    asyncio.run(async_main())


def example_stats():
    """Example 7: Memory statistics."""
    print("\n" + "="*60)
    print("Example 7: Memory Stats")
    print("="*60)
    
    agent = EZAgent()
    
    # Do some work
    agent.remember("Test fact 1")
    agent.remember("Test fact 2")
    agent.ask("What is 5 + 5?")
    
    # Get stats
    stats = agent.stats()
    print(f"Session ID: {stats['session_id']}")
    print(f"Memories created this session: {stats['session_memory_count']}")
    print(f"Total memories in graph: {stats['graph']['total_nodes']}")
    print(f"Total memories in database: {stats['store']['total_memories']}")


# ============================================================================
# ONE-LINERS FOR QUICK TASKS
# ============================================================================

def quick_examples():
    """Quick one-liner examples."""
    print("\n" + "="*60)
    print("One-Liner Examples")
    print("="*60)
    
    # Quick question
    print(EZAgent().ask("What is the capital of France?"))
    
    # Quick calculation
    print(EZAgent().ask("Calculate 15% tip on $45.50"))
    
    # Quick memory
    agent = EZAgent()
    agent.remember("Python was created in 1991")
    print(agent.ask("When was Python created?"))


# ============================================================================
# MAIN DEMO
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("EZ AGENT DEMO")
    print("="*60)
    
    # Run examples (comment out the ones you don't want)
    example_basic()
    example_memory()
    example_multi_step()
    example_conversation()
    # example_web_search()  # Requires TAVILY_API_KEY
    # example_async()
    example_stats()
    # quick_examples()
    
    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60)
    print("\nTo use in your own code:")
    print("  from ez_agent import EZAgent")
    print("  agent = EZAgent()")
    print('  result = agent.ask("Your question here")')
    print("="*60)
