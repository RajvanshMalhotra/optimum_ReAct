"""
optimum_ReAct — Palantir-style Fused Intelligence Backend
===========================================================
Frontend : Vercel (gotham-v2.jsx)
Backend  : AWS EC2 (this file)

WHAT THIS DOES:
  1. Stores satellite position history every cycle into SQLite via HybridMemory
  2. On NL query — runs THREE things concurrently:
       a. Recalls movement history from HybridMemory (where has it been?)
       b. Searches live news via Tavily (what's happening geopolitically?)
       c. Checks proximity alerts (are military sats converging?)
  3. Fuses all three into one enriched prompt → EZAgent reasons like a
     senior intel analyst, correlating movement patterns with news context

FLOW:
  Frontend POST /ingest every cycle  →  positions stored to SQLite
  User types query → POST /intel-query
    → recall history + Tavily search (concurrent)
    → fused prompt → ATLAS agent response
    → frontend highlights relevant satellites on map

ENV (.env on EC2, never committed):
  GROQ_API_KEY=gsk_...
  TAVILY_API_KEY=tvly_...

FRONTEND CHANGES NEEDED (2 edits in gotham-v2.jsx):

  1. Add to end of runCycle() to store history every cycle:
       const BACKEND_URL = "http://<your-ec2-ip>:8000";
       fetch(`${BACKEND_URL}/ingest`, {
         method: "POST",
         headers: {"Content-Type":"application/json"},
         body: JSON.stringify({snapshot: snap, cycle: cycle})
       }).catch(()=>{});   // fire-and-forget, don't block UI

  2. Replace handleNL() fetch with:
       const r = await fetch(`${BACKEND_URL}/intel-query`, {
         method: "POST",
         headers: {"Content-Type":"application/json"},
         body: JSON.stringify({query: nlQuery, satellite_snapshot: snap})
       });
       const d = await r.json();
       setNlResult(d.response);
       setHl(d.relevant_ids);
"""

import os
import re
import math
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from AgenT import EZAgent

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s"
)
log = logging.getLogger("akvani-api")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AkashVani Orbital — Fused Intelligence API",
    description="Palantir-style satellite movement history + live news fusion via optimum_ReAct",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to your Vercel URL after first deploy
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH       = os.getenv("AGENT_DB_PATH", "data/akvani_agent.db")
TAVILY_KEY    = os.getenv("TAVILY_API_KEY", "")
TAVILY_URL    = "https://api.tavily.com/search"
MAX_NEWS      = 4       # max Tavily results per query
PROXIMITY_KM  = 500     # alert if two military/intel sats within this distance

os.makedirs(
    os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".",
    exist_ok=True
)

# ── Satellite catalog — mirrors SAT_CATALOG in gotham-v2.jsx exactly ─────────
SAT_CATALOG = [
    {"id": "ISS",        "name": "ISS (ZARYA)",     "owner": "NASA/Roscosmos", "threat": 0, "type": "civilian"   },
    {"id": "TIANGONG",   "name": "CSS Tiangong",     "owner": "CNSA",           "threat": 1, "type": "military"   },
    {"id": "NOAA19",     "name": "NOAA-19",          "owner": "NOAA",           "threat": 0, "type": "weather"    },
    {"id": "TERRA",      "name": "Terra EOS AM-1",   "owner": "NASA",           "threat": 0, "type": "science"    },
    {"id": "AQUA",       "name": "Aqua EOS PM-1",    "owner": "NASA",           "threat": 0, "type": "science"    },
    {"id": "SENTINEL2B", "name": "Sentinel-2B",      "owner": "ESA",            "threat": 0, "type": "observation"},
    {"id": "STARLINK30", "name": "Starlink-1007",    "owner": "SpaceX",         "threat": 0, "type": "commercial" },
    {"id": "STARLINK31", "name": "Starlink-2341",    "owner": "SpaceX",         "threat": 0, "type": "commercial" },
    {"id": "IRIDIUM140", "name": "IRIDIUM-140",      "owner": "Iridium",        "threat": 0, "type": "commercial" },
    {"id": "GPS001",     "name": "GPS IIF-2",        "owner": "USAF",           "threat": 1, "type": "navigation" },
    {"id": "GLONASS",    "name": "GLONASS-M 730",    "owner": "Russia",         "threat": 1, "type": "navigation" },
    {"id": "COSMOS2543", "name": "COSMOS-2543",      "owner": "Russia",         "threat": 3, "type": "military"   },
    {"id": "YAOGAN30",   "name": "YAOGAN-30F",       "owner": "China/PLA",      "threat": 2, "type": "military"   },
    {"id": "LACROSSE5",  "name": "USA-182",          "owner": "NRO",            "threat": 2, "type": "intel"      },
]
THREAT_LABELS = ["NOMINAL", "MONITOR", "ELEVATED", "CRITICAL"]
VALID_IDS     = {s["id"] for s in SAT_CATALOG}
SAT_BY_ID     = {s["id"]: s for s in SAT_CATALOG}


# ── Agent singleton ───────────────────────────────────────────────────────────
_agent: Optional[EZAgent] = None
_lock  = asyncio.Lock()

async def get_agent() -> EZAgent:
    global _agent
    async with _lock:
        if _agent is None:
            log.info(f"Initializing EZAgent — DB: {DB_PATH}")
            _agent = EZAgent(DB_PATH)
            log.info("EZAgent ready")
    return _agent


# ── Geo helpers ───────────────────────────────────────────────────────────────
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    R    = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a    = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def ground_region(lat: float, lon: float) -> str:
    """Map lat/lon to a region label — matches the frontend hotspot zones."""
    if   lat >  35 and  -10 < lon <  40:             return "EUROPE"
    elif lat >  25 and -130 < lon < -60:              return "N.AMERICA"
    elif lat >  45 and   40 < lon < 180:              return "RUSSIA"
    elif  15 < lat <  55 and  70 < lon < 135:         return "CHINA"
    elif   5 < lat <  35 and  65 < lon <  90:         return "INDIA"
    elif  15 < lat <  42 and  25 < lon <  65:         return "MIDEAST"
    elif -35 < lat <  35 and -20 < lon <  55:         return "AFRICA"
    elif -55 < lat <  15 and -85 < lon < -35:         return "S.AMERICA"
    elif -45 < lat < -10 and 110 < lon < 155:         return "AUSTRALIA"
    elif  30 < lat <  50 and 125 < lon < 150:         return "JAPAN/KOREA"
    elif  35 < lat <  47 and  26 < lon <  45:         return "UKRAINE/BLACK SEA"
    elif  lat > 65:                                   return "ARCTIC"
    elif  lat < -60:                                  return "ANTARCTIC"
    else:                                             return "OPEN OCEAN"


# ── Tavily news search ────────────────────────────────────────────────────────
async def search_news(query: str) -> list[dict]:
    """
    Search Tavily for live geopolitical/satellite news.
    Fails gracefully — never blocks the agent response.
    """
    if not TAVILY_KEY:
        log.warning("TAVILY_API_KEY not set — skipping news search")
        return []
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                TAVILY_URL,
                json={
                    "api_key":        TAVILY_KEY,
                    "query":          query,
                    "search_depth":   "basic",
                    "max_results":    MAX_NEWS,
                    "include_answer": False,
                },
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            return [
                {
                    "title":   r.get("title", ""),
                    "url":     r.get("url", ""),
                    "snippet": r.get("content", "")[:300],
                }
                for r in results
            ]
    except Exception as e:
        log.warning(f"Tavily search failed: {e}")
        return []


# ── Movement history ──────────────────────────────────────────────────────────
def _format_position_as_memory(sat_id: str, pos: dict, cycle: int) -> str:
    """
    Format a single satellite position record as a natural-language
    string for storage in HybridMemory.
    """
    meta   = SAT_BY_ID.get(sat_id, {})
    region = ground_region(pos["lat"], pos["lon"])
    return (
        f"[SAT_HISTORY] {sat_id} ({meta.get('owner','?')} · {meta.get('type','?')}) "
        f"at {pos.get('ts', utcnow())} — "
        f"lat={pos['lat']:.2f} lon={pos['lon']:.2f} alt={pos.get('alt',0):.0f}km "
        f"over {region} — "
        f"threat={THREAT_LABELS[meta.get('threat', 0)]} — "
        f"cycle={cycle}"
    )

async def store_snapshot(agent: EZAgent, snapshot_text: str, cycle: int) -> int:
    """
    Parse the SGP4 snapshot text from the frontend and store each
    satellite position as a tagged memory entry.

    Frontend snapshot line format (from runCycle snap):
      ISS(NASA/Roscosmos): lat=23.45 lon=67.89 alt=412km threat=NOMINAL
    """
    ts      = utcnow()
    pattern = re.compile(
        r"(?P<id>[A-Z0-9]+)\([^)]+\):\s*"
        r"lat=(?P<lat>-?\d+\.?\d*)\s+"
        r"lon=(?P<lon>-?\d+\.?\d*)\s+"
        r"alt=(?P<alt>\d+\.?\d*)km"
    )
    stored = 0
    for line in snapshot_text.splitlines():
        m = pattern.match(line.strip())
        if not m:
            continue
        sat_id = m.group("id")
        if sat_id not in VALID_IDS:
            continue

        pos = {
            "lat": float(m.group("lat")),
            "lon": float(m.group("lon")),
            "alt": float(m.group("alt")),
            "ts":  ts,
        }
        memory_str = _format_position_as_memory(sat_id, pos, cycle)
        tags = [
            sat_id,
            SAT_BY_ID.get(sat_id, {}).get("owner", ""),
            SAT_BY_ID.get(sat_id, {}).get("type", ""),
            ground_region(pos["lat"], pos["lon"]),
            "SAT_HISTORY",
        ]
        await agent.remember_async(memory_str, tags=[t for t in tags if t])
        stored += 1

    log.info(f"Cycle {cycle} — stored {stored} position records")
    return stored

async def recall_history(agent: EZAgent, sat_ids: list[str]) -> str:
    """
    Recall the last N position records for each satellite ID.
    Returns a formatted block ready to include in the agent prompt.
    """
    blocks = []
    for sat_id in sat_ids:
        results = await agent.recall_async(
            f"SAT_HISTORY {sat_id} position movement",
            limit=10,
        )
        if not results:
            blocks.append(f"{sat_id}: no history in memory yet")
            continue

        # Filter to entries that actually contain this sat_id
        lines = [
            r if isinstance(r, str) else r.get("content", str(r))
            for r in results
            if sat_id in (r if isinstance(r, str) else r.get("content", str(r)))
        ]
        if not lines:
            blocks.append(f"{sat_id}: no matching history entries")
            continue

        meta = SAT_BY_ID.get(sat_id, {})
        blocks.append(
            f"── {sat_id} · {meta.get('name','?')} · {meta.get('owner','?')} ──\n" +
            "\n".join(f"  {l}" for l in lines[-8:])
        )

    return "\n\n".join(blocks) if blocks else "No movement history in memory yet."


# ── Proximity detection ───────────────────────────────────────────────────────
def check_proximity(snapshot_text: str) -> list[str]:
    """
    Scan the current snapshot for military/intel satellite pairs
    that are within PROXIMITY_KM of each other.
    """
    pattern = re.compile(
        r"(?P<id>[A-Z0-9]+)\([^)]+\):\s*"
        r"lat=(?P<lat>-?\d+\.?\d*)\s+"
        r"lon=(?P<lon>-?\d+\.?\d*)"
    )
    positions = {}
    for m in pattern.finditer(snapshot_text):
        sid = m.group("id")
        if sid in VALID_IDS:
            positions[sid] = (float(m.group("lat")), float(m.group("lon")))

    alerts = []
    ids    = list(positions.keys())
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b    = ids[i], ids[j]
            meta_a  = SAT_BY_ID.get(a, {})
            meta_b  = SAT_BY_ID.get(b, {})
            # only flag if at least one is military or intel
            if meta_a.get("type") not in ("military", "intel") and \
               meta_b.get("type") not in ("military", "intel"):
                continue
            dist = haversine_km(*positions[a], *positions[b])
            if dist < PROXIMITY_KM:
                alerts.append(
                    f"PROXIMITY: {a}({meta_a.get('owner','?')}) ↔ "
                    f"{b}({meta_b.get('owner','?')}) — {dist:.0f}km apart — "
                    f"over {ground_region(*positions[a])}"
                )
    return alerts


# ── Query helpers ─────────────────────────────────────────────────────────────
def extract_sat_ids(query: str) -> list[str]:
    """Pull any satellite IDs mentioned in the user's query."""
    return [sid for sid in VALID_IDS if sid in query.upper()]

def build_tavily_query(user_query: str, sat_ids: list[str]) -> str:
    """Build a focused Tavily search query from the NL query + satellite context."""
    owners = list({SAT_BY_ID[sid]["owner"] for sid in sat_ids if sid in SAT_BY_ID})
    extras = []
    if any(o in ("Russia", "China/PLA", "CNSA") for o in owners):
        extras.append("satellite military intelligence 2025")
    if sat_ids:
        extras.append(" ".join(sat_ids[:2]))
    return f"{user_query.strip()} {' '.join(extras)}".strip()


# ── ATLAS system prompt ───────────────────────────────────────────────────────
def atlas_system_prompt() -> str:
    catalog = " | ".join(
        f"{s['id']}:{s['name']}({s['owner']},threat={THREAT_LABELS[s['threat']]})"
        for s in SAT_CATALOG
    )
    return f"""You are ATLAS — senior satellite intelligence analyst on the AkashVani Orbital platform.

You receive three fused data sources:
  1. Current SGP4 positions (live, Mar-2025 TLE epoch)
  2. Movement history recalled from persistent HybridMemory
  3. Live geopolitical news from Tavily open-source search

SATELLITE CATALOG:
{catalog}

RESPONSE FORMAT:
[ATLAS] FUSED INTELLIGENCE BRIEF
═══════════════════════════════════
SUBJECT: [satellite(s) or topic]
TIMEFRAME: [period covered]

MOVEMENT ANALYSIS:
  [trajectory, regions overflown, patterns, anomalies]

GEOPOLITICAL CORRELATION:
  [connect satellite activity to news context — be specific]

ASSESSMENT:
  IF [observed pattern] → THEN [likely intent] → RESULT [strategic implication]

CONFIDENCE: [HIGH/MED/LOW] — [reason]
WATCH: [what to monitor in next 24-48h]
═══════════════════════════════════
End response with exactly: RELEVANT OBJECTS: [comma-separated IDs]

Rules:
- Intel-officer tone — terse, precise, no hedging
- Name real countries, operators, and organizations
- If history is sparse, say so and reason from current position only
- Correlate news to movement explicitly — don't just list both separately
- Flag proximity events as potential coordinated ISR operations"""


# ── Request / Response models ─────────────────────────────────────────────────
class IngestRequest(BaseModel):
    snapshot: str
    cycle:    int = 0

class IngestResponse(BaseModel):
    stored: int
    cycle:  int
    ts:     str

class IntelQueryRequest(BaseModel):
    query:              str
    satellite_snapshot: str = ""

class IntelQueryResponse(BaseModel):
    response:     str
    relevant_ids: list[str]
    news_used:    int
    history_sats: list[str]
    proximity:    list[str]
    ts:           str

class AgentRequest(BaseModel):
    role:               str
    user_message:       str
    satellite_snapshot: str = ""

class AgentResponse(BaseModel):
    role:         str
    response:     str
    relevant_ids: list[str]
    ts:           str


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_relevant_ids(text: str) -> list[str]:
    m = re.search(r"RELEVANT OBJECTS:\s*([A-Z0-9,\s]+)", text, re.IGNORECASE)
    if not m:
        return []
    return [i.strip() for i in m.group(1).split(",") if i.strip() in VALID_IDS]

def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status":     "ok",
        "service":    "akvani-orbital-fused-intel",
        "version":    "3.0.0",
        "ts":         utcnow(),
        "satellites": len(SAT_CATALOG),
        "db":         DB_PATH,
        "tavily":     bool(TAVILY_KEY),
    }


@app.get("/satellites")
async def list_satellites():
    return {
        "count":   len(SAT_CATALOG),
        "catalog": [{**s, "threat_label": THREAT_LABELS[s["threat"]]} for s in SAT_CATALOG],
    }


@app.post("/ingest", response_model=IngestResponse)
async def ingest_snapshot(req: IngestRequest):
    """
    Store satellite positions from a frontend cycle into HybridMemory.
    Call this from runCycle() in gotham-v2.jsx — fire and forget:

        fetch(`${BACKEND_URL}/ingest`, {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({snapshot: snap, cycle: cycle})
        }).catch(()=>{});
    """
    if not req.snapshot.strip():
        raise HTTPException(status_code=400, detail="snapshot cannot be empty")
    agent  = await get_agent()
    stored = await store_snapshot(agent, req.snapshot, req.cycle)
    return IngestResponse(stored=stored, cycle=req.cycle, ts=utcnow())


@app.post("/intel-query", response_model=IntelQueryResponse)
async def intel_query(req: IntelQueryRequest):
    """
    Palantir-style fused intelligence query.

    Simultaneously:
      - Recalls satellite movement history from HybridMemory
      - Searches live geopolitical news via Tavily
      - Detects proximity events in current snapshot
      - Fuses all three → ATLAS agent reasons like a senior analyst

    Replace handleNL() in gotham-v2.jsx:

        const r = await fetch(`${BACKEND_URL}/intel-query`, {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({query: nlQuery, satellite_snapshot: snap})
        });
        const d = await r.json();
        setNlResult(d.response);
        setHl(d.relevant_ids);
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query cannot be empty")

    log.info(f"Intel query: {req.query!r}")
    agent = await get_agent()

    # Which satellites is this query about?
    sat_ids = extract_sat_ids(req.query)
    if not sat_ids:
        # Default to high-threat satellites if none specified
        sat_ids = [s["id"] for s in SAT_CATALOG if s["threat"] >= 2]

    log.info(f"Query satellites: {sat_ids}")

    # Run memory recall + Tavily search concurrently — don't wait for one before starting other
    tavily_q = build_tavily_query(req.query, sat_ids)
    history_result, news_results = await asyncio.gather(
        recall_history(agent, sat_ids),
        search_news(tavily_q),
    )

    # Proximity check on current snapshot
    proximity_alerts = check_proximity(req.satellite_snapshot) if req.satellite_snapshot else []

    log.info(f"History recalled, {len(news_results)} news results, {len(proximity_alerts)} proximity alerts")

    # Filter current snapshot to relevant satellites only
    current_pos_block = ""
    if req.satellite_snapshot:
        relevant_lines = [
            line for line in req.satellite_snapshot.splitlines()
            if any(sid in line for sid in sat_ids)
        ]
        if relevant_lines:
            current_pos_block = (
                "CURRENT SGP4 POSITIONS (live):\n" +
                "\n".join(f"  {l}" for l in relevant_lines)
            )

    # Build news block
    if news_results:
        news_block = "LIVE NEWS (Tavily open-source):\n" + "\n".join(
            f"  [{i+1}] {n['title']}\n       {n['snippet']}"
            for i, n in enumerate(news_results)
        )
    else:
        news_block = "LIVE NEWS: no results returned"

    # Build proximity block
    proximity_block = (
        "PROXIMITY ALERTS:\n" + "\n".join(f"  ⚠ {a}" for a in proximity_alerts)
        if proximity_alerts else ""
    )

    # Assemble fused prompt
    fused_prompt = "\n\n".join(filter(bool, [
        f"ANALYST QUERY: {req.query}",
        f"TIMESTAMP: {utcnow()}",
        current_pos_block,
        f"MOVEMENT HISTORY (HybridMemory recall):\n{history_result}",
        news_block,
        proximity_block,
        "Correlate satellite movement patterns with geopolitical news. "
        "Reason about intent and strategic implications, not just position.",
    ]))

    # Run ATLAS agent
    try:
        response = await agent.ask_async(
            user_message=fused_prompt,
            system_prompt=atlas_system_prompt(),
        )
    except Exception as e:
        log.error(f"ATLAS agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    relevant_ids = parse_relevant_ids(response)
    log.info(f"Intel query complete — {len(response)} chars, IDs: {relevant_ids}")

    return IntelQueryResponse(
        response=response,
        relevant_ids=relevant_ids,
        news_used=len(news_results),
        history_sats=sat_ids,
        proximity=proximity_alerts,
        ts=utcnow(),
    )


@app.post("/agent", response_model=AgentResponse)
async def run_agent(req: AgentRequest):
    """
    Drop-in for the three agent tabs (ORBITAL-1, NEWS-1, ANALYST-1).
    Use this to route the existing runCycle() agents through EZAgent
    instead of calling Anthropic directly from the browser.

    Maps: orbital → SYS_ORBITAL, news → SYS_NEWS, analyst → SYS_ANALYST
    """
    SYS = {
        "orbital": (
            "You are ORBITAL-1 on optimum_ReAct. Real SGP4 positions from Mar-2025 TLEs. "
            "4-5 bullet intel. [ORBITAL-1] header. Flag conflict-zone passes, proximity events. Terse."
        ),
        "news": (
            "You are NEWS-1, geopolitical intel. 3-bullet OSINT briefing. "
            "[NEWS-1] then [SOURCE] HEADLINE — implication."
        ),
        "analyst": (
            "You are ANALYST-1.\n[ANALYST-1] SYNTHESIS\n═══════════════════════\n"
            "IF [actor][action] → THEN [effect] → RESULT [outcome]\n"
            "RECOMMENDATION: [48h action]  CONFIDENCE: [HIGH/MED/LOW] — [reason]\n"
            "═══════════════════════\nName real companies."
        ),
    }
    role = req.role.lower().strip()
    if role not in SYS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown role '{role}'. Use: orbital | news | analyst"
        )

    user_msg = req.user_message
    if req.satellite_snapshot:
        user_msg = f"Live SGP4 snapshot {utcnow()}:\n{req.satellite_snapshot}\n\n{user_msg}"

    try:
        agent    = await get_agent()
        response = await agent.ask_async(
            user_message=user_msg,
            system_prompt=SYS[role],
        )
    except Exception as e:
        log.error(f"Agent [{role}] error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return AgentResponse(
        role=role,
        response=response,
        relevant_ids=parse_relevant_ids(response),
        ts=utcnow(),
    )


@app.get("/history/{sat_id}")
async def satellite_history(sat_id: str, limit: int = 20):
    """
    Raw movement history for a specific satellite.
    Useful for debugging or building custom frontend charts.

    GET /history/COSMOS2543?limit=20
    """
    if sat_id not in VALID_IDS:
        raise HTTPException(status_code=404, detail=f"Unknown satellite ID '{sat_id}'")
    agent   = await get_agent()
    results = await agent.recall_async(f"SAT_HISTORY {sat_id}", limit=limit)
    return {
        "sat_id":  sat_id,
        "name":    SAT_BY_ID[sat_id]["name"],
        "owner":   SAT_BY_ID[sat_id]["owner"],
        "threat":  THREAT_LABELS[SAT_BY_ID[sat_id]["threat"]],
        "count":   len(results),
        "history": results,
        "ts":      utcnow(),
    }


@app.get("/stats")
async def stats():
    """Agent memory stats — useful for the Agents tab."""
    agent = await get_agent()
    try:
        s = await agent.stats_async()
        return {"stats": s, "db": DB_PATH, "tavily": bool(TAVILY_KEY), "ts": utcnow()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/clear")
async def clear_memory():
    """Wipe all agent memory. Use for demo resets."""
    global _agent
    agent = await get_agent()
    try:
        await agent.clear_async()
        _agent = None
        log.info("Memory cleared — agent reset")
        return {"cleared": True, "ts": utcnow()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False, workers=2)