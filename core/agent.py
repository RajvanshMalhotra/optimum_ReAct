"""Optimized autonomous agent with parallel execution and smart caching."""
import time
import json
import re
import asyncio
from typing import List, Optional
from models.agent import AgentThought, ToolResult
from memory.hybrid import HybridMemory
from core.llm import llm_client
from tools.registry import tool_registry
from config import AGENT_MAX_STEPS


class FastAgent:
    """Optimized autonomous agent."""
    
    def __init__(self, memory: HybridMemory):
        self.memory = memory
        self.llm = llm_client
        self._memory_cache = None  # Cache memory context
        self._last_recall_task = None
        
    async def _get_user_input(self, question: str) -> str:
        """Get input from user."""
        try:
            return input(f"\033[93m{question}\033[0m ")
        except (EOFError, KeyboardInterrupt):
            return "not specified"
    
    async def _execute_tools_parallel(self, tools_and_queries: List[tuple]) -> List[ToolResult]:
        """Execute multiple tools in parallel."""
        tasks = [self._execute_tool(tool, query) for tool, query in tools_and_queries]
        return await asyncio.gather(*tasks)
    
    async def _execute_tool(self, tool_name: str, query: str) -> ToolResult:
        """Execute a tool."""
        print(f"\033[94m🔧 {tool_name}\033[0m")
        
        try:
            if tool_name == "ask_user":
                answer = await self._get_user_input(query)
                self.memory.remember(
                    f"Q: {query} | A: {answer}",
                    mem_type="preference",
                    importance=0.9
                )
                return ToolResult(tool=tool_name, success=True, data=answer)
            
            elif tool_name == "remember":
                mem_id = self.memory.remember(query, mem_type="fact", importance=0.8)
                return ToolResult(tool=tool_name, success=True, data=f"Stored")
            
            elif tool_name == "recall":
                memories = self.memory.recall(query, limit=2)  # Reduced from 3
                result = "\n".join([f"- {m.content[:100]}" for m in memories])  # Truncate
                return ToolResult(tool=tool_name, success=True, data=result or "None")
            
            elif tool_registry.has_tool(tool_name):
                tool = tool_registry.get_tool(tool_name)
                result = await tool.execute(query)
                
                if result.success and tool_name == "web_search":
                    # Store truncated version
                    self.memory.remember(
                        f"Search: {query[:50]} → {str(result.data)[:150]}",
                        mem_type="fact",
                        importance=0.7
                    )
                
                return result
            
            else:
                return ToolResult(tool=tool_name, success=False, error="Tool unavailable")
                
        except Exception as e:
            return ToolResult(tool=tool_name, success=False, error=str(e))
    
    def _get_memory_context(self, task: str, force_refresh: bool = False) -> str:
        """Get memory context with caching."""
        # Cache memory context for same task
        if not force_refresh and self._last_recall_task == task and self._memory_cache:
            return self._memory_cache
        
        memories = self.memory.recall(task, limit=2)  # Reduced from 3
        context = "\n".join([f"- {m.content[:100]}" for m in memories]) if memories else "None"
        
        self._memory_cache = context
        self._last_recall_task = task
        return context
    
    def _parse_json_fast(self, response: str) -> Optional[dict]:
        """Fast JSON parsing with fallbacks."""
        # Try direct parse first (fastest)
        try:
            return json.loads(response)
        except:
            pass
        
        # Try regex extraction
        try:
            match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except:
            pass
        
        return None
    
    async def _think_fast(self, task: str, previous_thoughts: List[AgentThought]) -> AgentThought:
        """Optimized thinking with shorter prompts."""
        
        # Get cached memory context
        memory_context = self._get_memory_context(task)
        
        # Condensed thought context (only last 2 steps)
        recent_thoughts = previous_thoughts[-2:] if len(previous_thoughts) > 2 else previous_thoughts
        thought_context = "\n".join([
            f"{t.step}. {t.action}: {t.observation[:80] if t.observation else 'N/A'}"
            for t in recent_thoughts
        ])
        
        # Get tool descriptions (cached at registry level)
        tools = ["web_search", "ask_user", "remember", "recall"]
        tools_desc = "web_search (current data), ask_user (questions), remember (store), recall (retrieve)"
        
        # Shorter, more focused prompt
        prompt = f"""Task: {task}
Memory: {memory_context[:200]}
Steps: {thought_context if thought_context else 'First step'}

JSON (no markdown):
{{"reasoning": "brief thought", "action": "web_search|ask_user|remember|recall|final_answer", "query": "specific query", "complete": true/false}}"""

        response = await self.llm.simple_prompt(prompt, max_tokens=400)  # Reduced from 800
        
        # Fast JSON parse
        data = self._parse_json_fast(response)
        
        if data:
            thought = AgentThought(
                step=len(previous_thoughts) + 1,
                reasoning=data.get("reasoning", "")[:150],  # Truncate
                action=data.get("action", "final_answer"),
                query=data.get("query", ""),
                complete=data.get("complete", False)
            )
            
            # Store thought (async, non-blocking would be better but keeping simple)
            thought.memory_id = self.memory.remember(
                f"S{thought.step}: {thought.reasoning[:80]}",
                mem_type="thought",
                importance=0.5  # Lower importance for thoughts
            )
            
            return thought
        
        # Fallback
        return AgentThought(
            step=len(previous_thoughts) + 1,
            reasoning="Parsing failed",
            action="final_answer",
            complete=True
        )
    
    async def run(self, task: str, max_steps: int = AGENT_MAX_STEPS) -> str:
        """Run agent with optimizations."""
        print(f"\033[96m🤖 FastAgent running...\033[0m\n")
        
        thoughts: List[AgentThought] = []
        start_time = time.time()
        
        # Check if we've done this before (memory)
        similar_results = self.memory.recall(f"Task '{task[:50]}'", limit=1)
        if similar_results and "completed" in similar_results[0].content.lower():
            print(f"\033[93m💡 Found similar past task!\033[0m")
        
        for step in range(max_steps):
            print(f"\033[96m💭 Step {step + 1}\033[0m")
            
            # Parallel: Think while previous tool might be executing
            thought = await self._think_fast(task, thoughts)
            
            print(f"\033[2m{thought.reasoning[:100]}\033[0m")
            print(f"\033[92m→ {thought.action}\033[0m\n")
            
            # Execute action
            if thought.action == "final_answer":
                # Compile final answer with minimal context
                info = "\n".join([
                    f"{t.observation[:150]}" for t in thoughts[-3:] if t.observation
                ])
                
                final_prompt = f"""Task: {task}
Info: {info}

Concise final answer:"""

                final_answer = await self.llm.simple_prompt(final_prompt, max_tokens=1000)  # Reduced from 2000
                
                # Save session
                duration = time.time() - start_time
                self.memory.save_session(task, final_answer[:300], duration)  # Truncated
                
                return final_answer
            
            else:
                result = await self._execute_tool(thought.action, thought.query)
                thought.observation = f"{result.data[:200]}" if result.success else f"Error: {result.error}"
            
            # Link memory (only if both exist)
            if thought.memory_id and thoughts and thoughts[-1].memory_id:
                self.memory.relate(thoughts[-1].memory_id, thought.memory_id)
            
            thoughts.append(thought)
            
            if thought.complete:
                break
        
        # Max steps - quick compilation
        info = " | ".join([f"{t.observation[:100]}" for t in thoughts if t.observation])
        final_prompt = f"Task: {task}\nInfo: {info}\n\nBrief answer:"
        
        return await self.llm.simple_prompt(final_prompt, max_tokens=800)
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.llm.close()


# Backward compatibility
AutonomousAgent = FastAgent