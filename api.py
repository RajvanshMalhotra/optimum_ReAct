"""
optimum_ReAct — Palantir-style Fused Intelligence Backend
===========================================================
Frontend : Vercel (akvani-v2.jsx)
Backend  : AWS EC2 (this file)

FIXES vs previous version:
  - Removed calls to non-existent async methods (remember_async, recall_async,
    stats_async, clear_async, ask_async with kwargs that don't exist)
  - EZAgent.ask_async() takes only (task, max_steps) — no system_prompt kwarg
  - All "async" wrappers now run sync HybridMemory methods in a thread executor
  - atlas_system_prompt is injected INTO the task string, not as a kwarg
"""

import os
import re
import math
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from functools import partial

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from AgenT import EZAgent

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger("akvani-api")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AkashVani Orbital — Fused Intelligence API",
    description="Palantir-style satellite movement history + live news fusion",
    version="3.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH      = os.getenv("AGENT_DB_PATH", "data/akvani_agent.db")
TAVILY_KEY   = os.getenv("TAVILY_API_KEY", "")
TAVILY_URL   = "https://api.tavily.com/search"
MAX_NEWS     = 4
PROXIMITY_KM = 500

os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)

# ── Live TLE fetching ─────────────────────────────────────────────────────────
# NORAD catalog numbers for our 14 satellites
NORAD_IDS = {
    "ISS":        25544,
    "TIANGONG":   48274,
    "NOAA19":     33591,
    "TERRA":      25994,
    "AQUA":       27424,
    "SENTINEL2B": 42063,
    "STARLINK30": 44235,
    "STARLINK31": 44249,
    "IRIDIUM140": 43478,
    "GPS001":     32711,
    "GLONASS":    32276,
    "COSMOS2543": 44547,
    "YAOGAN30":   43163,
    "LACROSSE5":  28646,
}

# Cache: {sat_id: {"line1": ..., "line2": ..., "fetched_at": ...}}
_tle_cache: dict = {}
_tle_lock = asyncio.Lock()
TLE_TTL_HOURS = 6  # refresh every 6 hours

async def fetch_tle_celestrak(norad_id: int) -> tuple[str, str] | None:
    """Fetch a single TLE from Celestrak by NORAD ID."""
    url = f"https://celestrak.org/SATCAT/TLE/?CATNR={norad_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            lines = [l.strip() for l in r.text.strip().splitlines() if l.strip()]
            # Response is: NAME\nLINE1\nLINE2
            if len(lines) >= 3:
                return lines[1], lines[2]
            elif len(lines) == 2 and lines[0].startswith("1 "):
                return lines[0], lines[1]
    except Exception as e:
        log.warning(f"Celestrak fetch failed for {norad_id}: {e}")
    return None

async def fetch_all_tles() -> dict:
    """Fetch TLEs for all satellites, update cache."""
    results = {}
    now = datetime.now(timezone.utc)
    tasks = {sat_id: fetch_tle_celestrak(norad_id) for sat_id, norad_id in NORAD_IDS.items()}
    fetched = await asyncio.gather(*tasks.values(), return_exceptions=True)
    for sat_id, result in zip(tasks.keys(), fetched):
        if isinstance(result, tuple) and result:
            results[sat_id] = {"line1": result[0], "line2": result[1], "fetched_at": now.isoformat()}
            log.info(f"TLE fetched: {sat_id}")
        else:
            log.warning(f"TLE fetch failed for {sat_id}: {result}")
    return results

async def get_tles_cached() -> dict:
    """Return cached TLEs, refreshing if stale or missing."""
    global _tle_cache
    async with _tle_lock:
        now = datetime.now(timezone.utc)
        # Check if cache is fresh
        if _tle_cache:
            sample = next(iter(_tle_cache.values()))
            fetched_at = datetime.fromisoformat(sample["fetched_at"])
            age_hours = (now - fetched_at).total_seconds() / 3600
            if age_hours < TLE_TTL_HOURS:
                return _tle_cache
        log.info("Refreshing TLE cache from Celestrak...")
        fresh = await fetch_all_tles()
        if fresh:
            _tle_cache = fresh
        return _tle_cache

# ── Satellite catalog ─────────────────────────────────────────────────────────
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
            loop = asyncio.get_event_loop()
            _agent = await loop.run_in_executor(None, EZAgent, DB_PATH)
            log.info("EZAgent ready")
    return _agent


# ── Async wrappers for sync HybridMemory methods ──────────────────────────────
# EZAgent wraps HybridMemory. remember() and recall() are synchronous.
# We run them in a thread executor to avoid blocking FastAPI's event loop.

async def _remember(agent: EZAgent, content: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(agent.memory.remember, content, mem_type="fact", importance=0.8)
    )

async def _recall(agent: EZAgent, query: str, limit: int = 10) -> list:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(agent.memory.recall, query, limit)
    )

async def _ask(agent: EZAgent, task: str, max_steps: int = 6) -> str:
    # ask_async IS already async in EZAgent — call it directly
    return await agent.ask_async(task, max_steps=max_steps)


# ── Geo helpers ───────────────────────────────────────────────────────────────
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def ground_region(lat, lon):
    if   lat >  35 and  -10 < lon <  40: return "EUROPE"
    elif lat >  25 and -130 < lon < -60: return "N.AMERICA"
    elif lat >  45 and   40 < lon < 180: return "RUSSIA"
    elif  15 < lat <  55 and  70 < lon < 135: return "CHINA"
    elif   5 < lat <  35 and  65 < lon <  90: return "INDIA"
    elif  15 < lat <  42 and  25 < lon <  65: return "MIDEAST"
    elif -35 < lat <  35 and -20 < lon <  55: return "AFRICA"
    elif -55 < lat <  15 and -85 < lon < -35: return "S.AMERICA"
    elif -45 < lat < -10 and 110 < lon < 155: return "AUSTRALIA"
    elif  30 < lat <  50 and 125 < lon < 150: return "JAPAN/KOREA"
    elif  35 < lat <  47 and  26 < lon <  45: return "UKRAINE/BLACK SEA"
    elif lat > 65:  return "ARCTIC"
    elif lat < -60: return "ANTARCTIC"
    else:           return "OPEN OCEAN"


# ── Tavily news search ────────────────────────────────────────────────────────
async def search_news(query: str) -> list:
    if not TAVILY_KEY:
        log.warning("TAVILY_API_KEY not set — skipping news")
        return []
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(TAVILY_URL, json={
                "api_key": TAVILY_KEY, "query": query,
                "search_depth": "basic", "max_results": MAX_NEWS, "include_answer": False,
            })
            resp.raise_for_status()
            return [{"title": r.get("title",""), "url": r.get("url",""),
                     "snippet": r.get("content","")[:300]}
                    for r in resp.json().get("results", [])]
    except Exception as e:
        log.warning(f"Tavily failed: {e}")
        return []


# ── Movement history helpers ──────────────────────────────────────────────────
def _format_pos(sat_id: str, pos: dict, cycle: int) -> str:
    meta = SAT_BY_ID.get(sat_id, {})
    return (
        f"[SAT_HISTORY] {sat_id} ({meta.get('owner','?')} · {meta.get('type','?')}) "
        f"at {pos.get('ts', utcnow())} — "
        f"lat={pos['lat']:.2f} lon={pos['lon']:.2f} alt={pos.get('alt',0):.0f}km "
        f"over {ground_region(pos['lat'], pos['lon'])} — "
        f"threat={THREAT_LABELS[meta.get('threat', 0)]} — cycle={cycle}"
    )

async def store_snapshot(agent: EZAgent, snapshot_text: str, cycle: int) -> int:
    pattern = re.compile(
        r"(?P<id>[A-Z0-9]+)\([^)]+\):\s*"
        r"lat=(?P<lat>-?\d+\.?\d*)\s+"
        r"lon=(?P<lon>-?\d+\.?\d*)\s+"
        r"alt=(?P<alt>\d+\.?\d*)km"
    )
    ts = utcnow(); stored = 0
    for line in snapshot_text.splitlines():
        m = pattern.match(line.strip())
        if not m: continue
        sat_id = m.group("id")
        if sat_id not in VALID_IDS: continue
        pos = {"lat": float(m.group("lat")), "lon": float(m.group("lon")),
               "alt": float(m.group("alt")), "ts": ts}
        await _remember(agent, _format_pos(sat_id, pos, cycle))
        stored += 1
    log.info(f"Cycle {cycle} — stored {stored} records")
    return stored

async def recall_history(agent: EZAgent, sat_ids: list) -> str:
    blocks = []
    for sat_id in sat_ids:
        results = await _recall(agent, f"SAT_HISTORY {sat_id} position movement", limit=10)
        if not results:
            blocks.append(f"{sat_id}: no history yet"); continue
        lines = [
            (r.content if hasattr(r, "content") else str(r))
            for r in results
            if sat_id in (r.content if hasattr(r, "content") else str(r))
        ]
        if not lines:
            blocks.append(f"{sat_id}: no matching entries"); continue
        meta = SAT_BY_ID.get(sat_id, {})
        blocks.append(
            f"── {sat_id} · {meta.get('name','?')} · {meta.get('owner','?')} ──\n"
            + "\n".join(f"  {l}" for l in lines[-8:])
        )
    return "\n\n".join(blocks) if blocks else "No movement history yet."


# ── Proximity detection ───────────────────────────────────────────────────────
def check_proximity(snapshot_text: str) -> list:
    pattern = re.compile(
        r"(?P<id>[A-Z0-9]+)\([^)]+\):\s*lat=(?P<lat>-?\d+\.?\d*)\s+lon=(?P<lon>-?\d+\.?\d*)"
    )
    positions = {m.group("id"): (float(m.group("lat")), float(m.group("lon")))
                 for m in pattern.finditer(snapshot_text) if m.group("id") in VALID_IDS}
    alerts = []
    ids = list(positions.keys())
    for i in range(len(ids)):
        for j in range(i+1, len(ids)):
            a, b = ids[i], ids[j]
            ma, mb = SAT_BY_ID.get(a,{}), SAT_BY_ID.get(b,{})
            if ma.get("type") not in ("military","intel") and mb.get("type") not in ("military","intel"):
                continue
            dist = haversine_km(*positions[a], *positions[b])
            if dist < PROXIMITY_KM:
                alerts.append(
                    f"PROXIMITY: {a}({ma.get('owner','?')}) ↔ {b}({mb.get('owner','?')}) "
                    f"— {dist:.0f}km apart — over {ground_region(*positions[a])}"
                )
    return alerts


# ── Query helpers ─────────────────────────────────────────────────────────────
def extract_sat_ids(query: str) -> list:
    return [sid for sid in VALID_IDS if sid in query.upper()]

def build_tavily_query(user_query: str, sat_ids: list) -> str:
    owners = list({SAT_BY_ID[sid]["owner"] for sid in sat_ids if sid in SAT_BY_ID})
    extras = []
    if any(o in ("Russia", "China/PLA", "CNSA") for o in owners):
        extras.append("satellite military intelligence 2025")
    if sat_ids:
        extras.append(" ".join(sat_ids[:2]))
    return f"{user_query.strip()} {' '.join(extras)}".strip()

def atlas_system_prompt() -> str:
    catalog = " | ".join(
        f"{s['id']}:{s['name']}({s['owner']},threat={THREAT_LABELS[s['threat']]})"
        for s in SAT_CATALOG
    )
    return f"""You are ATLAS — senior satellite intelligence analyst on the Akashvani Orbital platform.

SATELLITE CATALOG:
{catalog}

RESPONSE FORMAT:
[ATLAS] FUSED INTELLIGENCE BRIEF
===================================
SUBJECT: [satellite(s) or topic]
TIMEFRAME: [period covered]

MOVEMENT ANALYSIS:
  [trajectory, regions overflown, patterns, anomalies]

GEOPOLITICAL CORRELATION:
  [connect satellite activity to news context]

ASSESSMENT:
  IF [observed pattern] THEN [likely intent] RESULT [strategic implication]

CONFIDENCE: [HIGH/MED/LOW] — [reason]
WATCH: [what to monitor in next 24-48h]
===================================
End with exactly: RELEVANT OBJECTS: [comma-separated IDs]

Rules: intel-officer tone, terse, name real countries/operators, flag proximity events."""


# ── Pydantic models ───────────────────────────────────────────────────────────
class IngestRequest(BaseModel):
    snapshot: str
    cycle:    int = 0

class IngestResponse(BaseModel):
    stored: int; cycle: int; ts: str

class IntelQueryRequest(BaseModel):
    query:              str
    satellite_snapshot: str = ""

class IntelQueryResponse(BaseModel):
    response: str; relevant_ids: list; news_used: int
    history_sats: list; proximity: list; ts: str

class AgentRequest(BaseModel):
    role: str; user_message: str; satellite_snapshot: str = ""

class AgentResponse(BaseModel):
    role: str; response: str; relevant_ids: list; ts: str


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_relevant_ids(text: str) -> list:
    m = re.search(r"RELEVANT OBJECTS:\s*([A-Z0-9,\s]+)", text, re.IGNORECASE)
    if not m: return []
    return [i.strip() for i in m.group(1).split(",") if i.strip() in VALID_IDS]

def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/tles")
async def get_tles_endpoint():
    """Return live TLEs for all tracked satellites. Cached for 6 hours."""
    tles = await get_tles_cached()
    if not tles:
        raise HTTPException(503, "TLE fetch failed — Celestrak may be unavailable")
    return {"count": len(tles), "tles": tles, "ttl_hours": TLE_TTL_HOURS, "ts": utcnow()}

@app.post("/tles/refresh")
async def refresh_tles():
    """Force-refresh TLE cache from Celestrak."""
    global _tle_cache
    _tle_cache = {}
    tles = await get_tles_cached()
    return {"refreshed": len(tles), "ts": utcnow()}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "AkashVani-orbital", "version": "3.1.0",
            "ts": utcnow(), "satellites": len(SAT_CATALOG), "db": DB_PATH, "tavily": bool(TAVILY_KEY)}

@app.get("/satellites")
async def list_satellites():
    return {"count": len(SAT_CATALOG),
            "catalog": [{**s, "threat_label": THREAT_LABELS[s["threat"]]} for s in SAT_CATALOG]}

@app.post("/ingest", response_model=IngestResponse)
async def ingest_snapshot(req: IngestRequest):
    if not req.snapshot.strip():
        raise HTTPException(400, "snapshot cannot be empty")
    agent  = await get_agent()
    stored = await store_snapshot(agent, req.snapshot, req.cycle)
    return IngestResponse(stored=stored, cycle=req.cycle, ts=utcnow())

@app.post("/intel-query", response_model=IntelQueryResponse)
async def intel_query(req: IntelQueryRequest):
    if not req.query.strip():
        raise HTTPException(400, "query cannot be empty")

    log.info(f"Intel query: {req.query!r}")
    agent   = await get_agent()
    sat_ids = extract_sat_ids(req.query) or [s["id"] for s in SAT_CATALOG if s["threat"] >= 2]

    history_result, news_results = await asyncio.gather(
        recall_history(agent, sat_ids),
        search_news(build_tavily_query(req.query, sat_ids)),
    )
    proximity_alerts = check_proximity(req.satellite_snapshot) if req.satellite_snapshot else []

    current_pos_block = ""
    if req.satellite_snapshot:
        lines = [l for l in req.satellite_snapshot.splitlines() if any(s in l for s in sat_ids)]
        if lines:
            current_pos_block = "CURRENT SGP4 POSITIONS:\n" + "\n".join(f"  {l}" for l in lines)

    news_block = ("LIVE NEWS:\n" + "\n".join(
        f"  [{i+1}] {n['title']}\n       {n['snippet']}" for i, n in enumerate(news_results)
    )) if news_results else "LIVE NEWS: none"

    proximity_block = ("PROXIMITY ALERTS:\n" + "\n".join(f"  ⚠ {a}" for a in proximity_alerts)) if proximity_alerts else ""

    # Inject system prompt INTO the task — EZAgent has no system_prompt param
    fused_task = "\n\n".join(filter(bool, [
        atlas_system_prompt(), "---",
        f"ANALYST QUERY: {req.query}", f"TIMESTAMP: {utcnow()}",
        current_pos_block,
        f"MOVEMENT HISTORY:\n{history_result}",
        news_block, proximity_block,
        "Correlate movement patterns with geopolitical news. Reason about intent.",
    ]))

    try:
        response = await _ask(agent, fused_task, max_steps=6)
    except Exception as e:
        log.error(f"ATLAS error: {e}")
        raise HTTPException(500, str(e))

    relevant_ids = parse_relevant_ids(response)
    return IntelQueryResponse(response=response, relevant_ids=relevant_ids,
                              news_used=len(news_results), history_sats=sat_ids,
                              proximity=proximity_alerts, ts=utcnow())

@app.post("/agent", response_model=AgentResponse)
async def run_agent(req: AgentRequest):
    SYS = {
        "orbital": "You are ORBITAL-1. Real SGP4 positions, Mar-2025 TLEs. 4-5 bullet intel. [ORBITAL-1] header. Terse.",
        "news":    "You are NEWS-1, geopolitical OSINT. [NEWS-1] then [SOURCE] HEADLINE — implication. 3 bullets.",
        "analyst": "You are ANALYST-1.\n[ANALYST-1] SYNTHESIS\nIF [actor][action] THEN [effect] RESULT [outcome]\nRECOMMENDATION: [48h action] CONFIDENCE: [HIGH/MED/LOW]",
    }
    role = req.role.lower().strip()
    if role not in SYS:
        raise HTTPException(400, f"Unknown role '{role}'. Use: orbital | news | analyst")

    snap = f"Live SGP4 {utcnow()}:\n{req.satellite_snapshot}\n\n" if req.satellite_snapshot else ""
    full_task = f"{SYS[role]}\n\n---\n\n{snap}{req.user_message}"

    try:
        agent    = await get_agent()
        response = await _ask(agent, full_task, max_steps=5)
    except Exception as e:
        log.error(f"Agent [{role}] error: {e}")
        raise HTTPException(500, str(e))

    return AgentResponse(role=role, response=response,
                         relevant_ids=parse_relevant_ids(response), ts=utcnow())

@app.get("/history/{sat_id}")
async def satellite_history(sat_id: str, limit: int = 20):
    if sat_id not in VALID_IDS:
        raise HTTPException(404, f"Unknown satellite ID '{sat_id}'")
    agent   = await get_agent()
    results = await _recall(agent, f"SAT_HISTORY {sat_id}", limit=limit)
    return {"sat_id": sat_id, "name": SAT_BY_ID[sat_id]["name"],
            "owner": SAT_BY_ID[sat_id]["owner"], "threat": THREAT_LABELS[SAT_BY_ID[sat_id]["threat"]],
            "count": len(results),
            "history": [r.content if hasattr(r, "content") else str(r) for r in results],
            "ts": utcnow()}

@app.get("/stats")
async def stats():
    agent = await get_agent()
    try:
        loop = asyncio.get_event_loop()
        s    = await loop.run_in_executor(None, agent.stats)
        return {"stats": s, "db": DB_PATH, "tavily": bool(TAVILY_KEY), "ts": utcnow()}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.delete("/clear")
async def clear_memory():
    global _agent
    try:
        agent = await get_agent()
        loop  = asyncio.get_event_loop()
        await loop.run_in_executor(None, agent.clear_session)
        _agent = None
        return {"cleared": True, "ts": utcnow()}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False, workers=2)