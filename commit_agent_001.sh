#!/bin/bash

FOLDER="agent_001"
START_DATE="2025-11-09"
DAY_OFFSET=0

for FILE in "$FOLDER"/*; do
    if [ -f "$FILE" ]; then
        COMMIT_DATE=$(date -j -v+"$DAY_OFFSET"d -f "%Y-%m-%d" "$START_DATE" "+%Y-%m-%dT10:00:00")
        git add "$FILE"
        GIT_AUTHOR_DATE="$COMMIT_DATE" GIT_COMMITTER_DATE="$COMMIT_DATE" git commit -m "Add $(basename "$FILE")"
        echo "Committed $(basename "$FILE") on $COMMIT_DATE"
        DAY_OFFSET=$((DAY_OFFSET + 1))
    fi
done
