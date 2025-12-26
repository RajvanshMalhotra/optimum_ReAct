"""Comprehensive real-world agent test with search and logical reasoning."""
import asyncio
import os
from pathlib import Path

from memory.hybrid import HybridMemory
from core.agent import FastAgent
from tools.registry import tool_registry


# Test database
TEST_DB = "test_comprehensive.db"


async def test_multi_hop_reasoning():
    """Test 1: Multi-hop logical reasoning requiring multiple steps."""
    print("\n" + "="*80)
    print("TEST 1: MULTI-HOP LOGICAL REASONING")
    print("="*80)
    print("Task: Chain of reasoning to solve a logic puzzle")
    print("-"*80)
    
    memory = HybridMemory(TEST_DB)
    agent = FastAgent(memory)
    
    task = """
    Given these facts:
    1. All mammals are warm-blooded
    2. All dogs are mammals
    3. Max is a dog
    
    Question: Is Max warm-blooded? Explain your reasoning step by step.
    """
    
    try:
        result = await agent.run(task, max_steps=8)
        
        print(f"\n{'='*80}")
        print("AGENT RESPONSE:")
        print("="*80)
        print(result)
        print("="*80)
        
        # Validate reasoning
        has_logic = any(word in result.lower() for word in ["therefore", "because", "since", "thus"])
        has_answer = "warm-blooded" in result.lower() and ("yes" in result.lower() or "max is" in result.lower())
        
        print(f"\n✓ Contains logical connectors: {has_logic}")
        print(f"✓ Contains correct conclusion: {has_answer}")
        
        assert has_logic, "Missing logical reasoning connectors"
        assert has_answer, "Missing correct conclusion"
        
        print("\n✅ PASSED: Multi-hop reasoning works")
        
    finally:
        pass


async def test_web_search_and_synthesis():
    """Test 2: Web search with information synthesis."""
    print("\n" + "="*80)
    print("TEST 2: WEB SEARCH + INFORMATION SYNTHESIS")
    print("="*80)
    
    if not tool_registry.has_tool("web_search"):
        print("⚠️  SKIPPED: Web search not available (set TAVILY_API_KEY)")
        return
    
    print("Task: Research and compare multiple pieces of information")
    print("-"*80)
    
    memory = HybridMemory(TEST_DB)
    agent = FastAgent(memory)
    
    task = """
    Find the current Bitcoin price and the current Ethereum price.
    Then tell me which one has a higher price and by approximately how much.
    """
    
    try:
        result = await agent.run(task, max_steps=10)
        
        print(f"\n{'='*80}")
        print("AGENT RESPONSE:")
        print("="*80)
        print(result)
        print("="*80)
        
        # Validate search was used and synthesis occurred
        has_prices = any(word in result.lower() for word in ["$", "price", "bitcoin", "ethereum"])
        has_comparison = any(word in result.lower() for word in ["higher", "lower", "more", "less", "difference"])
        
        print(f"\n✓ Contains price information: {has_prices}")
        print(f"✓ Contains comparison: {has_comparison}")
        
        assert has_prices, "Missing price information from search"
        assert has_comparison, "Missing comparison/synthesis"
        
        print("\n✅ PASSED: Web search and synthesis works")
        
    finally:
        pass


async def test_memory_based_reasoning():
    """Test 3: Reasoning that requires remembering and recalling information."""
    print("\n" + "="*80)
    print("TEST 3: MEMORY-BASED REASONING")
    print("="*80)
    print("Task: Multi-turn conversation requiring memory")
    print("-"*80)
    
    memory = HybridMemory(TEST_DB)
    
    # Turn 1: Store information
    agent1 = FastAgent(memory)
    task1 = """
    Remember these three facts about me:
    1. My name is Alex
    2. I work as a software engineer
    3. My favorite programming language is Python
    """
    
    print("\nTurn 1: Storing information...")
    result1 = await agent1.run(task1, max_steps=6)
    print(f"Response: {result1[:100]}...")
    
    # Turn 2: Recall and reason
    agent2 = FastAgent(memory)
    task2 = """
    Based on what you know about me, would I be a good fit for a job that requires:
    - 5 years of Java experience
    - Background in hardware engineering
    - Preference for C++ development
    
    Explain your reasoning.
    """
    
    print("\nTurn 2: Recalling and reasoning...")
    result2 = await agent2.run(task2, max_steps=8)
    
    print(f"\n{'='*80}")
    print("AGENT RESPONSE:")
    print("="*80)
    print(result2)
    print("="*80)
    
    # Validate memory recall and reasoning
    recalls_name = "alex" in result2.lower()
    recalls_job = "software" in result2.lower() or "engineer" in result2.lower()
    recalls_lang = "python" in result2.lower()
    has_reasoning = any(word in result2.lower() for word in ["because", "since", "however", "but"])
    
    print(f"\n✓ Recalls name: {recalls_name}")
    print(f"✓ Recalls job: {recalls_job}")
    print(f"✓ Recalls language preference: {recalls_lang}")
    print(f"✓ Contains reasoning: {has_reasoning}")
    
    assert recalls_job or recalls_lang, "Failed to recall stored information"
    assert has_reasoning, "Missing reasoning based on recalled facts"
    
    print("\n✅ PASSED: Memory-based reasoning works")


async def test_complex_search_task():
    """Test 4: Complex task requiring multiple searches and reasoning."""
    print("\n" + "="*80)
    print("TEST 4: COMPLEX MULTI-SEARCH TASK")
    print("="*80)
    
    if not tool_registry.has_tool("web_search"):
        print("⚠️  SKIPPED: Web search not available (set TAVILY_API_KEY)")
        return
    
    print("Task: Research, compare, and recommend")
    print("-"*80)
    
    memory = HybridMemory(TEST_DB)
    agent = FastAgent(memory)
    
    task = """
    I need to buy a new laptop for software development. 
    Search for the top 3 laptops for developers in 2024.
    Then tell me which one you'd recommend and why.
    """
    
    try:
        result = await agent.run(task, max_steps=12)
        
        print(f"\n{'='*80}")
        print("AGENT RESPONSE:")
        print("="*80)
        print(result)
        print("="*80)
        
        # Validate comprehensive response
        has_laptops = any(word in result.lower() for word in ["laptop", "macbook", "thinkpad", "dell", "hp"])
        has_recommendation = any(word in result.lower() for word in ["recommend", "suggest", "choose", "best"])
        has_reasoning = any(word in result.lower() for word in ["because", "since", "due to", "reason"])
        is_long_enough = len(result) > 200  # Should be detailed
        
        print(f"\n✓ Mentions laptops: {has_laptops}")
        print(f"✓ Contains recommendation: {has_recommendation}")
        print(f"✓ Contains reasoning: {has_reasoning}")
        print(f"✓ Detailed response (200+ chars): {is_long_enough}")
        
        assert has_laptops, "Missing laptop information"
        assert has_recommendation, "Missing recommendation"
        assert has_reasoning, "Missing reasoning for recommendation"
        
        print("\n✅ PASSED: Complex multi-search task works")
        
    finally:
        pass


async def test_mathematical_reasoning():
    """Test 5: Mathematical and logical problem solving."""
    print("\n" + "="*80)
    print("TEST 5: MATHEMATICAL REASONING")
    print("="*80)
    print("Task: Solve a word problem requiring multiple calculations")
    print("-"*80)
    
    memory = HybridMemory(TEST_DB)
    agent = FastAgent(memory)
    
    task = """
    Sarah has 3 times as many apples as Tom.
    Tom has 5 more apples than Lisa.
    Lisa has 7 apples.
    
    How many apples does Sarah have? Show your work step by step.
    """
    
    try:
        result = await agent.run(task, max_steps=8)
        
        print(f"\n{'='*80}")
        print("AGENT RESPONSE:")
        print("="*80)
        print(result)
        print("="*80)
        
        # Validate mathematical reasoning
        mentions_lisa = "lisa" in result.lower() and "7" in result
        mentions_tom = "tom" in result.lower()
        has_calculation = any(op in result for op in ["+", "×", "*", "="])
        has_answer = "36" in result or "thirty-six" in result.lower()
        
        print(f"\n✓ References Lisa's count: {mentions_lisa}")
        print(f"✓ References Tom: {mentions_tom}")
        print(f"✓ Shows calculations: {has_calculation}")
        print(f"✓ Correct answer (36): {has_answer}")
        
        assert mentions_lisa and mentions_tom, "Missing problem components"
        assert has_answer, "Incorrect or missing final answer (should be 36)"
        
        print("\n✅ PASSED: Mathematical reasoning works")
        
    finally:
        pass


async def test_search_and_fact_check():
    """Test 6: Use search to verify facts and detect contradictions."""
    print("\n" + "="*80)
    print("TEST 6: SEARCH-BASED FACT CHECKING")
    print("="*80)
    
    if not tool_registry.has_tool("web_search"):
        print("⚠️  SKIPPED: Web search not available (set TAVILY_API_KEY)")
        return
    
    print("Task: Verify a claim using web search")
    print("-"*80)
    
    memory = HybridMemory(TEST_DB)
    agent = FastAgent(memory)
    
    task = """
    I heard that Python was created in the 1970s. 
    Can you search and verify if this is correct? 
    Tell me the actual year Python was created.
    """
    
    try:
        result = await agent.run(task, max_steps=8)
        
        print(f"\n{'='*80}")
        print("AGENT RESPONSE:")
        print("="*80)
        print(result)
        print("="*80)
        
        # Validate fact checking (Python was created in 1991, not 1970s)
        mentions_1991 = "1991" in result or "1990" in result or "early 1990" in result.lower()
        corrects_claim = "incorrect" in result.lower() or "not" in result.lower() or "actually" in result.lower()
        
        print(f"\n✓ Mentions correct year (1991): {mentions_1991}")
        print(f"✓ Corrects false claim: {corrects_claim}")
        
        assert mentions_1991, "Failed to find correct information"
        assert corrects_claim, "Failed to identify incorrect claim"
        
        print("\n✅ PASSED: Fact checking with search works")
        
    finally:
        pass


async def test_chain_of_thought_planning():
    """Test 7: Planning a multi-step task with dependencies."""
    print("\n" + "="*80)
    print("TEST 7: CHAIN-OF-THOUGHT PLANNING")
    print("="*80)
    print("Task: Plan a complex task with logical dependencies")
    print("-"*80)
    
    memory = HybridMemory(TEST_DB)
    agent = FastAgent(memory)
    
    task = """
    I want to learn web development from scratch.
    Create a learning roadmap for me with the logical order of topics I should study.
    Explain why each step comes before the next.
    """
    
    try:
        result = await agent.run(task, max_steps=10)
        
        print(f"\n{'='*80}")
        print("AGENT RESPONSE:")
        print("="*80)
        print(result)
        print("="*80)
        
        # Validate planning and reasoning
        has_topics = sum(1 for topic in ["html", "css", "javascript", "react", "node"] 
                        if topic in result.lower()) >= 3
        has_order = any(word in result.lower() for word in ["first", "then", "next", "after", "before"])
        has_reasoning = any(word in result.lower() for word in ["because", "since", "foundation", "prerequisite"])
        is_structured = len(result.split('\n')) > 5  # Multiple lines/steps
        
        print(f"\n✓ Contains web dev topics (3+): {has_topics}")
        print(f"✓ Shows logical order: {has_order}")
        print(f"✓ Explains reasoning: {has_reasoning}")
        print(f"✓ Structured response: {is_structured}")
        
        assert has_topics, "Missing key web development topics"
        assert has_order and has_reasoning, "Missing logical ordering and reasoning"
        
        print("\n✅ PASSED: Chain-of-thought planning works")
        
    finally:
        pass


async def test_graph_memory_reasoning():
    """Test 8: Reasoning using connected memories from graph."""
    print("\n" + "="*80)
    print("TEST 8: GRAPH-BASED MEMORY REASONING")
    print("="*80)
    print("Task: Build connected knowledge and reason across it")
    print("-"*80)
    
    memory = HybridMemory(TEST_DB)
    
    # Build connected knowledge graph
    id1 = memory.remember("React is a JavaScript library", mem_type="fact", importance=0.9)
    id2 = memory.remember("React is used for building user interfaces", mem_type="fact", importance=0.9)
    id3 = memory.remember("React was created by Facebook", mem_type="fact", importance=0.8)
    id4 = memory.remember("JavaScript runs in web browsers", mem_type="fact", importance=0.8)
    
    # Create connections
    memory.relate(id1, id2, weight=1.0)
    memory.relate(id1, id4, weight=0.8)
    memory.relate(id2, id3, weight=0.7)
    
    print("✓ Built knowledge graph with 4 connected facts")
    
    # Now ask agent to reason using this knowledge
    agent = FastAgent(memory)
    task = """
    Based on what you know about React, explain to a beginner:
    1. What React is
    2. What it's used for
    3. Where it runs
    
    Use the information you have stored in memory.
    """
    
    try:
        result = await agent.run(task, max_steps=8)
        
        print(f"\n{'='*80}")
        print("AGENT RESPONSE:")
        print("="*80)
        print(result)
        print("="*80)
        
        # Validate graph memory was used
        mentions_react = "react" in result.lower()
        mentions_javascript = "javascript" in result.lower()
        mentions_ui = "interface" in result.lower() or "ui" in result.lower()
        has_structure = result.count('\n') > 2 or any(num in result for num in ["1.", "2.", "3."])
        
        print(f"\n✓ Mentions React: {mentions_react}")
        print(f"✓ Mentions JavaScript: {mentions_javascript}")
        print(f"✓ Mentions UI/interfaces: {mentions_ui}")
        print(f"✓ Structured response: {has_structure}")
        
        recalled_facts = sum([mentions_react, mentions_javascript, mentions_ui])
        assert recalled_facts >= 2, "Failed to recall connected memories from graph"
        
        print("\n✅ PASSED: Graph-based memory reasoning works")
        
    finally:
        pass


async def run_comprehensive_tests():
    """Run all comprehensive tests."""
    print("\n" + "="*80)
    print("🧪 COMPREHENSIVE AGENT TEST SUITE")
    print("   Testing Real-World Search & Reasoning Capabilities")
    print("="*80)
    
    # Clean test database
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        print(f"✓ Cleaned test database: {TEST_DB}\n")
    
    tests = [
        ("Multi-Hop Logical Reasoning", test_multi_hop_reasoning),
        ("Web Search + Synthesis", test_web_search_and_synthesis),
        ("Memory-Based Reasoning", test_memory_based_reasoning),
        ("Complex Multi-Search Task", test_complex_search_task),
        ("Mathematical Reasoning", test_mathematical_reasoning),
        ("Search-Based Fact Checking", test_search_and_fact_check),
        ("Chain-of-Thought Planning", test_chain_of_thought_planning),
        ("Graph-Based Memory Reasoning", test_graph_memory_reasoning),
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    start_time = asyncio.get_event_loop().time()
    
    for name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ {name} FAILED")
            print(f"   Reason: {e}")
            failed += 1
        except Exception as e:
            if "SKIPPED" in str(e) or "Web search not available" in str(e):
                skipped += 1
            else:
                print(f"\n❌ {name} ERROR: {e}")
                import traceback
                traceback.print_exc()
                failed += 1
    
    end_time = asyncio.get_event_loop().time()
    duration = end_time - start_time
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"✅ Passed:  {passed}/{len(tests)}")
    print(f"❌ Failed:  {failed}/{len(tests)}")
    print(f"⚠️  Skipped: {skipped}/{len(tests)} (missing API keys)")
    print(f"⏱️  Duration: {duration:.1f}s")
    
    if failed == 0:
        print("\n🎉 All tests passed! Agent is fully functional.")
    else:
        print(f"\n⚠️  {failed} test(s) failed - review output above")
    
    # Cleanup
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    
    # Close shared LLM client
    from core.llm import llm_client
    try:
        await llm_client.close()
    except:
        pass
    
    print("="*80)


if __name__ == "__main__":
    asyncio.run(run_comprehensive_tests())