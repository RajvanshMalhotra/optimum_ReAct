# 👾  EZAgent Complete tutorial 
## Simple Frame work for Building AI Agents
Tired of langchain and endless courses on youtube and udemy, want full control? 
all prayers have been answered,this framework exactly does that, no unneccesary confusion hassle to setup.
faster and more logical answers and  opensource guess it's christmas 🎄 like every time of the year!

## 1. Getting Started

### Installation
```bash
pip -r install requirements.txt
```

### Setup Environment
```bash
# Create .env file
echo 'GROQ_API_KEY=your_groq_key_here' > .env
echo 'TAVILY_API_KEY=your_tavily_key_here' >> .env
```

### Import and Create Agent
```python
from AgenT import EZAgent

# Create agent with default database
agent = EZAgent()

# Or with custom database name
agent = EZAgent("my_agent.db")
```

---

## 2. Basic Operations

### Ask Questions (Main Function)
```python
# Simple question
answer = agent.ask("What is the capital of France?")
print(answer)

# Complex task
answer = agent.ask("Find cheap flights from Delhi to Bali for tomorrow")
print(answer)

# With custom step limit
answer = agent.ask("Complex research task", max_steps=15)
```

### Store Information
```python
# Store a fact (default importance: 0.8)
agent.remember("My name is Alex")

# Store with custom importance (0.0 to 1.0)
agent.remember("Critical password: abc123", importance=1.0)
agent.remember("Random note", importance=0.3)
```

### Retrieve Information
```python
# Search memories
memories = agent.recall("my name")
for memory in memories:
    print(memory)

# Get more results
memories = agent.recall("search term", limit=10)

# Get fewer results
memories = agent.recall("quick search", limit=3)
```

### Get Statistics
```python
# Get memory statistics
stats = agent.stats()

print(f"Session ID: {stats['session_id']}")
print(f"Memories created this session: {stats['session_memory_count']}")
print(f"Memories in RAM: {stats['graph']['total_nodes']}")
print(f"Memories in database: {stats['store']['total_memories']}")
print(f"Total sessions: {stats['store']['total_sessions']}")
```

---

## 3. Memory Management

### Clear Current Session
```python
# Start fresh (keeps database intact)
agent.clear_session()
print("Started new session, old memories still in database")
```

### Delete Old Memories
```python
# Access the underlying memory system
memory = agent.memory

# Remove memories older than 30 days
deleted = memory.cleanup_old_data(days=30)
print(f"Deleted {deleted} old memories")

# More aggressive cleanup (7 days)
deleted = memory.cleanup_old_data(days=7)
```

### Complete Reset
```python
import os

# Delete entire database
db_path = agent.memory.store.db_path
agent = None  # Close agent first
os.remove(db_path)
print("Database completely deleted")

# Create new agent
agent = EZAgent("fresh_start.db")
```

---

## 4. Advanced Operations

### Async Operations
```python
import asyncio

async def main():
    agent = EZAgent()
    
    # Async ask
    result = await agent.ask_async("What is Bitcoin price?")
    print(result)
    
    # Multiple concurrent queries
    tasks = [
        agent.ask_async("What is 10 + 20?"),
        agent.ask_async("What is 5 * 8?"),
        agent.ask_async("What is 100 / 4?")
    ]
    results = await asyncio.gather(*tasks)
    for i, result in enumerate(results, 1):
        print(f"Result {i}: {result}")
    
    await agent.cleanup()

asyncio.run(main())
```

### Access Memory Directly
```python
# Get the underlying HybridMemory object
memory = agent.memory

# Store with full control
memory_id = memory.remember(
    content="Detailed information",
    mem_type="fact",           # fact, thought, preference, tool_output
    importance=0.9,
    metadata={"category": "work", "date": "2024-12-26"}
)

# Create memory connections
id1 = memory.remember("Python is a programming language")
id2 = memory.remember("Python is used for AI")
memory.relate(id1, id2, weight=1.0)

# Get related memories
related = memory.graph.get_related(id1, depth=2, limit=5)
for node in related:
    print(node.content)
```

### Query Sessions
```python
memory = agent.memory

# Find similar past sessions
sessions = memory.store.find_similar_sessions("flight search", limit=5)
for session in sessions:
    print(f"Session: {session['task']}")
    print(f"Duration: {session['duration']}s")
    print(f"Result: {session['result'][:100]}...")
    print()
```

---

## 5. Complete Examples

### Example 1: Personal Assistant
```python
from AgenT import EZAgent

# Create personal assistant
assistant = EZAgent("personal_assistant.db")

# Store personal info
assistant.remember("I work at Tech Corp as a software engineer")
assistant.remember("My favorite programming language is Python")
assistant.remember("I prefer dark mode interfaces")

# Ask for personalized help
result = assistant.ask("""
    Suggest 3 side project ideas that match my skills and preferences
""")
print(result)

# Query stored info
memories = assistant.recall("work preferences")
print("What I know about you:")
for mem in memories:
    print(f"- {mem}")
```

### Example 2: Research Assistant
```python
from AgenT import EZAgent

researcher = EZAgent("research_assistant.db")

# Research task
result = researcher.ask("""
    Find the top 3 AI breakthroughs in 2024 and summarize each
""", max_steps=12)
print(result)

# Store findings
researcher.remember(result, importance=0.9)

# Later - recall research
past_research = researcher.recall("AI breakthroughs 2024")
print("Previous research:")
for research in past_research:
    print(research)
```

### Example 3: Conversation Bot
```python
from AgenTimport EZAgent

bot = EZAgent("chatbot.db")

# Conversation loop
print("Chat with the bot (type 'exit' to quit)")
while True:
    user_input = input("\nYou: ")
    if user_input.lower() in ['exit', 'quit']:
        break
    
    # Remember user messages
    bot.remember(f"User said: {user_input}", importance=0.7)
    
    # Get response
    response = bot.ask(user_input, max_steps=5)
    print(f"Bot: {response}")
```

### Example 4: Data Analysis Helper
```python
from AgenT import EZAgent

analyzer = EZAgent("data_analyzer.db")

# Store dataset info
analyzer.remember("Dataset: sales_2024.csv with 50k rows")
analyzer.remember("Columns: date, product, quantity, revenue, region")

# Ask for analysis
result = analyzer.ask("""
    What kind of analysis would be useful for this sales dataset?
    Suggest 5 specific analysis tasks.
""")
print(result)

# Get recommendations
recommendations = analyzer.recall("analysis")
print("\nSaved recommendations:")
for rec in recommendations:
    print(f"- {rec}")
```

### Example 5: Learning Assistant
```python
from AgenT import EZAgent

tutor = EZAgent("learning_assistant.db")

# Learning session
topics = [
    "Explain neural networks in simple terms",
    "How do transformers work?",
    "What is reinforcement learning?"
]

for topic in topics:
    print(f"\n{'='*60}")
    print(f"Topic: {topic}")
    print('='*60)
    
    explanation = tutor.ask(topic, max_steps=5)
    print(explanation)
    
    # Store for review
    tutor.remember(f"Learned: {topic}", importance=0.8)

# Review what was learned
learned = tutor.recall("learned")
print("\n\nTopics covered:")
for item in learned:
    print(f"✓ {item}")
```

---

## 6. Database Operations

### Export All Memories
```python
import json

agent = EZAgent("my_agent.db")

# Get all memories through recall
all_memories = agent.recall("", limit=1000)  # Empty query returns all

# Export to JSON
export_data = {
    "export_date": "2024-12-26",
    "total_memories": len(all_memories),
    "memories": all_memories
}

with open("memories_backup.json", "w") as f:
    json.dump(export_data, f, indent=2)

print(f"Exported {len(all_memories)} memories")
```

### Import Memories
```python
import json

agent = EZAgent("my_agent.db")

# Load from JSON
with open("memories_backup.json", "r") as f:
    data = json.load(f)

# Import each memory
for memory_text in data["memories"]:
    agent.remember(memory_text, importance=0.7)

print(f"Imported {len(data['memories'])} memories")
```

### Inspect Database
```python
import sqlite3

# Direct database access
conn = sqlite3.connect("my_agent.db")
cursor = conn.cursor()

# Count memories
cursor.execute("SELECT COUNT(*) FROM memories")
count = cursor.fetchone()[0]
print(f"Total memories: {count}")

# Get memory types
cursor.execute("SELECT type, COUNT(*) FROM memories GROUP BY type")
types = cursor.fetchall()
print("\nMemory types:")
for mem_type, count in types:
    print(f"  {mem_type}: {count}")

# Get high-importance memories
cursor.execute("SELECT content FROM memories WHERE importance > 0.8")
important = cursor.fetchall()
print("\nHigh importance memories:")
for (content,) in important:
    print(f"  - {content[:60]}...")

conn.close()
```

---

## 7. Error Handling

### Basic Error Handling
```python
from AgenT import EZAgent

agent = EZAgent()

try:
    result = agent.ask("Your task here", max_steps=10)
    print(result)
except Exception as e:
    print(f"Error: {e}")
    # Handle error appropriately
```

### Robust Implementation
```python
from AgenT import EZAgent
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

class SafeAgent:
    def __init__(self, db_path="agent.db"):
        try:
            self.agent = EZAgent(db_path)
            logging.info(f"Agent initialized with {db_path}")
        except Exception as e:
            logging.error(f"Failed to initialize agent: {e}")
            raise
    
    def ask(self, query, max_steps=10, retries=3):
        """Ask with automatic retries."""
        for attempt in range(retries):
            try:
                result = self.agent.ask(query, max_steps=max_steps)
                return result
            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == retries - 1:
                    return f"Failed after {retries} attempts: {e}"
        return None

# Use safe agent
safe_agent = SafeAgent()
result = safe_agent.ask("What is Python?")
print(result)
```

---

## 8. Best Practices

### Practice 1: Descriptive Database Names
```python
# Bad
agent = EZAgent("db.db")

# Good
agent = EZAgent("customer_support_bot.db")
agent = EZAgent("personal_assistant_2024.db")
agent = EZAgent("research_helper_ml.db")
```

### Practice 2: Set Appropriate Importance
```python
agent = EZAgent()

# Critical information
agent.remember("Database password: xyz123", importance=1.0)

# User preferences
agent.remember("User prefers dark mode", importance=0.9)

# General facts
agent.remember("Python was created in 1991", importance=0.7)

# Temporary notes
agent.remember("Checked this at 3pm", importance=0.3)
```

### Practice 3: Use Meaningful Queries
```python
# Bad - too vague
memories = agent.recall("stuff")

# Good - specific
memories = agent.recall("user preferences dark mode")
memories = agent.recall("password database credentials")
memories = agent.recall("meeting notes 2024")
```

### Practice 4: Regular Cleanup
```python
agent = EZAgent("my_agent.db")

# Weekly cleanup routine
def weekly_cleanup():
    # Remove old low-priority memories
    deleted = agent.memory.cleanup_old_data(days=7)
    print(f"Cleaned up {deleted} old memories")
    
    # Check stats
    stats = agent.stats()
    print(f"Current memories: {stats['total_memories']}")
    
    if stats['total_memories'] > 10000:
        print("Warning: Database getting large, consider archiving")

weekly_cleanup()
```

### Practice 5: Backup Before Reset
```python
import shutil
from datetime import datetime

agent = EZAgent("production.db")

# Backup before major operations
backup_name = f"production_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
shutil.copy("production.db", backup_name)
print(f"Backup created: {backup_name}")

# Now safe to do cleanup or reset
agent.clear_session()
```

---

## 9. Quick Reference

### One-Liners
```python
from AgenT import EZAgent

# Create and use
print(EZAgent().ask("What is AI?"))

# Create, remember, recall
agent = EZAgent(); agent.remember("Fact"); print(agent.recall("Fact"))

# Quick stats
print(EZAgent("my.db").stats())
```

### Common Patterns
```python
# Pattern: Store and retrieve
agent = EZAgent()
agent.remember("Important fact")
facts = agent.recall("Important")

# Pattern: Multi-step task
result = agent.ask("Complex task", max_steps=15)

# Pattern: Session management
stats = agent.stats()
if stats['session_memory_count'] > 100:
    agent.clear_session()

# Pattern: Cleanup old data
deleted = agent.memory.cleanup_old_data(days=30)
```

---

## 10. Complete API Summary

```python
from AgenT import EZAgent

# Create
agent = EZAgent()                    # Default database
agent = EZAgent("custom.db")         # Custom database

# Ask (Main function)
result = agent.ask("Task")           # Basic
result = agent.ask("Task", max_steps=15)  # Custom steps

# Memory
agent.remember("Fact")               # Store (default importance)
agent.remember("Fact", importance=0.9)    # Store with importance
memories = agent.recall("Query")     # Retrieve (default limit=5)
memories = agent.recall("Query", limit=10)  # Custom limit

# Stats
stats = agent.stats()                # Get statistics

# Management  
agent.clear_session()                # New session, keep DB

# Advanced
await agent.ask_async("Task")        # Async version
await agent.cleanup()                # Close resources
memory = agent.memory                # Access underlying memory

# Cleanup
deleted = agent.memory.cleanup_old_data(days=30)  # Delete old
```

---

## 11. Troubleshooting

### Problem: "GROQ_API_KEY not found"
```bash
# Solution: Set environment variable
echo 'GROQ_API_KEY=your_key_here' > .env
```

### Problem: "Agent too slow"
```python
# Solution: Reduce max_steps
agent.ask("Task", max_steps=5)  # Instead of default 10
```

### Problem: "Too many memories"
```python
# Solution: Regular cleanup
agent.memory.cleanup_old_data(days=7)
```

### Problem: "Database locked"
```python
# Solution: Close agent properly
await agent.cleanup()
```

---

## 12. Resources

### Get API Keys
- **GROQ API**: https://console.groq.com (Free tier available)
- **Tavily API**: https://tavily.com (500 free searches/month)

### Documentation
- Agent source: `core/agent.py`
- Memory system: `memory/hybrid.py`
- Tools: `tools/`
- Examples: `ez_agent.py`

### Support
- Issues: Check error messages
- Debugging: Enable logging with `logging.basicConfig(level=logging.DEBUG)`
- Testing: Run `python test_search.py --quick`

---

**That's everything you need to use the AgenT framework hope it's EZ!**
