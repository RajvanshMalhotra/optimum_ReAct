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
