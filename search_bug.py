"""Debug Tavily API key loading."""
import os
import sys

print("="*80)
print("TAVILY API KEY DIAGNOSTIC")
print("="*80)

# Check 1: Environment variable
print("\n1. Checking environment variable...")
tavily_key = os.getenv("TAVILY_API_KEY")
if tavily_key:
    print(f"   ✓ TAVILY_API_KEY found: {tavily_key[:10]}..." if len(tavily_key) > 10 else f"   ✓ TAVILY_API_KEY found: {tavily_key}")
else:
    print("   ✗ TAVILY_API_KEY not found in environment")

# Check 2: .env file
print("\n2. Checking .env file...")
if os.path.exists(".env"):
    print("   ✓ .env file exists")
    with open(".env", 'r') as f:
        lines = f.readlines()
        tavily_lines = [l for l in lines if "TAVILY" in l.upper()]
        if tavily_lines:
            print(f"   ✓ Found Tavily entries in .env:")
            for line in tavily_lines:
                print(f"      {line.strip()}")
        else:
            print("   ✗ No TAVILY entries in .env file")
else:
    print("   ✗ .env file does not exist")

# Check 3: Load with python-dotenv
print("\n3. Testing python-dotenv...")
try:
    from dotenv import load_dotenv
    print("   ✓ python-dotenv is installed")
    
    load_dotenv()
    tavily_after_load = os.getenv("TAVILY_API_KEY")
    if tavily_after_load:
        print(f"   ✓ After load_dotenv(): {tavily_after_load[:10]}...")
    else:
        print("   ✗ Still not found after load_dotenv()")
except ImportError:
    print("   ✗ python-dotenv not installed")
    print("      Run: pip install python-dotenv")

# Check 4: SearchTool initialization
print("\n4. Testing SearchTool...")
try:
    from tools.search_tool import SearchTool
    
    # Try to create instance
    try:
        tool = SearchTool()
        print("   ✓ SearchTool initialized successfully!")
    except ValueError as e:
        print(f"   ✗ SearchTool initialization failed: {e}")
    except ImportError as e:
        print(f"   ✗ Import error: {e}")
        print("      Run: pip install tavily-python")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Check 5: Tool registry
print("\n5. Checking tool registry...")
try:
    from tools.registry import tool_registry
    
    if tool_registry.has_tool("web_search"):
        print("   ✓ web_search tool is registered")
    else:
        print("   ✗ web_search tool is NOT registered")
        print("      Available tools:", list(tool_registry._tools.keys()))
except Exception as e:
    print(f"   ✗ Error: {e}")

# Recommendations
print("\n" + "="*80)
print("RECOMMENDATIONS:")
print("="*80)

if not tavily_key and not tavily_after_load:
    print("\n❌ TAVILY_API_KEY is not set. Try one of these:")
    print("\nOption 1 - Export in terminal:")
    print('   export TAVILY_API_KEY="tvly-your-key-here"')
    print('   python final_test.py')
    
    print("\nOption 2 - Add to .env file:")
    print('   echo \'TAVILY_API_KEY=tvly-your-key-here\' >> .env')
    print('   python final_test.py')
    
    print("\nOption 3 - Set in code (config.py):")
    print('   import os')
    print('   os.environ["TAVILY_API_KEY"] = "tvly-your-key-here"')
    
    print("\n🔑 Get a free API key at: https://tavily.com")

elif tavily_key or tavily_after_load:
    print("\n✅ API key is set correctly!")
    print("   If tests still show 'not available', check SearchTool initialization above.")

print("="*80)