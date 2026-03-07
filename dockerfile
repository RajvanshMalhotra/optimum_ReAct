# optimum_ReAct API — Dockerfile
# Build:  docker build -t optimum-react-api .
# Run:    docker run -p 8000:8000 --env-file .env -v $(pwd)/data:/app/data optimum-react-api

FROM python:3.11-slim

# System deps for numpy / sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Install Python deps ───────────────────────────────────────────────────────
# Copy requirements first so Docker layer-caches them
COPY requirements.txt .

# sentence-transformers pulls PyTorch (~1.5GB) — this step takes a while on first build.
# If you want a lighter image (BM25 keyword search only, no semantic search),
# comment out sentence-transformers and faiss-cpu in requirements.txt before building.
RUN pip install --no-cache-dir -r requirements.txt

# FastAPI + uvicorn (not in your requirements.txt, adding here)
RUN pip install --no-cache-dir fastapi uvicorn[standard]

# ── Copy project ──────────────────────────────────────────────────────────────
COPY . .

# Data directory for SQLite DB
# The host mounts its own data/ folder here via -v $(pwd)/data:/app/data
# so the DB persists across container restarts
RUN mkdir -p /app/data

# ── Environment defaults ──────────────────────────────────────────────────────
# Override these in .env or ECS task definition — do NOT hardcode real keys here
ENV AGENT_DB_PATH=/app/data/gotham_agent.db
ENV PORT=8000

# AWS ALB health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

EXPOSE ${PORT}

# 2 workers is right for t2.micro (1 vCPU, 1GB RAM)
# Increase to 4 on t3.small or larger
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT} --workers 2"]