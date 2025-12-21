#!/bin/bash

START_DATE="2025-11-09"

declare -a COMMITS=(
  "memory/graph.py|add basic graph memory structure"
  "memory/store.py|implement initial memory store interface"
  "models/agent.py|scaffold agent class with core attributes"
  "models/memory.py|define base memory abstraction"
  "memory/hybrid.py|introduce hybrid memory placeholder"
  "memory/graph.py|add node linking logic"
  "models/agent.py|wire agent with memory dependency"
  "tools/__init__.py|expose tool interfaces"
  "memory/store.py|add simple in-memory backend"
  "models/memory.py|add read/write memory contracts"
  "memory/hybrid.py|combine graph and store strategies"
  "memory/graph.py|optimize traversal logic"
  "models/agent.py|add decision loop skeleton"
  "models/agent.py|refactor agent execution flow"
  "memory/store.py|handle memory overwrite cases"
  "models/memory.py|add basic validation checks"
  "memory/graph.py|add edge weighting support"
  "memory/hybrid.py|prioritize recent memories"
  "models/agent.py|add agent state tracking"
  "models/agent.py|minor cleanup and docstrings"
  "memory/store.py|add persistence hooks (stub)"
  "memory/graph.py|handle cyclic references"
  "models/memory.py|document memory lifecycle"
  "memory/hybrid.py|improve fallback strategy"
  "models/agent.py|add TODOs for planning module"
  "memory/store.py|refactor storage API naming"
  "memory/graph.py|simplify node lookup"
  "models/memory.py|tighten memory interface"
  "models/agent.py|add logging hooks"
  "memory/hybrid.py|tune memory merge logic"
  "memory/store.py|add lightweight caching"
  "models/agent.py|finalize agent init flow"
  "memory/graph.py|add comments for future optimizations"
  "models/memory.py|cleanup unused imports"
  "models/agent.py|stabilize agent-memory interaction"
  "README.md|document agent memory architecture"
)

DAY=0

for entry in "${COMMITS[@]}"; do
  FILE="${entry%%|*}"
  MSG="${entry##*|}"

  COMMIT_DATE=$(date -j -v+${DAY}d -f "%Y-%m-%d" "$START_DATE" "+%Y-%m-%d")
  HOUR=$((RANDOM % 4 + 11))
  MIN=$((RANDOM % 60))

  echo "# ${MSG} (${COMMIT_DATE})" >> "$FILE"

  git add "$FILE"

  GIT_AUTHOR_DATE="$COMMIT_DATE ${HOUR}:${MIN}:00" \
  GIT_COMMITTER_DATE="$COMMIT_DATE ${HOUR}:${MIN}:00" \
  git commit -m "$MSG"

  DAY=$((DAY + 1))
done
