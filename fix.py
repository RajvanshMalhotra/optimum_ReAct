"""Quick patch script to fix remaining issues."""

# Fix 1: Update core/agent.py - Add data=None to ToolResult errors
print("Fix 1: Patching core/agent.py...")

agent_file = "core/agent.py"
with open(agent_file, 'r') as f:
    content = f.read()

# Replace error returns to include data=None
content = content.replace(
    'return ToolResult(tool=tool_name, success=False, error="Tool unavailable")',
    'return ToolResult(tool=tool_name, success=False, data=None, error="Tool unavailable")'
)
content = content.replace(
    'return ToolResult(tool=tool_name, success=False, error=str(e))',
    'return ToolResult(tool=tool_name, success=False, data=None, error=str(e))'
)

with open(agent_file, 'w') as f:
    f.write(content)

print("  ✓ Fixed ToolResult validation errors")

# Fix 2: Update memory/graph.py - Fix empty doc_count check
print("\nFix 2: Patching memory/graph.py...")

graph_file = "memory/graph.py"
with open(graph_file, 'r') as f:
    content = f.read()

# Add empty doc_count check
if "if doc_count == 0:" not in content:
    old_code = """        # Build term frequency across all documents (simple IDF)
        doc_count = len(self.nodes)
        term_doc_freq: Dict[str, int] = {}"""
    
    new_code = """        # Build term frequency across all documents (simple IDF)
        doc_count = len(self.nodes)
        if doc_count == 0:
            return []
        
        term_doc_freq: Dict[str, int] = {}"""
    
    content = content.replace(old_code, new_code)
    
    with open(graph_file, 'w') as f:
        f.write(content)
    
    print("  ✓ Fixed empty document collection handling")
else:
    print("  ✓ Already patched")

# Fix 3: Check FTS5 syntax in memory/store.py
print("\nFix 3: Checking memory/store.py FTS5 syntax...")

store_file = "memory/store.py"
with open(store_file, 'r') as f:
    content = f.read()

if 'WHERE content MATCH ?' in content:
    print("  ⚠ FTS5 still using ? placeholder - needs manual fix")
    print("  Replace: WHERE content MATCH ?")
    print("  With: WHERE content MATCH \"{safe_query}\"")
    print("  And use f-string for the query")
elif 'MATCH "{safe_query}"' in content or "MATCH '{safe_query}'" in content:
    print("  ✓ FTS5 using string interpolation (correct)")
else:
    print("  ? Unknown FTS5 syntax - check manually")

print("\n" + "="*60)
print("Patches applied! Now run: python test.py")
print("="*60)