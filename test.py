"""Comprehensive agent testing suite."""
import asyncio
import time
from pathlib import Path

from memory.hybrid import HybridMemory
from core.agent import FastAgent
from tools.registry import tool_registry

# Initialize test database
TEST_DB = "test_memory.db"

async def test_basic_reasoning():
    """Test 1: Basic reasoning without tools."""
    print("\n" + "="*60)
    print("TEST 1: Basic Reasoning")
    print("="*60)
    
    memory = HybridMemory(TEST_DB)
    agent = FastAgent(memory)
    
    result = await agent.run(
        "What is 15 * 23? Think step by step.",
        max_steps=3
    )
    
    print(f"\n✅ Result: {result}")
    await agent.cleanup()
    
    # Check if answer is correct (345)
    assert "345" in result, "Math calculation failed"
    print("✓ Basic reasoning works")


async def test_memory_persistence():
    """Test 2: Memory storage and recall."""
    print("\n" + "="*60)
    print("TEST 2: Memory Persistence")
    print("="*60)
    
    memory = HybridMemory(TEST_DB)
    
    # Store some facts
    id1 = memory.remember(
        "Python was created by Guido van Rossum",
        mem_type="fact",
        importance=0.9
    )
    id2 = memory.remember(
        "Python is a high-level programming language",
        mem_type="fact",
        importance=0.8
    )
    memory.relate(id1, id2, weight=0.9)
    
    print(f"✓ Stored 2 memories: {id1}, {id2}")
    
    # Recall
    results = memory.recall("Python creator", limit=2)
    print(f"✓ Recalled {len(results)} memories")
    
    for mem in results:
        print(f"  - {mem.content[:60]}...")
    
    assert len(results) > 0, "Recall failed"
    print("✓ Memory persistence works")


async def test_web_search():
    """Test 3: Web search tool."""
    print("\n" + "="*60)
    print("TEST 3: Web Search")
    print("="*60)
    
    if not tool_registry.has_tool("web_search"):
        print("⚠ Web search not available (TAVILY_API_KEY not set)")
        return
    
    memory = HybridMemory(TEST_DB)
    agent = FastAgent(memory)
    
    result = await agent.run(
        "What is the current price of Bitcoin?",
        max_steps=5
    )
    
    print(f"\n✅ Result: {result[:200]}...")
    await agent.cleanup()
    
    # Should contain price info
    assert any(word in result.lower() for word in ["$", "price", "bitcoin", "btc"]), \
        "Search result doesn't contain expected info"
    print("✓ Web search works")


async def test_multi_step_reasoning():
    """Test 4: Multi-step task with memory."""
    print("\n" + "="*60)
    print("TEST 4: Multi-Step Reasoning")
    print("="*60)
    
    memory = HybridMemory(TEST_DB)
    agent = FastAgent(memory)
    
    result = await agent.run(
        "First remember that my favorite color is blue. "
        "Then remember that I like cats. "
        "Finally, tell me what you remember about me.",
        max_steps=10
    )
    
    print(f"\n✅ Result: {result}")
    await agent.cleanup()
    
    # Should recall both facts
    assert "blue" in result.lower(), "Didn't recall color"
    assert "cat" in result.lower(), "Didn't recall animal preference"
    print("✓ Multi-step reasoning with memory works")


async def test_cross_session_memory():
    """Test 5: Cross-session memory retrieval."""
    print("\n" + "="*60)
    print("TEST 5: Cross-Session Memory")
    print("="*60)
    
    # Session 1: Store information
    memory1 = HybridMemory(TEST_DB)
    agent1 = FastAgent(memory1)
    
    await agent1.run(
        "Remember that the optimal GPU for gaming in 2024 is RTX 4090",
        max_steps=3
    )
    await agent1.cleanup()
    print("✓ Session 1 completed")
    
    # Small delay
    await asyncio.sleep(1)
    
    # Session 2: Recall information
    memory2 = HybridMemory(TEST_DB)
    agent2 = FastAgent(memory2)
    
    result = await agent2.run(
        "What GPU did I mention for gaming?",
        max_steps=5
    )
    
    print(f"\n✅ Result: {result}")
    await agent2.cleanup()
    
    # Should recall from previous session
    assert "4090" in result or "rtx" in result.lower(), \
        "Failed to recall from previous session"
    print("✓ Cross-session memory works")


async def test_graph_traversal():
    """Test 6: Graph relationship traversal."""
    print("\n" + "="*60)
    print("TEST 6: Graph Traversal")
    print("="*60)
    
    memory = HybridMemory(TEST_DB)
    
    # Create a chain of related memories
    id1 = memory.remember("Machine learning is a subset of AI", 
                         mem_type="fact", importance=0.8)
    id2 = memory.remember("Neural networks are used in machine learning", 
                         mem_type="fact", importance=0.8)
    id3 = memory.remember("Deep learning uses neural networks", 
                         mem_type="fact", importance=0.8)
    
    # Create connections
    memory.relate(id1, id2, weight=1.0)
    memory.relate(id2, id3, weight=1.0)
    
    print(f"✓ Created memory chain: {id1} → {id2} → {id3}")
    
    # Recall should find related memories through graph
    results = memory.recall("AI concepts", limit=5, use_graph_traversal=True)
    
    print(f"✓ Found {len(results)} related memories:")
    for mem in results:
        print(f"  - {mem.content}")
    
    assert len(results) >= 2, "Graph traversal didn't find connected memories"
    print("✓ Graph traversal works")


async def test_memory_eviction():
    """Test 7: Memory eviction and persistence."""
    print("\n" + "="*60)
    print("TEST 7: Memory Eviction")
    print("="*60)
    
    memory = HybridMemory(TEST_DB)
    
    # Store many memories to trigger eviction
    print("Storing 120 memories to trigger eviction...")
    for i in range(120):
        memory.remember(
            f"Test memory number {i} with some content",
            mem_type="thought",
            importance=0.3 + (i / 1000)  # Varying importance
        )
    
    stats = memory.get_statistics()
    print(f"✓ Graph nodes: {stats['graph']['total_nodes']}")
    print(f"✓ DB memories: {stats['store']['total_memories']}")
    
    # Should have triggered eviction
    assert stats['graph']['total_nodes'] < 120, "Eviction didn't happen"
    assert stats['store']['total_memories'] > 0, "No memories persisted"
    print("✓ Memory eviction works")


async def test_fts_search():
    """Test 8: Full-text search capabilities."""
    print("\n" + "="*60)
    print("TEST 8: Full-Text Search")
    print("="*60)
    
    memory = HybridMemory(TEST_DB)
    
    # Store memories with related but different words
    memory.remember("I am running the tests now", mem_type="fact")
    memory.remember("The runner completed the marathon", mem_type="fact")
    memory.remember("Test execution is important", mem_type="fact")
    
    # Force persistence to SQLite
    memory._persist_old_memories()
    
    # Search with different word form (should match via stemming)
    results = memory.store.search_fts("run test")
    
    print(f"✓ FTS found {len(results)} matches for 'run test':")
    for mem in results:
        print(f"  - {mem.content}")
    
    # Should match "running" and "tests" via stemming
    assert len(results) >= 1, "FTS stemming didn't work"
    print("✓ Full-text search with stemming works")


async def test_performance():
    """Test 9: Performance benchmarks."""
    print("\n" + "="*60)
    print("TEST 9: Performance")
    print("="*60)
    
    memory = HybridMemory(TEST_DB)
    
    # Benchmark memory storage
    start = time.perf_counter()
    for i in range(100):
        memory.remember(f"Performance test {i}", mem_type="thought")
    storage_time = time.perf_counter() - start
    
    print(f"✓ Stored 100 memories in {storage_time:.3f}s")
    print(f"  Average: {storage_time/100*1000:.2f}ms per memory")
    
    # Benchmark recall
    start = time.perf_counter()
    for i in range(50):
        results = memory.recall(f"test {i}", limit=5)
    recall_time = time.perf_counter() - start
    
    print(f"✓ Performed 50 recalls in {recall_time:.3f}s")
    print(f"  Average: {recall_time/50*1000:.2f}ms per recall")
    
    # Performance assertions
    assert storage_time < 5.0, "Storage too slow"
    assert recall_time < 10.0, "Recall too slow"
    print("✓ Performance acceptable")


async def test_error_handling():
    """Test 10: Error handling and recovery."""
    print("\n" + "="*60)
    print("TEST 10: Error Handling")
    print("="*60)
    
    memory = HybridMemory(TEST_DB)
    agent = FastAgent(memory)
    
    # Test with invalid tool
    result = await agent.run(
        "Use the nonexistent_tool to do something",
        max_steps=3
    )
    
    print(f"✅ Handled invalid tool gracefully")
    
    # Test with malformed query
    result = await agent.run("", max_steps=1)
    print(f"✅ Handled empty query")
    
    await agent.cleanup()
    print("✓ Error handling works")


async def run_all_tests():
    """Run all tests in sequence."""
    print("\n" + "="*60)
    print("🧪 AGENT TEST SUITE")
    print("="*60)
    
    # Clean test database
    import os
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        print(f"Cleaned test database: {TEST_DB}\n")
    
    tests = [
        ("Basic Reasoning", test_basic_reasoning),
        ("Memory Persistence", test_memory_persistence),
        ("Web Search", test_web_search),
        ("Multi-Step Reasoning", test_multi_step_reasoning),
        ("Cross-Session Memory", test_cross_session_memory),
        ("Graph Traversal", test_graph_traversal),
        ("Memory Eviction", test_memory_eviction),
        ("Full-Text Search", test_fts_search),
        ("Performance", test_performance),
        ("Error Handling", test_error_handling),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {failed} test(s) failed")
    
    # Cleanup
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


if __name__ == "__main__":
    asyncio.run(run_all_tests())