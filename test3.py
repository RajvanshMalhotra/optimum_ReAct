# import asyncio
# import os
# from memory.hybrid import HybridMemory
# from core.agent import FastAgent

# from dotenv import load_dotenv
# load_dotenv()

# # Import tools to auto-register them
# import tools  # This line is important!

# memory = HybridMemory("agent.db")
# agent = FastAgent(memory)
# while(input!="exit"):
#     user_input = input("Enter your task: ")

#     # Use asyncio.run() to run the async function
#     output = asyncio.run(agent.run(user_input, max_steps=5))

#     print("\n" + "="*60)
#     print("RESULT:")
#     print("="*60)
#     print(output)
#     print("="*60)
#     continue_prompt = input("Type 'exit' to quit or press Enter to continue: ")
#     if continue_prompt.lower() == 'exit':
#         break


# # Cleanup
# asyncio.run(agent.cleanup())

"""Test search agent with flight queries."""
import asyncio
import os
from memory.hybrid import HybridMemory
from core.agent import FastAgent


async def test_flight_search():
    """Test flight search with proper result usage."""
    print("\n" + "="*80)
    print("TESTING FLIGHT SEARCH AGENT")
    print("="*80)
    
    # Clean test database
    test_db = "test_search.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Initialize agent
    memory = HybridMemory(test_db)
    agent = FastAgent(memory)
    
    # Test query
    task = "Find cheap flights from Delhi to Bali for tomorrow"
    
    print(f"\nTask: {task}")
    print("-" * 80)
    
    try:
        result = await agent.run(task, max_steps=8)
        
        print("\n" + "="*80)
        print("RESULT")
        print("="*80)
        print(result)
        print("="*80)
        
        # Validate result
        checks = {
            "Contains price": any(symbol in result for symbol in ["₹", "$", "Rs"]),
            "Contains Bali": "bali" in result.lower(),
            "Contains airline": any(airline in result.lower() for airline in ["indigo", "air india", "spicejet", "vistara", "airasia"]),
            "Contains link": "http" in result.lower() or "www." in result.lower(),
            "NOT about Goa": "goa" not in result.lower()
        }
        
        print("\n" + "="*80)
        print("VALIDATION")
        print("="*80)
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")
        
        all_passed = all(checks.values())
        if all_passed:
            print("\n🎉 ALL CHECKS PASSED - Agent working correctly!")
        else:
            print("\n⚠️  Some checks failed - review output above")
        
    finally:
        await agent.cleanup()
        if os.path.exists(test_db):
            os.remove(test_db)


async def test_multi_query():
    """Test multiple different search queries."""
    print("\n" + "="*80)
    print("TESTING MULTIPLE QUERIES")
    print("="*80)
    
    test_db = "test_multi.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    queries = [
        "What is the current Bitcoin price?",
        "Find the weather in Mumbai today",
        "Search for best laptops for programming in 2024"
    ]
    
    memory = HybridMemory(test_db)
    agent = FastAgent(memory)
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*80}")
        print(f"Query {i}: {query}")
        print("-" * 80)
        
        try:
            result = await agent.run(query, max_steps=6)
            print(f"\nResult: {result[:200]}...")
            print("✅ Query completed")
        except Exception as e:
            print(f"❌ Query failed: {e}")
    
    await agent.cleanup()
    if os.path.exists(test_db):
        os.remove(test_db)


async def interactive_test():
    """Interactive testing mode."""
    print("\n" + "="*80)
    print("INTERACTIVE SEARCH AGENT TEST")
    print("="*80)
    print("Type your queries. Type 'exit' to quit.")
    print("-" * 80)
    
    test_db = "test_interactive.db"
    memory = HybridMemory(test_db)
    agent = FastAgent(memory)
    
    try:
        while True:
            query = input("\n\033[96mEnter your task:\033[0m ")
            
            if query.lower() in ['exit', 'quit', 'q']:
                break
            
            if not query.strip():
                continue
            
            try:
                result = await agent.run(query, max_steps=8)
                
                print("\n" + "="*80)
                print("RESULT:")
                print("="*80)
                print(result)
                print("="*80)
                
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
    
    finally:
        await agent.cleanup()
        if os.path.exists(test_db):
            os.remove(test_db)


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("🧪 SEARCH AGENT TEST SUITE")
    print("="*80)
    
    # Test 1: Flight search (main test)
    await test_flight_search()
    
    # Test 2: Multiple queries (optional)
    print("\n\nPress Enter to test multiple queries, or Ctrl+C to skip...")
    try:
        input()
        await test_multi_query()
    except KeyboardInterrupt:
        print("\nSkipped")
    
    # Test 3: Interactive mode (optional)
    print("\n\nPress Enter for interactive mode, or Ctrl+C to exit...")
    try:
        input()
        await interactive_test()
    except KeyboardInterrupt:
        print("\nExiting")
    
    print("\n" + "="*80)
    print("TESTS COMPLETE")
    print("="*80)


if __name__ == "__main__":
    # Quick test mode - just run flight search
    import sys
    
    if "--quick" in sys.argv:
        asyncio.run(test_flight_search())
    elif "--interactive" in sys.argv:
        asyncio.run(interactive_test())
    else:
        asyncio.run(main())