"""Fix agent to properly synthesize search results instead of looping."""

print("="*80)
print("FIXING SEARCH RESULT SYNTHESIS")
print("="*80)

# Fix 1: Improve loop detection and force synthesis
agent_file = "core/agent.py"
with open(agent_file, 'r') as f:
    content = f.read()

# Find the loop detection section and improve it
old_loop_detection = """                # Detect search loops
                if thought.action == "web_search":
                    recent_searches = [t for t in thoughts[-3:] if t.action == "web_search"]
                    if len(recent_searches) >= 2:
                        print("  ⚠️  Search loop detected - forcing synthesis")
                        # Next iteration should synthesize results
                        thought.complete = True"""

new_loop_detection = """                # Detect search loops and force synthesis
                if thought.action == "web_search":
                    recent_searches = [t for t in thoughts[-3:] if t.action == "web_search"]
                    if len(recent_searches) >= 2:
                        print("  ⚠️  Detected search loop - moving to synthesis")
                        
                        # Collect all search results from this session
                        search_results = []
                        for t in thoughts:
                            if t.action == "web_search" and t.observation:
                                search_results.append(t.observation[:500])  # Keep recent searches
                        
                        # Force next action to be final_answer with search context
                        if search_results:
                            thought.complete = True
                            # Store combined context for final answer
                            combined_results = "\\n\\n".join(search_results[-2:])  # Last 2 searches
                            self.memory.remember(
                                f"Recent search results for synthesis:\\n{combined_results}",
                                mem_type="tool_output",
                                importance=1.0  # Maximum importance
                            )
                            print(f"  ✓ Prepared {len(search_results)} search results for synthesis")"""

if old_loop_detection in content:
    content = content.replace(old_loop_detection, new_loop_detection)
    print("✓ Improved loop detection with forced synthesis")
else:
    print("⚠ Loop detection not found or already patched")

# Fix 2: Improve final answer compilation to prioritize recent searches
old_final_answer = """            # Execute action
            if thought.action == "final_answer":
                # Get relevant memories for final answer
                memory_context = self.memory.recall_context(task, max_tokens=800)
                
                final_prompt = f\"\"\"Task: {task}
Relevant Information:
{memory_context}

Provide a concise, comprehensive final answer:\"\"\"

                final_answer = await self.llm.simple_prompt(final_prompt, max_tokens=1000)"""

new_final_answer = """            # Execute action
            if thought.action == "final_answer":
                # Get RECENT search results specifically
                recent_tool_outputs = [
                    t.observation for t in thoughts 
                    if t.action == "web_search" and t.observation
                ]
                
                if recent_tool_outputs:
                    # Use fresh search results
                    search_context = "\\n\\n".join(recent_tool_outputs[-2:])  # Last 2 searches
                    
                    final_prompt = f\"\"\"Task: {task}

Search Results (USE THESE):
{search_context[:2000]}

Based on the search results above, provide a clear, specific answer with:
1. Actual prices/data from the results
2. Airline names mentioned
3. Booking links if provided

Answer:\"\"\"
                else:
                    # Fallback to memory
                    memory_context = self.memory.recall_context(task, max_tokens=800)
                    
                    final_prompt = f\"\"\"Task: {task}
Relevant Information:
{memory_context}

Provide a concise, comprehensive final answer:\"\"\"

                final_answer = await self.llm.simple_prompt(final_prompt, max_tokens=1000)"""

if old_final_answer in content:
    content = content.replace(old_final_answer, new_final_answer)
    print("✓ Improved final answer compilation to use fresh results")
else:
    print("⚠ Final answer section not found or already patched")

# Save changes
with open(agent_file, 'w') as f:
    f.write(content)

print("\n" + "="*80)
print("FIXES APPLIED")
print("="*80)
print("\nWhat changed:")
print("1. After 2 searches, agent now stores combined results with MAX importance")
print("2. Final answer uses RECENT search observations directly (not old memories)")
print("3. Agent explicitly told to use the search results in the prompt")
print("\nTest again:")
print("  python test3.py")
print("  Task: cheap flight for bali from delhi for tomorrow")
print("\nExpected behavior:")
print("  - Searches 2-3 times")
print("  - Detects loop")
print("  - Uses FRESH results to provide actual prices from ixigo/Google/Skyscanner")
print("="*80)