"""Optimized configuration for the autonomous agent."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure we load .env from the correct location
BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR / ".env"

# Load environment variables
load_dotenv(ENV_PATH)

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# LLM Configuration - OPTIMIZED
LLM_MODEL = "llama-3.3-70b-versatile"  # Fastest Groq model
LLM_BASE_URL = "https://api.groq.com/openai/v1"
LLM_MAX_TOKENS = 1000  # Reduced from 1500 (faster)
LLM_TEMPERATURE = 0.6  # Reduced from 0.7 (more focused)
LLM_TIMEOUT = 60.0  # Reduced from 90.0

# Memory Configuration - OPTIMIZED
MEMORY_MAX_GRAPH_NODES = 50  # Reduced from 100 (faster searches)
MEMORY_PERSIST_BATCH_SIZE = 10  # Reduced from 20 (smaller writes)
MEMORY_SEARCH_LIMIT = 2  # Reduced from 5 (faster recalls)

# Agent Configuration - OPTIMIZED
AGENT_MAX_STEPS = 8  # Reduced from 10 (faster convergence)

# Cache Configuration - NEW
CACHE_ENABLED = True
CACHE_MAX_SIZE = 100
CACHE_TTL = 3600  # 1 hour

# Parallel Execution - NEW
MAX_PARALLEL_TOOLS = 3  # Max tools to run concurrently

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

MEMORY_DB_PATH = DATA_DIR / "agent_memory.db"
LOG_FILE_PATH = DATA_DIR / "agent_logs.jsonl"

# Validate required keys
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment")