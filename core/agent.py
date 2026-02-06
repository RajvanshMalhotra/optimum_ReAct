# # """Optimized autonomous agent with parallel execution and smart caching."""
# # import time
# # import json
# # import re
# # import asyncio
# # from typing import List, Optional
# # from models.agent import AgentThought, ToolResult
# # from memory.hybrid import HybridMemory
# # from core.llm import llm_client
# # from tools.registry import tool_registry
# # from config import AGENT_MAX_STEPS


# # class FastAgent:
# #     """Optimized autonomous agent."""
    
# #     def __init__(self, memory: HybridMemory):
# #         self.memory = memory
# #         self.llm = llm_client
# #         self._memory_cache = None  # Cache memory context
# #         self._last_recall_task = None
        
# #     async def _get_user_input(self, question: str) -> str:
# #         """Get input from user."""
# #         try:
# #             return input(f"\033[93m{question}\033[0m ")
# #         except (EOFError, KeyboardInterrupt):
# #             return "not specified"
    
# #     async def _execute_tools_parallel(self, tools_and_queries: List[tuple]) -> List[ToolResult]:
# #         """Execute multiple tools in parallel."""
# #         tasks = [self._execute_tool(tool, query) for tool, query in tools_and_queries]
# #         return await asyncio.gather(*tasks)
    
# #     async def _execute_tool(self, tool_name: str, query: str) -> ToolResult:
# #         """Execute a tool."""
# #         print(f"\033[94m🔧 {tool_name}\033[0m")
        
# #         try:
# #             if tool_name == "ask_user":
# #                 answer = await self._get_user_input(query)
# #                 self.memory.remember(
# #                     f"Q: {query} | A: {answer}",
# #                     mem_type="preference",
# #                     importance=0.9
# #                 )
# #                 return ToolResult(tool=tool_name, success=True, data=answer)
            
# #             elif tool_name == "remember":
# #                 mem_id = self.memory.remember(query, mem_type="fact", importance=0.8)
# #                 return ToolResult(tool=tool_name, success=True, data=f"Stored")
            
# #             elif tool_name == "recall":
# #                 memories = self.memory.recall(query, limit=2)  # Reduced from 3
# #                 result = "\n".join([f"- {m.content[:100]}" for m in memories])  # Truncate
# #                 return ToolResult(tool=tool_name, success=True, data=result or "None")
            
# #             elif tool_registry.has_tool(tool_name):
# #                 tool = tool_registry.get_tool(tool_name)
# #                 result = await tool.execute(query)
                
# #                 if result.success and tool_name == "web_search":
# #                     # Store truncated version
# #                     self.memory.remember(
# #                         f"Search: {query[:50]} → {str(result.data)[:150]}",
# #                         mem_type="fact",
# #                         importance=0.7
# #                     )
                
# #                 return result
            
# #             else:
# #                 return ToolResult(tool=tool_name, success=False, error="Tool unavailable")
                
# #         except Exception as e:
# #             return ToolResult(tool=tool_name, success=False, error=str(e))
    
# #     def _get_memory_context(self, task: str, force_refresh: bool = False) -> str:
# #         """Get memory context with caching."""
# #         # Cache memory context for same task
# #         if not force_refresh and self._last_recall_task == task and self._memory_cache:
# #             return self._memory_cache
        
# #         memories = self.memory.recall(task, limit=2)  # Reduced from 3
# #         context = "\n".join([f"- {m.content[:100]}" for m in memories]) if memories else "None"
        
# #         self._memory_cache = context
# #         self._last_recall_task = task
# #         return context
    
# #     def _parse_json_fast(self, response: str) -> Optional[dict]:
# #         """Fast JSON parsing with fallbacks."""
# #         # Try direct parse first (fastest)
# #         try:
# #             return json.loads(response)
# #         except:
# #             pass
        
# #         # Try regex extraction
# #         try:
# #             match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
# #             if match:
# #                 return json.loads(match.group(0))
# #         except:
# #             pass
        
# #         return None
    
# #     async def _think_fast(self, task: str, previous_thoughts: List[AgentThought]) -> AgentThought:
# #         """Optimized thinking with shorter prompts."""
        
# #         # Get cached memory context
# #         memory_context = self._get_memory_context(task)
        
# #         # Condensed thought context (only last 2 steps)
# #         recent_thoughts = previous_thoughts[-2:] if len(previous_thoughts) > 2 else previous_thoughts
# #         thought_context = "\n".join([
# #             f"{t.step}. {t.action}: {t.observation[:80] if t.observation else 'N/A'}"
# #             for t in recent_thoughts
# #         ])
        
# #         # Get tool descriptions (cached at registry level)
# #         tools = ["web_search", "ask_user", "remember", "recall"]
# #         tools_desc = "web_search (current data), ask_user (questions), remember (store), recall (retrieve)"
        
# #         # Shorter, more focused prompt
# #         prompt = f"""Task: {task}
# # Memory: {memory_context[:200]}
# # Steps: {thought_context if thought_context else 'First step'}

# # JSON (no markdown):
# # {{"reasoning": "brief thought", "action": "web_search|ask_user|remember|recall|final_answer", "query": "specific query", "complete": true/false}}"""

# #         response = await self.llm.simple_prompt(prompt, max_tokens=400)  # Reduced from 800
        
# #         # Fast JSON parse
# #         data = self._parse_json_fast(response)
        
# #         if data:
# #             thought = AgentThought(
# #                 step=len(previous_thoughts) + 1,
# #                 reasoning=data.get("reasoning", "")[:150],  # Truncate
# #                 action=data.get("action", "final_answer"),
# #                 query=data.get("query", ""),
# #                 complete=data.get("complete", False)
# #             )
            
# #             # Store thought (async, non-blocking would be better but keeping simple)
# #             thought.memory_id = self.memory.remember(
# #                 f"S{thought.step}: {thought.reasoning[:80]}",
# #                 mem_type="thought",
# #                 importance=0.5  # Lower importance for thoughts
# #             )
            
# #             return thought
        
# #         # Fallback
# #         return AgentThought(
# #             step=len(previous_thoughts) + 1,
# #             reasoning="Parsing failed",
# #             action="final_answer",
# #             complete=True
# #         )
    
# #     async def run(self, task: str, max_steps: int = AGENT_MAX_STEPS) -> str:
# #         """Run agent with optimizations."""
# #         print(f"\033[96m🤖 FastAgent running...\033[0m\n")
        
# #         thoughts: List[AgentThought] = []
# #         start_time = time.time()
        
# #         # Check if we've done this before (memory)
# #         similar_results = self.memory.recall(f"Task '{task[:50]}'", limit=1)
# #         if similar_results and "completed" in similar_results[0].content.lower():
# #             print(f"\033[93m💡 Found similar past task!\033[0m")
        
# #         for step in range(max_steps):
# #             print(f"\033[96m💭 Step {step + 1}\033[0m")
            
# #             # Parallel: Think while previous tool might be executing
# #             thought = await self._think_fast(task, thoughts)
            
# #             print(f"\033[2m{thought.reasoning[:100]}\033[0m")
# #             print(f"\033[92m→ {thought.action}\033[0m\n")
            
# #             # Execute action
# #             if thought.action == "final_answer":
# #                 # Compile final answer with minimal context
# #                 info = "\n".join([
# #                     f"{t.observation[:150]}" for t in thoughts[-3:] if t.observation
# #                 ])
                
# #                 final_prompt = f"""Task: {task}
# # Info: {info}

# # Concise final answer:"""

# #                 final_answer = await self.llm.simple_prompt(final_prompt, max_tokens=1000)  # Reduced from 2000
                
# #                 # Save session
# #                 duration = time.time() - start_time
# #                 self.memory.save_session(task, final_answer[:300], duration)  # Truncated
                
# #                 return final_answer
            
# #             else:
# #                 result = await self._execute_tool(thought.action, thought.query)
# #                 thought.observation = f"{result.data[:200]}" if result.success else f"Error: {result.error}"
            
# #             # Link memory (only if both exist)
# #             if thought.memory_id and thoughts and thoughts[-1].memory_id:
# #                 self.memory.relate(thoughts[-1].memory_id, thought.memory_id)
            
# #             thoughts.append(thought)
            
# #             if thought.complete:
# #                 break
        
# #         # Max steps - quick compilation
# #         info = " | ".join([f"{t.observation[:100]}" for t in thoughts if t.observation])
# #         final_prompt = f"Task: {task}\nInfo: {info}\n\nBrief answer:"
        
# #         return await self.llm.simple_prompt(final_prompt, max_tokens=800)
    
# #     async def cleanup(self):
# #         """Cleanup resources."""
# #         await self.llm.close()


# # Backward compatibility
# # AutonomousAgent = FastAgent

# # """Agent integration with fixed memory system - Key changes only."""
# # import time
# # from typing import List
# # from models.agent import AgentThought, ToolResult
# # from memory.hybrid import HybridMemory
# # from core.llm import llm_client
# # from tools.registry import tool_registry
# # from config import AGENT_MAX_STEPS


# # class FastAgent:
# #     """Optimized autonomous agent with proper memory utilization."""
    
# #     def __init__(self, memory: HybridMemory):
# #         self.memory = memory
# #         self.llm = llm_client
        
# #     async def _get_user_input(self, question: str) -> str:
# #         """Get input from user."""
# #         try:
# #             return input(f"\033[93m{question}\033[0m ")
# #         except (EOFError, KeyboardInterrupt):
# #             return "not specified"
    
# #     async def _execute_tool(self, tool_name: str, query: str) -> ToolResult:
# #         """Execute a tool."""
# #         print(f"\033[94m🔧 {tool_name}\033[0m")
        
# #         try:
# #             if tool_name == "ask_user":
# #                 answer = await self._get_user_input(query)
# #                 self.memory.remember(
# #                     f"Q: {query} | A: {answer}",
# #                     mem_type="preference",
# #                     importance=0.9
# #                 )
# #                 return ToolResult(tool=tool_name, success=True, data=answer)
            
# #             elif tool_name == "remember":
# #                 mem_id = self.memory.remember(query, mem_type="fact", importance=0.8)
# #                 return ToolResult(tool=tool_name, success=True, data=f"Stored as {mem_id}")
            
# #             elif tool_name == "recall":
# #                 # Use new recall_context method with token limit
# #                 result = self.memory.recall_context(query, max_tokens=500)
# #                 return ToolResult(tool=tool_name, success=True, data=result)
            
# #             elif tool_registry.has_tool(tool_name):
# #                 tool = tool_registry.get_tool(tool_name)
# #                 result = await tool.execute(query)
                
# #                 # Store search results with full content
# #                 if result.success and tool_name == "web_search":
# #                     self.memory.remember(
# #                         f"Search '{query}': {str(result.data)}",
# #                         mem_type="tool_output",
# #                         importance=0.7
# #                     )
                
# #                 return result
            
# #             else:
# #                 return ToolResult(tool=tool_name, success=False, error="Tool unavailable")
                
# #         except Exception as e:
# #             return ToolResult(tool=tool_name, success=False, error=str(e))
    
# #     async def _think_fast(self, task: str, previous_thoughts: List[AgentThought]) -> AgentThought:
# #         """Optimized thinking with memory context."""
        
# #         # Get relevant memory context (uses graph + FTS)
# #         memory_context = self.memory.recall_context(task, max_tokens=400)
        
# #         # Condensed thought context (only last 2 steps)
# #         recent_thoughts = previous_thoughts[-2:] if len(previous_thoughts) > 2 else previous_thoughts
# #         thought_context = "\n".join([
# #             f"{t.step}. {t.action}: {t.observation[:100] if t.observation else 'N/A'}"
# #             for t in recent_thoughts
# #         ])
        
# #         # Shorter, more focused prompt
# #         prompt = f"""Task: {task}
# # Memory: {memory_context[:300]}
# # Steps: {thought_context if thought_context else 'First step'}

# # JSON (no markdown):
# # {{"reasoning": "brief thought", "action": "web_search|ask_user|remember|recall|final_answer", "query": "specific query", "complete": true/false}}"""

# #         response = await self.llm.simple_prompt(prompt, max_tokens=400)
        
# #         # Parse JSON
# #         import json
# #         import re
# #         try:
# #             data = json.loads(response)
# #         except:
# #             match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
# #             if match:
# #                 data = json.loads(match.group(0))
# #             else:
# #                 data = {}
        
# #         if data:
# #             thought = AgentThought(
# #                 step=len(previous_thoughts) + 1,
# #                 reasoning=data.get("reasoning", ""),
# #                 action=data.get("action", "final_answer"),
# #                 query=data.get("query", ""),
# #                 complete=data.get("complete", False)
# #             )
            
# #             # Store thought with full content
# #             thought.memory_id = self.memory.remember(
# #                 f"Step {thought.step}: {thought.reasoning} → {thought.action}",
# #                 mem_type="thought",
# #                 importance=0.5
# #             )
            
# #             return thought
        
# #         # Fallback
# #         return AgentThought(
# #             step=len(previous_thoughts) + 1,
# #             reasoning="Parsing failed",
# #             action="final_answer",
# #             complete=True
# #         )
    
# #     async def run(self, task: str, max_steps: int = AGENT_MAX_STEPS) -> str:
# #         """Run agent with enhanced memory utilization."""
# #         print(f"\033[96m🤖 FastAgent running...\033[0m\n")
        
# #         # Load context from similar past sessions
# #         self.memory.load_past_session_context(task)
        
# #         thoughts: List[AgentThought] = []
# #         start_time = time.time()
        
# #         for step in range(max_steps):
# #             print(f"\033[96m💭 Step {step + 1}\033[0m")
            
# #             thought = await self._think_fast(task, thoughts)
            
# #             print(f"\033[2m{thought.reasoning[:150]}\033[0m")
# #             print(f"\033[92m→ {thought.action}\033[0m\n")
            
# #             # Execute action
# #             if thought.action == "final_answer":
# #                 # Get relevant memories for final answer
# #                 memory_context = self.memory.recall_context(task, max_tokens=800)
                
# #                 final_prompt = f"""Task: {task}
# # Relevant Information:
# # {memory_context}

# # Provide a concise, comprehensive final answer:"""

# #                 final_answer = await self.llm.simple_prompt(final_prompt, max_tokens=1000)
                
# #                 # Save session with full context
# #                 duration = time.time() - start_time
# #                 self.memory.save_session(task, final_answer, duration)
                
# #                 return final_answer
            
# #             else:
# #                 result = await self._execute_tool(thought.action, thought.query)
# #                 thought.observation = str(result.data) if result.success else f"Error: {result.error}"
            
# #             # Create weighted connection between sequential thoughts
# #             if thought.memory_id and thoughts and thoughts[-1].memory_id:
# #                 # Higher weight for direct sequential connections
# #                 self.memory.relate(thoughts[-1].memory_id, thought.memory_id, weight=1.0)
            
# #             thoughts.append(thought)
            
# #             if thought.complete:
# #                 break
        
# #         # Max steps reached - compile answer from available context
# #         memory_context = self.memory.recall_context(task, max_tokens=800)
# #         final_prompt = f"Task: {task}\nInfo: {memory_context}\n\nBrief answer based on available info:"
        
# #         final_answer = await self.llm.simple_prompt(final_prompt, max_tokens=800)
        
# #         duration = time.time() - start_time
# #         self.memory.save_session(task, final_answer, duration)
        
# #         return final_answer
    
# #     async def cleanup(self):
# #         """Cleanup resources."""
# #         await self.llm.close()


# # # Backward compatibility
# # AutonomousAgent = FastAgent
# """Optimized autonomous agent with proper search result usage."""
# import time
# import json
# import re
# import asyncio
# from typing import List, Optional
# from models.agent import AgentThought, ToolResult
# from memory.hybrid import HybridMemory
# from core.llm import llm_client
# from tools.registry import tool_registry
# from config import AGENT_MAX_STEPS


# class FastAgent:
#     """Optimized autonomous agent with fixed search synthesis."""
    
#     def __init__(self, memory: HybridMemory):
#         self.memory = memory
#         self.llm = llm_client
        
#     async def _get_user_input(self, question: str) -> str:
#         """Get input from user."""
#         try:
#             return input(f"\033[93m{question}\033[0m ")
#         except (EOFError, KeyboardInterrupt):
#             return "not specified"
    
#     async def _execute_tool(self, tool_name: str, query: str) -> ToolResult:
#         """Execute a tool."""
#         print(f"\033[94m🔧 {tool_name}\033[0m")
        
#         try:
#             if tool_name == "ask_user":
#                 answer = await self._get_user_input(query)
#                 self.memory.remember(
#                     f"Q: {query} | A: {answer}",
#                     mem_type="preference",
#                     importance=0.9
#                 )
#                 return ToolResult(tool=tool_name, success=True, data=answer)
            
#             elif tool_name == "remember":
#                 mem_id = self.memory.remember(query, mem_type="fact", importance=0.8)
#                 return ToolResult(tool=tool_name, success=True, data=f"Stored as {mem_id}")
            
#             elif tool_name == "recall":
#                 # Use new recall_context method with token limit
#                 result = self.memory.recall_context(query, max_tokens=500)
#                 return ToolResult(tool=tool_name, success=True, data=result)
            
#             elif tool_registry.has_tool(tool_name):
#                 tool = tool_registry.get_tool(tool_name)
#                 result = await tool.execute(query)
                
#                 # Store search results with FULL content and HIGH importance
#                 if result.success and tool_name == "web_search":
#                     search_summary = f"Search: {query}\nResults:\n{str(result.data)}"
#                     self.memory.remember(
#                         search_summary,
#                         mem_type="tool_output",
#                         importance=0.95  # Very high importance for fresh searches
#                     )
#                     print(f"  ✓ Stored search results ({len(str(result.data))} chars)")
                
#                 return result
            
#             else:
#                 return ToolResult(tool=tool_name, success=False, data=None, error="Tool unavailable")
                
#         except Exception as e:
#             return ToolResult(tool=tool_name, success=False, data=None, error=str(e))
    
#     async def _think_fast(self, task: str, previous_thoughts: List[AgentThought]) -> AgentThought:
#         """Optimized thinking with memory context."""
        
#         # Get relevant memory context (uses graph + FTS)
#         memory_context = self.memory.recall_context(task, max_tokens=400)
        
#         # Condensed thought context (only last 2 steps)
#         recent_thoughts = previous_thoughts[-2:] if len(previous_thoughts) > 2 else previous_thoughts
#         thought_context = "\n".join([
#             f"{t.step}. {t.action}: {t.observation[:100] if t.observation else 'N/A'}"
#             for t in recent_thoughts
#         ])
        
#         # Count recent searches to prevent loops
#         recent_search_count = sum(1 for t in previous_thoughts[-3:] if t.action == "web_search")
        
#         # Dynamic prompt that adapts based on context
#         search_guidance = ""
#         if recent_search_count >= 2:
#             search_guidance = "You've already searched multiple times. Use those results - move to final_answer."
#         elif recent_search_count == 1:
#             search_guidance = "You've searched once. Only search again if you need different/additional information."
        
#         prompt = f"""Task: {task}

# Context: {memory_context[:300] if memory_context else 'Starting fresh'}
# Recent steps: {thought_context if thought_context else 'First step'}
# {search_guidance}

# Decide the next action. Choose the most efficient path to complete the task:
# - web_search: When you need current/factual information from the internet
# - ask_user: When you need clarification or missing information from the user
# - remember: When you should store important information for later
# - recall: When you need to retrieve previously stored information
# - final_answer: When you have enough information to answer the task

# Respond with valid JSON only:
# {{"reasoning": "why this action", "action": "action_name", "query": "specific query if needed", "complete": true/false}}"""

#         response = await self.llm.simple_prompt(prompt, max_tokens=400)
        
#         # Parse JSON with multiple fallback strategies
#         import json
#         import re
        
#         data = None
        
#         # Strategy 1: Direct parse
#         try:
#             data = json.loads(response.strip())
#         except:
#             pass
        
#         # Strategy 2: Remove markdown and try again
#         if not data:
#             try:
#                 clean = re.sub(r'```(?:json)?\s*|\s*```', '', response)
#                 data = json.loads(clean.strip())
#             except:
#                 pass
        
#         # Strategy 3: Find JSON and fix unquoted keys
#         if not data:
#             try:
#                 match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
#                 if match:
#                     json_str = match.group(0)
#                     # Fix unquoted keys
#                     json_str = re.sub(r'(\w+):', r'"\1":', json_str)
#                     # Fix single quotes
#                     json_str = json_str.replace("'", '"')
#                     data = json.loads(json_str)
#             except Exception as e:
#                 print(f"  ⚠️  JSON parse failed: {str(e)[:50]}")
#                 pass
        
#         # Strategy 4: Extract action manually
#         if not data:
#             try:
#                 action_match = re.search(r'["\']?action["\']?\s*:\s*["\'](\w+)["\']', response, re.IGNORECASE)
#                 if action_match:
#                     data = {
#                         "reasoning": "Recovered from malformed JSON",
#                         "action": action_match.group(1),
#                         "query": "",
#                         "complete": False
#                     }
#                     print(f"  ⚠️  Recovered action: {data['action']}")
#             except:
#                 pass
        
#         if data:
#             thought = AgentThought(
#                 step=len(previous_thoughts) + 1,
#                 reasoning=data.get("reasoning", "")[:150],
#                 action=data.get("action", "final_answer"),
#                 query=data.get("query", ""),
#                 complete=data.get("complete", False)
#             )
            
#             # Store thought with full content
#             thought.memory_id = self.memory.remember(
#                 f"Step {thought.step}: {thought.reasoning} → {thought.action}",
#                 mem_type="thought",
#                 importance=0.5
#             )
            
#             return thought
        
#         # Fallback: parsing completely failed
#         return AgentThought(
#             step=len(previous_thoughts) + 1,
#             reasoning="JSON parsing failed",
#             action="final_answer",
#             complete=True
#         )
    
#     async def run(self, task: str, max_steps: int = AGENT_MAX_STEPS) -> str:
#         """Run agent with enhanced memory utilization and proper search synthesis."""
#         print(f"\033[96m🤖 FastAgent running...\033[0m\n")
        
#         # Load context from similar past sessions
#         self.memory.load_past_session_context(task)
        
#         thoughts: List[AgentThought] = []
#         start_time = time.time()
        
#         for step in range(max_steps):
#             print(f"\033[96m💭 Step {step + 1}\033[0m")
            
#             thought = await self._think_fast(task, thoughts)
            
#             print(f"\033[2m{thought.reasoning[:100]}\033[0m")
#             print(f"\033[92m→ {thought.action}\033[0m")
            
#             # Execute action
#             if thought.action == "final_answer":
#                 # CRITICAL: Use FRESH search results from THIS session
#                 recent_searches = [
#                     t.observation for t in thoughts 
#                     if t.action == "web_search" and t.observation
#                 ]
                
#                 if recent_searches:
#                     # Use the actual search results from this session
#                     search_data = "\n\n=== NEXT RESULT ===\n\n".join(recent_searches[-3:])  # Last 3 searches
                    
#                     final_prompt = f"""You are a helpful AI assistant completing this task: {task}

# You just performed web searches. Here are the actual search results:

# {search_data[:4000]}

# Instructions:
# 1. Answer the user's question using ONLY information from the search results above
# 2. Be specific and concrete - include actual data points (prices, names, numbers, dates, URLs)
# 3. If the results contain links, include them
# 4. If the results mention specific entities (companies, products, people), name them
# 5. Don't add information not present in the results
# 6. Don't say "the results show..." - just give the answer directly
# 7. Format your response to be maximally useful for the user's specific request

# Answer the task concisely and specifically:"""

                    
                    
#                     print(f"\n\033[93m📊 Using {len(recent_searches)} fresh search results for answer\033[0m")
#                 else:
#                     # Fallback if no searches performed
#                     memory_context = self.memory.recall_context(task, max_tokens=800)
                    
#                     final_prompt = f"""Task: {task}

# Available information:
# {memory_context}

# Provide a helpful, specific answer using the information available. If you don't have enough information, explain what you would need to answer properly.

# Answer:"""
                    
#                     print(f"\n\033[93m📚 Using memory context for answer\033[0m")

#                 final_answer = await self.llm.simple_prompt(final_prompt, max_tokens=1000)
                
#                 # Save session with full context
#                 duration = time.time() - start_time
#                 self.memory.save_session(task, final_answer, duration)
                
#                 return final_answer
            
#             else:
#                 result = await self._execute_tool(thought.action, thought.query)
#                 thought.observation = str(result.data) if result.success else f"Error: {result.error}"
                
#                 # Detect search loops and force synthesis
#                 if thought.action == "web_search":
#                     recent_search_count = sum(1 for t in thoughts[-3:] if t.action == "web_search")
#                     if recent_search_count >= 2:
#                         print("  \033[93m⚠️  Detected search loop - forcing final answer\033[0m")
#                         # Force next iteration to synthesize
#                         thought.complete = True
            
#             # Create weighted connection between sequential thoughts
#             if thought.memory_id and thoughts and thoughts[-1].memory_id:
#                 self.memory.relate(thoughts[-1].memory_id, thought.memory_id, weight=1.0)
            
#             thoughts.append(thought)
            
#             if thought.complete:
#                 break
        
#         # Max steps reached - compile answer from available context
#         recent_searches = [t.observation for t in thoughts if t.action == "web_search" and t.observation]
        
#         if recent_searches:
#             search_data = "\n\n".join(recent_searches[-2:])
#             final_prompt = f"""Task: {task}

# Search Results:
# {search_data[:3000]}

# Based on these results, provide a brief answer:"""
#         else:
#             memory_context = self.memory.recall_context(task, max_tokens=800)
#             final_prompt = f"Task: {task}\nInfo: {memory_context}\n\nBrief answer:"
        
#         final_answer = await self.llm.simple_prompt(final_prompt, max_tokens=800)
        
#         duration = time.time() - start_time
#         self.memory.save_session(task, final_answer, duration)
        
#         return final_answer
    
#     async def cleanup(self):
#         """Cleanup resources."""
#         try:
#             if self.llm and hasattr(self.llm, '_client') and self.llm._client:
#                 await self.llm.close()
#         except:
#             pass


# # Backward compatibility
# AutonomousAgent = FastAgent






# v2

"""Optimized autonomous agent with proper search result usage."""
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


# class FastAgent:
#     """Optimized autonomous agent with fixed search synthesis."""
    
#     def __init__(self, memory: HybridMemory):
#         self.memory = memory
#         self.llm = llm_client
#         #new:
#         self.conversation_history = [] 
        
#     async def _get_user_input(self, question: str) -> str:
#         """Get input from user."""
#         try:
#             return input(f"\033[93m{question}\033[0m ")
#         except (EOFError, KeyboardInterrupt):
#             return "not specified"
    
#     async def _execute_tool(self, tool_name: str, query: str) -> ToolResult:
#         """Execute a tool."""
#         print(f"\033[94m🔧 {tool_name}\033[0m")
        
#         try:
#             if tool_name == "ask_user":
#                 answer = await self._get_user_input(query)
#                 self.memory.remember(
#                     f"Q: {query} | A: {answer}",
#                     mem_type="preference",
#                     importance=0.9
#                 )
#                 return ToolResult(tool=tool_name, success=True, data=answer)
            
#             elif tool_name == "remember":
#                 mem_id = self.memory.remember(query, mem_type="fact", importance=0.8)
#                 return ToolResult(tool=tool_name, success=True, data=f"Stored as {mem_id}")
            
#             elif tool_name == "recall":
#                 result = self.memory.recall_context(query, max_tokens=500)
#                 return ToolResult(tool=tool_name, success=True, data=result)
            
#             elif tool_registry.has_tool(tool_name):
#                 tool = tool_registry.get_tool(tool_name)
#                 result = await tool.execute(query)
                
#                 if result.success and tool_name == "web_search":
#                     search_summary = f"Search: {query}\nResults:\n{str(result.data)}"
#                     self.memory.remember(
#                         search_summary,
#                         mem_type="tool_output",
#                         importance=0.95
#                     )
#                     print(f"  ✓ Stored search results ({len(str(result.data))} chars)")
                
#                 return result
            
#             else:
#                 return ToolResult(tool=tool_name, success=False, data=None, error="Tool unavailable")
                
#         except Exception as e:
#             return ToolResult(tool=tool_name, success=False, data=None, error=str(e))
    
#     async def _think_fast(self, task: str, previous_thoughts: List[AgentThought]) -> AgentThought:
#         """Optimized thinking with Ez reasoning system."""
        
#         memory_context = self.memory.recall_context(task, max_tokens=400)
        
#         recent_thoughts = previous_thoughts[-2:] if len(previous_thoughts) > 2 else previous_thoughts
#         thought_context = "\n".join([
#             f"{t.step}. {t.action}: {t.observation[:100] if t.observation else 'N/A'}"
#             for t in recent_thoughts
#         ])
        
#         recent_search_count = sum(1 for t in previous_thoughts[-3:] if t.action == "web_search")
        
#         search_guidance = ""
#         if recent_search_count >= 2:
#             search_guidance = "You've already searched multiple times. Use those results - move to final_answer."
#         elif recent_search_count == 1:
#             search_guidance = "You've searched once. Only search again if you need different/additional information."
        
#         # Full Ez prompt
#         prompt = f"""You are Ez, a reasoning-focused AI assistant with web search capabilities.

# Your Strengths:
# - Deep analytical and logical reasoning
# - Breaking down complex problems into clear steps
# - Synthesizing information from multiple sources
# - Critical thinking and evaluation of information quality

# Your Tool:
# - Web search: Use this to find current, factual information when needed

# How You Work:
# 1. Think through problems systematically before acting
# 2. Use web search strategically - only when you need external information
# 3. Evaluate search results critically for relevance and reliability
# 4. Reason through the information to provide insightful answers
# 5. Be honest about uncertainty and limitations

# Communication Style:
# - Clear and direct - no unnecessary fluff
# - Explain your reasoning when it adds value
# - Adapt to the user's needs (technical vs. conversational)
# - Don't over-explain obvious steps

# Values:
# - Accuracy over speed
# - Practical solutions over theoretical perfection
# - Honesty about what you can and cannot do
# - Continuous learning from each interaction

# Current Task: {task}

# Context: {memory_context[:300] if memory_context else 'Starting fresh'}
# Recent Steps: {thought_context if thought_context else 'First step'}
# {search_guidance}

# Available Actions:
# - web_search: Find current/factual information from the internet
# - ask_user: Get clarification or missing information from user
# - remember: Store important information for later use
# - recall: Retrieve previously stored information
# - final_answer: Provide answer when you have sufficient information

# Think clearly and decide the most efficient next action. Respond with valid JSON only:
# {{"reasoning": "your logical thought process", "action": "action_name", "query": "specific query if needed", "complete": true/false}}"""

#         response = await self.llm.simple_prompt(prompt, max_tokens=400)
        
#         # Robust JSON parsing
#         data = None
        
#         # Strategy 1: Direct parse
#         try:
#             data = json.loads(response.strip())
#         except:
#             pass
        
#         # Strategy 2: Remove markdown
#         if not data:
#             try:
#                 clean = re.sub(r'```(?:json)?\s*|\s*```', '', response)
#                 data = json.loads(clean.strip())
#             except:
#                 pass
        
#         # Strategy 3: Find JSON and fix formatting
#         if not data:
#             try:
#                 match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
#                 if match:
#                     json_str = match.group(0)
#                     json_str = re.sub(r'(\w+):', r'"\1":', json_str)
#                     json_str = json_str.replace("'", '"')
#                     data = json.loads(json_str)
#             except Exception as e:
#                 print(f"  ⚠️  JSON parse failed: {str(e)[:50]}")
#                 pass
        
#         # Strategy 4: Extract action manually
#         if not data:
#             try:
#                 action_match = re.search(r'["\']?action["\']?\s*:\s*["\'](\w+)["\']', response, re.IGNORECASE)
#                 if action_match:
#                     data = {
#                         "reasoning": "Recovered from malformed JSON",
#                         "action": action_match.group(1),
#                         "query": "",
#                         "complete": False
#                     }
#                     print(f"  ⚠️  Recovered action: {data['action']}")
#             except:
#                 pass
        
#         if data:
#             thought = AgentThought(
#                 step=len(previous_thoughts) + 1,
#                 reasoning=data.get("reasoning", "")[:150],
#                 action=data.get("action", "final_answer"),
#                 query=data.get("query", ""),
#                 complete=data.get("complete", False)
#             )
            
#             thought.memory_id = self.memory.remember(
#                 f"Step {thought.step}: {thought.reasoning} → {thought.action}",
#                 mem_type="thought",
#                 importance=0.5
#             )
            
#             return thought
        
#         # Fallback
#         return AgentThought(
#             step=len(previous_thoughts) + 1,
#             reasoning="JSON parsing failed",
#             action="final_answer",
#             complete=True
#         )
#     def _build_context_with_history(self, task: str) -> str:
#         """Build context including conversation history."""
#         if not hasattr(self, 'conversation_history'):
#             self.conversation_history = []
        
#         context_parts = []
        
#         # Add recent conversation
#         if self.conversation_history:
#             context_parts.append("Recent conversation:")
#             for turn in self.conversation_history[-3:]:  # Last 3 turns
#                 context_parts.append(f"User: {turn['user']}")
#                 context_parts.append(f"Assistant: {turn['assistant'][:100]}...")
        
#         # Add current task
#         context_parts.append(f"\nCurrent task: {task}")
        
#         return "\n".join(context_parts)
    
#     async def run(self, task: str, max_steps: int = AGENT_MAX_STEPS) -> str:
#         """Run Ez agent with enhanced reasoning and search synthesis."""
#         print(f"\033[96m🤖 Ez Agent running...\033[0m\n")
#         context = self._build_context_with_history(task)
#         self.memory.load_past_session_context(task)
        
#         thoughts: List[AgentThought] = []
#         start_time = time.time()
        
#         for step in range(max_steps):
#             print(f"\033[96m💭 Step {step + 1}\033[0m")
            
#             thought = await self._think_fast(task, thoughts)
            
#             print(f"\033[2m{thought.reasoning[:100]}\033[0m")
#             print(f"\033[92m→ {thought.action}\033[0m")
            
#             if thought.action == "final_answer":
#                 recent_searches = [
#                     t.observation for t in thoughts 
#                     if t.action == "web_search" and t.observation
#                 ]
                
#                 if recent_searches:
#                     search_data = "\n\n=== NEXT RESULT ===\n\n".join(recent_searches[-3:])
                    
#                     final_prompt = f"""You are Ez, a helpful AI assistant completing this task: {task}

# You just performed web searches. Here are the actual search results:

# {search_data[:4000]}

# Instructions:
# 1. Answer the user's question using ONLY information from the search results above
# 2. Be specific and concrete - include actual data points (prices, names, numbers, dates, URLs)
# 3. If the results contain links, include them
# 4. If the results mention specific entities (companies, products, people), name them
# 5. Don't add information not present in the results
# 6. Don't say "the results show..." - just give the answer directly
# 7. Format your response to be maximally useful for the user's specific request

# Answer the task concisely and specifically:"""
                    
#                     print(f"\n\033[93m📊 Using {len(recent_searches)} fresh search results for answer\033[0m")
#                 else:
#                     memory_context = self.memory.recall_context(task, max_tokens=800)
                    
#                     final_prompt = f"""You are Ez, a reasoning-focused AI assistant with web search capabilities.

# Your Strengths:
# - Deep analytical and logical reasoning
# - Breaking down complex problems into clear steps
# - Synthesizing information from multiple sources
# - Critical thinking and evaluation of information quality

# Task: {task}

# Available information:
# {memory_context}

# Values:
# - Accuracy over speed
# - Practical solutions over theoretical perfection
# - Honesty about what you can and cannot do

# Provide a helpful, specific answer using the information available. If you don't have enough information, explain what you would need to answer properly.

# Answer:"""
                    
#                     print(f"\n\033[93m📚 Using memory context for answer\033[0m")

#                 final_answer = await self.llm.simple_prompt(final_prompt, max_tokens=1000)
                
#                 duration = time.time() - start_time
#                 self.memory.save_session(task, final_answer, duration)
                
#                 return final_answer
            
#             else:
#                 result = await self._execute_tool(thought.action, thought.query)
#                 thought.observation = str(result.data) if result.success else f"Error: {result.error}"
                
#                 if thought.action == "web_search":
#                     recent_search_count = sum(1 for t in thoughts[-3:] if t.action == "web_search")
#                     if recent_search_count >= 2:
#                         print("  \033[93m⚠️  Detected search loop - forcing final answer\033[0m")
#                         thought.complete = True
            
#             if thought.memory_id and thoughts and thoughts[-1].memory_id:
#                 self.memory.relate(thoughts[-1].memory_id, thought.memory_id, weight=1.0)
            
#             thoughts.append(thought)
            
#             if thought.complete:
#                 break
        
#         # Max steps reached
#         recent_searches = [t.observation for t in thoughts if t.action == "web_search" and t.observation]
        
#         if recent_searches:
#             search_data = "\n\n".join(recent_searches[-2:])
#             final_prompt = f"""You are Ez, a reasoning-focused AI assistant.

# Task: {task}

# Search Results:
# {search_data[:3000]}

# Based on these results, provide a brief, practical answer:"""
#         else:
#             memory_context = self.memory.recall_context(task, max_tokens=800)
#             final_prompt = f"""You are Ez, a reasoning-focused AI assistant.

# Task: {task}
# Available Info: {memory_context}

# Provide a brief, honest answer based on what's available:"""
        
#         final_answer = await self.llm.simple_prompt(final_prompt, max_tokens=800)
        
#         duration = time.time() - start_time
#         self.memory.save_session(task, final_answer, duration)
        
#         return final_answer
    
#     async def cleanup(self):
#         """Cleanup resources."""
#         try:
#             if self.llm and hasattr(self.llm, '_client') and self.llm._client:
#                 await self.llm.close()
#         except:
#             pass

# v3


class IntelligentAgent:
    """Agent that trusts LLM intelligence instead of micromanaging with rules."""
    
    def __init__(self, memory: HybridMemory):
        self.memory = memory
        self.llm = llm_client
        self.conversation_history = [] 
        
    async def _get_user_input(self, question: str) -> str:
        """Get input from user."""
        try:
            return input(f"\033[93m{question}\033[0m ")
        except (EOFError, KeyboardInterrupt):
            return "not specified"
    
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
                return ToolResult(tool=tool_name, success=True, data=f"Stored as {mem_id}")
            
            elif tool_name == "recall":
                result = self.memory.recall_context(query, max_tokens=500)
                return ToolResult(tool=tool_name, success=True, data=result)
            
            elif tool_registry.has_tool(tool_name):
                tool = tool_registry.get_tool(tool_name)
                result = await tool.execute(query)
                
                if result.success and tool_name == "web_search":
                    search_summary = f"Search: {query}\nResults:\n{str(result.data)}"
                    self.memory.remember(
                        search_summary,
                        mem_type="tool_output",
                        importance=0.95
                    )
                    print(f"  ✓ Stored search results ({len(str(result.data))} chars)")
                
                return result
            
            else:
                return ToolResult(tool=tool_name, success=False, data=None, error="Tool unavailable")
                
        except Exception as e:
            return ToolResult(tool=tool_name, success=False, data=None, error=str(e))
    
    def _build_context_with_history(self, task: str) -> str:
        """Build context including conversation history."""
        context_parts = []
        
        # Add recent conversation
        if self.conversation_history:
            context_parts.append("Recent conversation:")
            for turn in self.conversation_history[-3:]:
                context_parts.append(f"User: {turn['user']}")
                context_parts.append(f"Assistant: {turn['assistant'][:100]}...")
        
        # Add current task
        context_parts.append(f"\nCurrent task: {task}")
        
        return "\n".join(context_parts)
    
    async def _think_intelligently(self, task: str, previous_thoughts: List[AgentThought]) -> AgentThought:
        """Let the LLM think intelligently with MORE reasoning space."""
        
        # Get context
        context_with_history = self._build_context_with_history(task)
        memory_context = self.memory.recall_context(context_with_history, max_tokens=600)
        
        # Build recent steps summary
        recent_thoughts = previous_thoughts[-3:] if len(previous_thoughts) > 3 else previous_thoughts
        thought_context = "\n".join([
            f"Step {t.step}: {t.action} - {t.observation[:150] if t.observation else 'pending'}..."
            for t in recent_thoughts
        ])
        
        # Simple, trust-based prompt - let the LLM think
        prompt = f"""You are an intelligent AI agent helping with this task:

TASK: {task}

AVAILABLE INFORMATION:
{memory_context if memory_context else "No stored information relevant to this task"}

WHAT YOU'VE DONE SO FAR:
{thought_context if thought_context else "This is your first step"}

AVAILABLE TOOLS:
- web_search: Search the internet for current information
- ask_user: Ask the user a clarifying question
- remember: Store information for later
- recall: Retrieve stored information
- final_answer: Provide your final answer to the user

THINK STEP BY STEP:
1. Do I have enough RELEVANT information to answer this task?
2. If the available information is about a different topic, should I search instead?
3. What's the most logical next action?

Respond with JSON:
{{"reasoning": "your detailed thinking process", "action": "chosen_action", "query": "query for the action if needed", "complete": true/false}}"""

        # Give MORE tokens for reasoning (800 instead of 400)
        response = await self.llm.simple_prompt(prompt, max_tokens=800)
        
        # Robust JSON parsing
        data = None
        
        # Strategy 1: Direct parse
        try:
            data = json.loads(response.strip())
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Remove markdown
        if not data:
            try:
                clean = re.sub(r'```(?:json)?\s*|\s*```', '', response)
                data = json.loads(clean.strip())
            except json.JSONDecodeError:
                pass
        
        # Strategy 3: Find JSON and fix formatting
        if not data:
            try:
                match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    json_str = re.sub(r'(\w+):', r'"\1":', json_str)
                    json_str = json_str.replace("'", '"')
                    data = json.loads(json_str)
            except (json.JSONDecodeError, AttributeError) as e:
                print(f"  ⚠️  JSON parse failed: {str(e)[:50]}")
        
        # Strategy 4: Extract action manually
        if not data:
            try:
                action_match = re.search(r'["\']?action["\']?\s*:\s*["\'](\w+)["\']', response, re.IGNORECASE)
                if action_match:
                    data = {
                        "reasoning": "Recovered from malformed JSON",
                        "action": action_match.group(1),
                        "query": "",
                        "complete": False
                    }
                    print(f"  ⚠️  Recovered action: {data['action']}")
            except Exception as e:
                print(f"  ⚠️  Action recovery failed: {str(e)[:50]}")
        
        if data:
            thought = AgentThought(
                step=len(previous_thoughts) + 1,
                reasoning=data.get("reasoning", "")[:200],  # Allow longer reasoning
                action=data.get("action", "final_answer"),
                query=str(data.get("query") or ""),
                complete=data.get("complete", False)
            )
            
            thought.memory_id = self.memory.remember(
                f"Step {thought.step}: {thought.reasoning} → {thought.action}",
                mem_type="thought",
                importance=0.5
            )
            
            return thought
        
        # Fallback
        return AgentThought(
            step=len(previous_thoughts) + 1,
            reasoning="JSON parsing failed - searching by default",
            action="web_search",
            query=task,
            complete=False
        )
    
    async def run(self, task: str, max_steps: int = AGENT_MAX_STEPS) -> str:
        """Run intelligent agent."""
        print(f"\033[96m🤖 Intelligent Agent running...\033[0m\n")
        
        self.memory.load_past_session_context(task)
        
        thoughts: List[AgentThought] = []
        start_time = time.time()
        
        for step in range(max_steps):
            print(f"\033[96m💭 Step {step + 1}\033[0m")
            
            thought = await self._think_intelligently(task, thoughts)
            
            print(f"\033[2m{thought.reasoning[:150]}\033[0m")
            print(f"\033[92m→ {thought.action}\033[0m")
            
            if thought.action == "final_answer":
                recent_searches = [
                    t.observation for t in thoughts 
                    if t.action == "web_search" and t.observation
                ]
                
                if recent_searches:
                    search_data = "\n\n=== NEXT RESULT ===\n\n".join(recent_searches[-3:])
                    
                    final_prompt = f"""Task: {task}

Search results:
{search_data[:4000]}

Provide a helpful, specific answer using the search results. Include concrete details, names, locations, prices, etc.

Answer:"""
                    
                    print(f"\n\033[93m📊 Using {len(recent_searches)} search results\033[0m")
                else:
                    memory_context = self.memory.recall_context(task, max_tokens=800)
                    
                    final_prompt = f"""Task: {task}

Available information:
{memory_context}

Provide a helpful answer. If you don't have enough information, be honest about it.

Answer:"""
                    
                    print(f"\n\033[93m📚 Using memory context\033[0m")

                final_answer = await self.llm.simple_prompt(final_prompt, max_tokens=1000)
                
                duration = time.time() - start_time
                self.memory.save_session(task, final_answer, duration)
                
                # Update conversation history
                self.conversation_history.append({
                    'user': task,
                    'assistant': final_answer
                })
                
                return final_answer
            
            else:
                result = await self._execute_tool(thought.action, thought.query)
                thought.observation = str(result.data) if result.success else f"Error: {result.error}"
                
                # Simple loop detection - if we've searched 3+ times, force answer
                if thought.action == "web_search":
                    recent_search_count = sum(1 for t in thoughts[-4:] if t.action == "web_search")
                    if recent_search_count >= 3:
                        print("  \033[93m⚠️  Multiple searches completed - moving to answer\033[0m")
                        thought.complete = True
            
            if thought.memory_id and thoughts and thoughts[-1].memory_id:
                self.memory.relate(thoughts[-1].memory_id, thought.memory_id, weight=1.0)
            
            thoughts.append(thought)
            
            if thought.complete:
                break
        
        # Max steps reached - generate answer with what we have
        recent_searches = [t.observation for t in thoughts if t.action == "web_search" and t.observation]
        
        if recent_searches:
            search_data = "\n\n".join(recent_searches[-2:])
            final_prompt = f"Task: {task}\n\nSearch results:\n{search_data[:3000]}\n\nProvide a brief answer:"
        else:
            memory_context = self.memory.recall_context(task, max_tokens=800)
            final_prompt = f"Task: {task}\nInfo: {memory_context}\n\nProvide a brief answer:"
        
        final_answer = await self.llm.simple_prompt(final_prompt, max_tokens=800)
        
        duration = time.time() - start_time
        self.memory.save_session(task, final_answer, duration)
        
        # Update conversation history
        self.conversation_history.append({
            'user': task,
            'assistant': final_answer
        })
        
        return final_answer
    
    async def cleanup(self):
        """Cleanup resources."""
        try:
            if self.llm and hasattr(self.llm, '_client') and self.llm._client:
                await self.llm.close()
        except Exception as e:
            print(f"Warning: Cleanup failed: {str(e)}")


# Aliases
FastAgent = IntelligentAgent
AutonomousAgent = IntelligentAgent

