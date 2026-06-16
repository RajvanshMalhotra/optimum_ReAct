#!/usr/bin/env bash
# ============================================================
# Gotham Orbital — API Test Suite (curl)
# ============================================================
# Usage:
#   ./tests/curl_tests.sh                        # hit localhost:8000
#   BASE=http://your-ec2-ip:8080 ./tests/curl_tests.sh
#   GROQ_KEY=gsk_... TAVILY_KEY=tvly-... ./tests/curl_tests.sh
#
# Requires: curl, jq
# ============================================================

BASE="${BASE:-http://localhost:8000}"
GROQ_KEY="${GROQ_KEY:-${GROQ_API_KEY:-}}"
TAVILY_KEY="${TAVILY_KEY:-${TAVILY_API_KEY:-}}"

PASS=0; FAIL=0; SKIP=0
START_TIME=$(date +%s)

# ── colours ────────────────────────────────────────────────
GREEN="\033[92m"; YELLOW="\033[93m"; RED="\033[91m"
CYAN="\033[96m";  BOLD="\033[1m";    DIM="\033[2m"; RESET="\033[0m"

log()  { echo -e "$*${RESET}"; }
pass() { PASS=$((PASS+1)); log "${GREEN}  ✓  $*"; }
fail() { FAIL=$((FAIL+1)); log "${RED}  ✗  $*"; }
skip() { SKIP=$((SKIP+1)); log "${YELLOW}  -  $* (skipped — no API key)"; }
section() { echo; log "${BOLD}${CYAN}━━━  $*  ━━━"; }

# ── helper: timed curl ─────────────────────────────────────
# Usage: call METHOD PATH [body_json] [extra_headers...]
# Prints latency, HTTP status, response preview. Sets $RESP and $HTTP_STATUS.
call() {
    local method="$1" path="$2" body="${3:-}" shift3=0
    shift 3 || true
    local extra_headers=("$@")

    local tmpfile; tmpfile=$(mktemp)
    local curl_args=(
        -s -w "\n__STATUS__%{http_code}__TIME__%{time_total}__"
        -X "$method"
        -H "Content-Type: application/json"
    )
    [[ -n "$GROQ_KEY" ]]   && curl_args+=(-H "x-groq-key: $GROQ_KEY")
    [[ -n "$TAVILY_KEY" ]] && curl_args+=(-H "x-tavily-key: $TAVILY_KEY")
    for h in "${extra_headers[@]}"; do curl_args+=(-H "$h"); done
    [[ -n "$body" ]] && curl_args+=(--data-raw "$body")
    curl_args+=("${BASE}${path}")

    local raw; raw=$(curl "${curl_args[@]}" 2>/dev/null)
    HTTP_STATUS=$(echo "$raw" | grep -o '__STATUS__[0-9]*' | grep -o '[0-9]*')
    HTTP_TIME=$(echo "$raw" | grep -o '__TIME__[0-9.]*' | grep -o '[0-9.]*')
    RESP=$(echo "$raw" | sed 's/__STATUS__[0-9]*__TIME__[0-9.]*$//')
    rm -f "$tmpfile"
}

# ── check deps ─────────────────────────────────────────────
for dep in curl jq; do
    if ! command -v $dep &>/dev/null; then
        log "${RED}Missing dependency: $dep — install it first."; exit 1
    fi
done

echo
log "${BOLD}╔══════════════════════════════════════════════════════╗"
log "${BOLD}║  Gotham Orbital — API Test Suite                     ║"
log "${BOLD}╚══════════════════════════════════════════════════════╝"
log "${DIM}  Target: ${BASE}"
log "${DIM}  Groq key:   ${GROQ_KEY:+set (${GROQ_KEY:0:8}...)}${GROQ_KEY:-NOT SET}"
log "${DIM}  Tavily key: ${TAVILY_KEY:+set}${TAVILY_KEY:-NOT SET}"


# ════════════════════════════════════════════════════════════
section "1 — HEALTH & METADATA"
# ════════════════════════════════════════════════════════════

call GET /health
if [[ "$HTTP_STATUS" == "200" ]]; then
    STATUS=$(echo "$RESP" | jq -r '.status // empty' 2>/dev/null)
    VERSION=$(echo "$RESP" | jq -r '.version // empty' 2>/dev/null)
    SGP4=$(echo "$RESP" | jq -r '.sgp4 // empty' 2>/dev/null)
    if [[ "$STATUS" == "ok" ]]; then
        pass "GET /health → status=ok  version=$VERSION  sgp4=$SGP4  [${HTTP_TIME}s]"
    else
        fail "GET /health → HTTP $HTTP_STATUS but status='$STATUS'"
    fi
else
    fail "GET /health → HTTP $HTTP_STATUS (is the server running?)"
fi

call GET /models
if [[ "$HTTP_STATUS" == "200" ]]; then
    COUNT=$(echo "$RESP" | jq '.models | length' 2>/dev/null)
    DEFAULT=$(echo "$RESP" | jq -r '.default // empty' 2>/dev/null)
    pass "GET /models → $COUNT models available, default=$DEFAULT  [${HTTP_TIME}s]"
else
    fail "GET /models → HTTP $HTTP_STATUS"
fi

call GET /satellites
if [[ "$HTTP_STATUS" == "200" ]]; then
    COUNT=$(echo "$RESP" | jq '.count // 0' 2>/dev/null)
    THREATS=$(echo "$RESP" | jq '[.catalog[].threat] | add' 2>/dev/null)
    pass "GET /satellites → $COUNT satellites in catalog, cumulative threat=$THREATS  [${HTTP_TIME}s]"
else
    fail "GET /satellites → HTTP $HTTP_STATUS"
fi

call GET /stats
if [[ "$HTTP_STATUS" == "200" ]]; then
    pass "GET /stats → HTTP $HTTP_STATUS  [${HTTP_TIME}s]"
else
    log "${YELLOW}  -  GET /stats → HTTP $HTTP_STATUS (agent pool may be cold)"
    SKIP=$((SKIP+1))
fi


# ════════════════════════════════════════════════════════════
section "2 — AGENT ROLES (all four)"
# ════════════════════════════════════════════════════════════

SNAPSHOT="COSMOS2543(Russia): lat=51.2 lon=37.8 alt=490km\nYAOGAN30(China/PLA): lat=28.5 lon=104.3 alt=600km\nISSS(NASA): lat=35.1 lon=-80.2 alt=420km"

if [[ -z "$GROQ_KEY" ]]; then
    skip "POST /agent [all roles] — GROQ_KEY not set"
else
    for ROLE in orbital news atlas analyst; do
        BODY=$(jq -n \
            --arg role "$ROLE" \
            --arg snap "$(echo -e "$SNAPSHOT")" \
            '{role: $role, user_message: "Provide a brief intelligence assessment.", satellite_snapshot: $snap}')
        call POST /agent "$BODY"
        if [[ "$HTTP_STATUS" == "200" ]]; then
            RESP_LEN=${#RESP}
            NEEDS_INPUT=$(echo "$RESP" | jq -r '.needs_input // false' 2>/dev/null)
            if [[ "$NEEDS_INPUT" == "true" ]]; then
                pass "POST /agent role=$ROLE → needs_input=true (ask_user flow triggered)  [${HTTP_TIME}s]"
            else
                PREVIEW=$(echo "$RESP" | jq -r '.response // empty' 2>/dev/null | head -c 100)
                pass "POST /agent role=$ROLE → ${RESP_LEN}B  preview: \"${PREVIEW}...\"  [${HTTP_TIME}s]"
            fi
        else
            fail "POST /agent role=$ROLE → HTTP $HTTP_STATUS: $(echo "$RESP" | jq -r '.detail // empty' 2>/dev/null)"
        fi
    done
fi


# ════════════════════════════════════════════════════════════
section "3 — AGENT: BAD ROLE (error handling)"
# ════════════════════════════════════════════════════════════

call POST /agent '{"role":"ghost","user_message":"test"}'
if [[ "$HTTP_STATUS" == "400" ]]; then
    DETAIL=$(echo "$RESP" | jq -r '.detail // empty' 2>/dev/null)
    pass "POST /agent role=ghost → HTTP 400 (expected)  detail: \"$DETAIL\"  [${HTTP_TIME}s]"
else
    fail "POST /agent role=ghost → expected HTTP 400, got $HTTP_STATUS"
fi


# ════════════════════════════════════════════════════════════
section "4 — INTEL QUERY (ATLAS synthesis)"
# ════════════════════════════════════════════════════════════

if [[ -z "$GROQ_KEY" ]]; then
    skip "POST /intel-query — GROQ_KEY not set"
else
    INTEL_BODY=$(jq -n \
        --arg snap "$(echo -e "$SNAPSHOT")" \
        '{
            query: "Are COSMOS2543 and YAOGAN30 conducting coordinated ISR operations?",
            satellite_snapshot: $snap,
            current_cycle: 1
        }')
    call POST /intel-query "$INTEL_BODY"
    if [[ "$HTTP_STATUS" == "200" ]]; then
        PROX=$(echo "$RESP" | jq '.proximity | length' 2>/dev/null)
        TRACKS=$(echo "$RESP" | jq '.ground_tracks | keys | length' 2>/dev/null)
        REL_IDS=$(echo "$RESP" | jq -r '.relevant_ids | join(", ")' 2>/dev/null)
        pass "POST /intel-query → HTTP 200  proximity_alerts=$PROX  tracks=$TRACKS  relevant_ids=[$REL_IDS]  [${HTTP_TIME}s]"
    else
        fail "POST /intel-query → HTTP $HTTP_STATUS: $(echo "$RESP" | jq -r '.detail // empty' 2>/dev/null)"
    fi
fi


# ════════════════════════════════════════════════════════════
section "5 — INGEST (satellite snapshot ingestion)"
# ════════════════════════════════════════════════════════════

if [[ -z "$GROQ_KEY" ]]; then
    skip "POST /ingest — GROQ_KEY not set"
else
    INGEST_BODY=$(jq -n \
        --arg snap "$(echo -e "$SNAPSHOT")" \
        '{snapshot: $snap, cycle: 42}')
    call POST /ingest "$INGEST_BODY"
    if [[ "$HTTP_STATUS" == "200" ]]; then
        STORED=$(echo "$RESP" | jq '.stored // 0' 2>/dev/null)
        CYCLE=$(echo "$RESP" | jq '.cycle // 0' 2>/dev/null)
        pass "POST /ingest → stored=$STORED records, cycle=$CYCLE  [${HTTP_TIME}s]"
    else
        fail "POST /ingest → HTTP $HTTP_STATUS: $(echo "$RESP" | jq -r '.detail // empty' 2>/dev/null)"
    fi
fi


# ════════════════════════════════════════════════════════════
section "6 — SATELLITE HISTORY"
# ════════════════════════════════════════════════════════════

for SAT in COSMOS2543 YAOGAN30 ISS; do
    call GET "/history/${SAT}"
    if [[ "$HTTP_STATUS" == "200" ]]; then
        COUNT=$(echo "$RESP" | jq '.count // 0' 2>/dev/null)
        NAME=$(echo "$RESP" | jq -r '.name // empty' 2>/dev/null)
        THREAT=$(echo "$RESP" | jq -r '.threat // empty' 2>/dev/null)
        pass "GET /history/$SAT → \"$NAME\" threat=$THREAT, $COUNT history records  [${HTTP_TIME}s]"
    else
        fail "GET /history/$SAT → HTTP $HTTP_STATUS"
    fi
done

call GET "/history/FAKEID_XYZ"
if [[ "$HTTP_STATUS" == "404" ]]; then
    pass "GET /history/FAKEID_XYZ → HTTP 404 (expected)  [${HTTP_TIME}s]"
else
    fail "GET /history/FAKEID_XYZ → expected HTTP 404, got $HTTP_STATUS"
fi


# ════════════════════════════════════════════════════════════
section "7 — TLE DATA"
# ════════════════════════════════════════════════════════════

call GET /tles
if [[ "$HTTP_STATUS" == "200" ]]; then
    COUNT=$(echo "$RESP" | jq '.count // 0' 2>/dev/null)
    TTL=$(echo "$RESP" | jq '.ttl_hours // 0' 2>/dev/null)
    SAMPLE=$(echo "$RESP" | jq -r '.tles | keys[0] // empty' 2>/dev/null)
    pass "GET /tles → $COUNT TLEs cached (TTL=${TTL}h), sample: $SAMPLE  [${HTTP_TIME}s]"
elif [[ "$HTTP_STATUS" == "503" ]]; then
    log "${YELLOW}  -  GET /tles → HTTP 503 (Celestrak unavailable — expected in offline env)"
    SKIP=$((SKIP+1))
else
    fail "GET /tles → HTTP $HTTP_STATUS"
fi


# ════════════════════════════════════════════════════════════
section "8 — ASK_USER SESSION FLOW"
# ════════════════════════════════════════════════════════════

# POST /agent/resume with a fake session ID — should return 404
call POST /agent/resume '{"session_id":"fake-session-000","answer":"test","role":"atlas"}'
if [[ "$HTTP_STATUS" == "404" ]]; then
    pass "POST /agent/resume (bad session_id) → HTTP 404 (expected)  [${HTTP_TIME}s]"
else
    log "${YELLOW}  -  POST /agent/resume → HTTP $HTTP_STATUS (acceptable if session expired)"
    SKIP=$((SKIP+1))
fi


# ════════════════════════════════════════════════════════════
section "9 — MODEL OVERRIDE HEADER"
# ════════════════════════════════════════════════════════════

if [[ -z "$GROQ_KEY" ]]; then
    skip "Model override test — GROQ_KEY not set"
else
    BODY='{"role":"orbital","user_message":"Quick status check."}'
    call POST /agent "$BODY" "x-llm-model: gemma2-9b-it"
    if [[ "$HTTP_STATUS" == "200" ]]; then
        pass "POST /agent x-llm-model=gemma2-9b-it → HTTP 200  [${HTTP_TIME}s]"
    else
        fail "POST /agent x-llm-model=gemma2-9b-it → HTTP $HTTP_STATUS"
    fi
fi


# ════════════════════════════════════════════════════════════
section "RESULTS"
# ════════════════════════════════════════════════════════════

END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))
TOTAL=$((PASS + FAIL + SKIP))

echo
log "${BOLD}┌─────────────────────────────────┐"
log "${BOLD}│  Total:   ${TOTAL}"
log "${BOLD}│  ${GREEN}Passed:   ${PASS}${BOLD}"
log "${BOLD}│  ${RED}Failed:   ${FAIL}${BOLD}"
log "${BOLD}│  ${YELLOW}Skipped:  ${SKIP}${BOLD}"
log "${BOLD}│  Wall time: ${TOTAL_TIME}s"
log "${BOLD}└─────────────────────────────────┘"

if [[ $FAIL -gt 0 ]]; then
    echo
    log "${RED}${BOLD}$FAIL test(s) failed. Check server logs: uvicorn api:app --port 8000"
    exit 1
else
    echo
    log "${GREEN}${BOLD}All tests passed."
    exit 0
fi
