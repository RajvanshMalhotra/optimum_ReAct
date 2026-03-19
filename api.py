"""
Gotham Orbital — Fused Intelligence Backend  v4.1
==================================================
Key changes in this version
----------------------------
1. Role-specific agent pool — each role (atlas, orbital, news, analyst) gets
   its own EZAgent with the correct system_prompt set at construction time,
   not buried in the task string.  Uses your EZAgent / IntelligentAgent API
   exactly as designed.
2. workers=1  — _agents dict is process-global; workers>1 splits it.
3. max_steps=6 — each step = 1 Groq call; 20 steps burned the rate limit.
4. Semaphore(2) — caps concurrent Groq calls across the whole process.
5. Bounded 429 retry in llm.py (15/30/60 s, max 3 attempts).
6. Task truncation at 6000 chars — prevents Groq 400 → JSON fail →
   full-prompt-as-search-query → Tavily 400 cascade.
7. Staggered TLE fetches (200 ms) — prevents Celestrak IP banning EC2.
8. x-llm-model header — frontend can hot-swap the model per request.
9. GET /models — returns available models for the frontend model picker.
10. Default model: llama-3.1-8b-instant (131k tok/min vs 12k for 70b).
"""

import os
import re
import math
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from functools import partial
from fastapi.middleware.cors import CORSMiddleware

try:
    from sgp4.api import Satrec, jday
    SGP4_AVAILABLE = True
except ImportError:
    SGP4_AVAILABLE = False

import httpx
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger("gotham-api")

app = FastAPI(title="Gotham Orbital — Fused Intelligence API", version="4.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(10.0),
    limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
)

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH        = os.getenv("AGENT_DB_PATH", "data/gotham_agent.db")
TAVILY_KEY     = os.getenv("TAVILY_API_KEY", "")
PROXIMITY_KM   = 500
MAX_TASK_CHARS = 6000

os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)

_groq_semaphore = asyncio.Semaphore(2)

# ── Available models ──────────────────────────────────────────────────────────
AVAILABLE_MODELS = [
    {"id": "llama-3.1-8b-instant",    "label": "Llama 3.1 8B Instant",    "tokens_min": 131072, "recommended": True,  "note": "Best for multi-step agents"},
    {"id": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B Versatile", "tokens_min": 12000,  "recommended": False, "note": "Highest quality, hits rate limits fast"},
    {"id": "llama3-70b-8192",         "label": "Llama 3 70B 8192",        "tokens_min": 6000,   "recommended": False, "note": "Lower limit than 3.3"},
    {"id": "gemma2-9b-it",            "label": "Gemma 2 9B IT",           "tokens_min": 15000,  "recommended": False, "note": "Balanced quality and limits"},
    {"id": "mixtral-8x7b-32768",      "label": "Mixtral 8x7B 32768",      "tokens_min": 5000,   "recommended": False, "note": "Lowest limit — avoid for agents"},
]
DEFAULT_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")

# ── Role system prompts ───────────────────────────────────────────────────────
# These are passed directly to EZAgent(system_prompt=...) so IntelligentAgent
# injects them at every reasoning step — not buried in task strings.
ROLE_SYSTEM_PROMPTS = {
    "atlas": (
        "You are ATLAS, a senior satellite intelligence analyst. "
        "You are rigorous, methodical, and intellectually honest. "
        "You do not speculate beyond your data. "
        "Your credibility depends on the precision and sourcing of every claim. "
        "Tag every factual claim as [RETRIEVED], [INFERRED], or [UNKNOWN]. "
        "Search the web for current conflict zone locations and satellite mission details "
        "before declaring anything [UNKNOWN]."
    ),
    "orbital": (
        "You are ORBITAL-1, a precise satellite tracking analyst. "
        "Analyze satellite positions and produce a 4-5 bullet intel brief. "
        "For each bullet: name the satellite, state its region and altitude, "
        "and flag anomalies with [ANOMALY]. "
        "If position data is missing for a satellite say so — do not estimate. "
        "Always start your response with [ORBITAL-1]."
    ),
    "news": (
        "You are NEWS-1, a geopolitical OSINT analyst. "
        "Give a 3-bullet brief on the strategic context of satellite operators. "
        "Each bullet must cite a specific event, date, or verifiable fact. "
        "Search the web for recent developments before responding. "
        "Always start your response with [NEWS-1]."
    ),
    "analyst": (
        "You are ANALYST-1, a senior intelligence analyst. "
        "Your reputation depends on never overstating certainty. "
        "You are rewarded for identifying gaps, not for confident-sounding conclusions from weak data.\n\n"
        "Before writing anything you MUST search for: "
        "(1) current active conflict zones in every region overflown, "
        "(2) each satellite's known mission and ISR role, "
        "(3) latest military/ground activity in each overflown region, "
        "(4) open-source evidence of Russia-China satellite coordination.\n\n"
        "[UNKNOWN] is only valid after a search returned no result. "
        "Declaring something [UNKNOWN] without searching is an analytical failure.\n\n"
        "Start your response with [ANALYST-1] SYNTHESIS. "
        "Format findings as: IF [actor][action] THEN [effect] RESULT [outcome]. "
        "End with RECOMMENDATION, CONFIDENCE, and: "
        "RELEVANT OBJECTS: [comma-separated IDs from catalog]"
    ),
}

# ── Agent pool — keyed by (groq_key, model, role) ────────────────────────────
_agents: dict = {}
_agents_lock  = asyncio.Lock()


async def get_agent(
    groq_key:   str = "",
    tavily_key: str = "",
    model:      str = "moonshotai/kimi-k2-instruct-0905",
    role:       str = "atlas",
) -> Any:
    global _agents

    effective_groq   = groq_key   or os.getenv("GROQ_API_KEY",  "")
    effective_tavily = tavily_key or os.getenv("TAVILY_API_KEY", "")
    effective_model  = model      or DEFAULT_MODEL
    effective_role   = role       if role in ROLE_SYSTEM_PROMPTS else "atlas"

    if not effective_groq:
        raise HTTPException(
            status_code=401,
            detail="Groq API key required. Send via x-groq-key header.",
        )

    pool_key = (effective_groq, effective_model, effective_role)

    async with _agents_lock:
        if pool_key not in _agents:
            log.info(
                f"Building EZAgent — role={effective_role} "
                f"model={effective_model} key={effective_groq[:8]}..."
            )
            os.environ["GROQ_API_KEY"]   = effective_groq
            os.environ["TAVILY_API_KEY"] = effective_tavily

            # Update the shared LLM client's api_key
            from core.llm import llm_client
            llm_client.api_key = effective_groq

            # Import EZAgent and build with explicit model + system_prompt
            from AgenT import EZAgent as _EZAgent
            loop = asyncio.get_event_loop()
            agent = await loop.run_in_executor(
                None,
                lambda: _EZAgent(
                    memory_path=DB_PATH,
                    model=effective_model,
                    system_prompt=ROLE_SYSTEM_PROMPTS[effective_role],
                ),
            )
            _agents[pool_key] = agent
            log.info(f"EZAgent ready — role={effective_role} model={agent.model}")

    return _agents[pool_key]


# ── Task truncation ───────────────────────────────────────────────────────────
def truncate_task(text: str, limit: int = MAX_TASK_CHARS) -> str:
    if len(text) <= limit:
        return text
    log.warning(f"Task truncated from {len(text)} to {limit} chars")
    return text[:limit] + "\n\n[CONTEXT TRUNCATED — answer with available data]"


async def _ask(agent: Any, task: str, max_steps: int = 6) -> str:
    safe_task = truncate_task(task)
    async with _groq_semaphore:
        return await agent.ask_async(safe_task, max_steps=max_steps)


# ── Async memory wrappers ─────────────────────────────────────────────────────
async def _remember(agent: Any, content: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(agent.memory.remember, content, mem_type="fact", importance=0.8)
    )

async def _recall(agent: Any, query: str, limit: int = 10) -> list:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, partial(agent.memory.recall, query, limit)
    )


# ── Geo helpers ───────────────────────────────────────────────────────────────
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
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


# ── TLE fetching ──────────────────────────────────────────────────────────────
NORAD_IDS = {
    "ISS": 25544, "TIANGONG": 48274, "NOAA19": 33591, "TERRA": 25994,
    "AQUA": 27424, "SENTINEL2B": 42063, "STARLINK30": 44235, "STARLINK31": 44249,
    "IRIDIUM140": 43478, "GPS001": 32711, "GLONASS": 32276,
    "COSMOS2543": 44547, "YAOGAN30": 43163, "LACROSSE5": 28646,
}

_tle_cache: dict = {}
_tle_lock = asyncio.Lock()
TLE_TTL_HOURS = 6


async def fetch_tle_celestrak(norad_id: int) -> Optional[tuple]:
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad_id}&FORMAT=TLE"
    try:
        r = await http_client.get(url)
        r.raise_for_status()
        lines = [l.strip() for l in r.text.strip().splitlines() if l.strip()]
        if len(lines) >= 3:  return lines[1], lines[2]
        if len(lines) == 2 and lines[0].startswith("1 "): return lines[0], lines[1]
    except Exception as e:
        log.warning(f"Celestrak fetch failed for {norad_id}: {e}")
    return None


async def fetch_all_tles() -> dict:
    """Staggered fetch — 200 ms between requests to avoid Celestrak IP bans."""
    results = {}
    now = datetime.now(timezone.utc)
    for sat_id, norad_id in NORAD_IDS.items():
        result = await fetch_tle_celestrak(norad_id)
        if result:
            results[sat_id] = {"line1": result[0], "line2": result[1], "fetched_at": now.isoformat()}
            log.info(f"TLE fetched: {sat_id}")
        else:
            log.warning(f"TLE fetch failed for {sat_id}")
        await asyncio.sleep(0.2)
    return results


async def get_tles_cached() -> dict:
    global _tle_cache
    async with _tle_lock:
        now = datetime.now(timezone.utc)
        if _tle_cache:
            sample    = next(iter(_tle_cache.values()))
            fetched_at = datetime.fromisoformat(sample["fetched_at"])
            if (now - fetched_at).total_seconds() / 3600 < TLE_TTL_HOURS:
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


# ── Helpers ───────────────────────────────────────────────────────────────────
def extract_sat_ids(query: str) -> list:
    return [sid for sid in VALID_IDS if sid in query.upper()]

def parse_relevant_ids(text: str) -> list:
    m = re.search(r"RELEVANT OBJECTS:\s*([A-Z0-9,\s]+)", text, re.IGNORECASE)
    if not m: return []
    return [i.strip() for i in m.group(1).split(",") if i.strip() in VALID_IDS]

def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def enrich_snapshot(snapshot_text: str) -> str:
    pattern = re.compile(
        r"(?P<id>[A-Z0-9]+)\([^)]+\):\s*"
        r"lat=(?P<lat>-?\d+\.?\d*)\s+"
        r"lon=(?P<lon>-?\d+\.?\d*)\s+"
        r"alt=(?P<alt>\d+\.?\d*)km"
    )
    enriched = []
    for line in snapshot_text.splitlines():
        m = pattern.match(line.strip())
        if m:
            region = ground_region(float(m.group("lat")), float(m.group("lon")))
            enriched.append(f"{line.strip()} → REGION: {region}")
        else:
            enriched.append(line)
    return "\n".join(enriched)

def check_proximity(snapshot_text: str) -> list:
    pattern = re.compile(
        r"(?P<id>[A-Z0-9]+)\([^)]+\):\s*lat=(?P<lat>-?\d+\.?\d*)\s+lon=(?P<lon>-?\d+\.?\d*)"
    )
    positions = {
        m.group("id"): (float(m.group("lat")), float(m.group("lon")))
        for m in pattern.finditer(snapshot_text) if m.group("id") in VALID_IDS
    }
    alerts = []
    ids = list(positions.keys())
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            ma, mb = SAT_BY_ID.get(a, {}), SAT_BY_ID.get(b, {})
            if ma.get("type") not in ("military", "intel") and mb.get("type") not in ("military", "intel"):
                continue
            dist = haversine_km(*positions[a], *positions[b])
            if dist < PROXIMITY_KM:
                alerts.append(
                    f"PROXIMITY: {a}({ma.get('owner','?')}) ↔ {b}({mb.get('owner','?')}) "
                    f"— {dist:.0f}km — over {ground_region(*positions[a])}"
                )
    return alerts


# ── Movement history ──────────────────────────────────────────────────────────
def _format_pos(sat_id: str, pos: dict, cycle: int) -> str:
    meta = SAT_BY_ID.get(sat_id, {})
    return (
        f"[SAT_HISTORY] {sat_id} ({meta.get('owner','?')} · {meta.get('type','?')}) "
        f"at {pos.get('ts', utcnow())} — "
        f"lat={pos['lat']:.2f} lon={pos['lon']:.2f} alt={pos.get('alt',0):.0f}km "
        f"over {ground_region(pos['lat'], pos['lon'])} — "
        f"threat={THREAT_LABELS[meta.get('threat', 0)]} — cycle={cycle}"
    )

async def store_snapshot(agent: Any, snapshot_text: str, cycle: int) -> int:
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

async def recall_history(agent: Any, sat_ids: list) -> str:
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


# ── Ground track prediction ───────────────────────────────────────────────────
def compute_ground_tracks(sat_ids: list, tles: dict, minutes: int = 90, step: int = 15) -> dict:
    if not SGP4_AVAILABLE:
        return {sid: [] for sid in sat_ids}
    tracks = {}
    now = datetime.now(timezone.utc)
    for sid in sat_ids:
        tle = tles.get(sid)
        if not tle:
            tracks[sid] = []; continue
        try:
            sat = Satrec.twoline2rv(tle["line1"], tle["line2"])
            points = []
            for offset in range(0, minutes + step, step):
                t = now + timedelta(minutes=offset)
                jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute,
                              t.second + t.microsecond / 1e6)
                e, r, _ = sat.sgp4(jd, fr)
                if e != 0: continue
                x, y, z = r
                alt_km = math.sqrt(x**2 + y**2 + z**2) - 6371.0
                lat    = math.degrees(math.atan2(z, math.sqrt(x**2 + y**2)))
                gmst   = _gmst(jd + fr)
                lon    = (math.degrees(math.atan2(y, x)) - math.degrees(gmst) + 180) % 360 - 180
                points.append({
                    "ts": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "lat": round(lat, 2), "lon": round(lon, 2),
                    "alt_km": round(alt_km, 1), "region": ground_region(lat, lon),
                    "t_plus": f"+{offset}min",
                })
            tracks[sid] = points
        except Exception as e:
            log.warning(f"Ground track failed for {sid}: {e}")
            tracks[sid] = []
    return tracks

def _gmst(jd_full: float) -> float:
    T = (jd_full - 2451545.0) / 36525.0
    gmst_sec = (67310.54841 + (876600 * 3600 + 8640184.812866) * T
                + 0.093104 * T**2 - 6.2e-6 * T**3)
    return math.radians((gmst_sec % 86400) / 86400 * 360)

def _format_ground_tracks_for_prompt(tracks: dict) -> str:
    if not any(tracks.values()): return ""
    lines = ["Predicted ground tracks (next 90 min, SGP4):"]
    for sid, points in tracks.items():
        if not points:
            lines.append(f"  {sid}: propagation unavailable"); continue
        meta = SAT_BY_ID.get(sid, {})
        for p in points:
            lines.append(
                f"  {sid} ({meta.get('owner','?')}) {p['t_plus']}: "
                f"lat={p['lat']} lon={p['lon']} alt={p['alt_km']}km over {p['region']}"
            )
    return "\n".join(lines)


# ── Pydantic models ───────────────────────────────────────────────────────────
class IngestRequest(BaseModel):
    snapshot: str
    cycle:    int = 0

class IngestResponse(BaseModel):
    stored: int; cycle: int; ts: str

class IntelQueryRequest(BaseModel):
    query:              str
    satellite_snapshot: str = ""
    current_cycle:      int = 0

class IntelQueryResponse(BaseModel):
    response: str; relevant_ids: list; history_sats: list
    proximity: list; ground_tracks: dict; ts: str

class AgentRequest(BaseModel):
    role: str; user_message: str; satellite_snapshot: str = ""

class AgentResponse(BaseModel):
    role: str; response: str; relevant_ids: list; ts: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/models")
async def list_models():
    return {"default": DEFAULT_MODEL, "models": AVAILABLE_MODELS, "ts": utcnow()}

@app.get("/health")
async def health():
    return {
        "status": "ok", "service": "gotham-orbital", "version": "4.1.0",
        "ts": utcnow(), "satellites": len(SAT_CATALOG), "db": DB_PATH,
        "tavily": bool(TAVILY_KEY), "groq_env": bool(os.getenv("GROQ_API_KEY")),
        "default_model": DEFAULT_MODEL, "sgp4": SGP4_AVAILABLE,
        "agent_roles": list(ROLE_SYSTEM_PROMPTS.keys()),
    }

@app.get("/satellites")
async def list_satellites():
    return {"count": len(SAT_CATALOG),
            "catalog": [{**s, "threat_label": THREAT_LABELS[s["threat"]]} for s in SAT_CATALOG]}

@app.get("/tles")
async def get_tles_endpoint():
    tles = await get_tles_cached()
    if not tles:
        raise HTTPException(503, "TLE fetch failed — Celestrak may be unavailable")
    return {"count": len(tles), "tles": tles, "ttl_hours": TLE_TTL_HOURS, "ts": utcnow()}

@app.post("/tles/refresh")
async def refresh_tles():
    global _tle_cache
    _tle_cache = {}
    tles = await get_tles_cached()
    return {"refreshed": len(tles), "ts": utcnow()}

@app.post("/ingest", response_model=IngestResponse)
async def ingest_snapshot(
    req:          IngestRequest,
    x_groq_key:   str = Header(default=""),
    x_tavily_key: str = Header(default=""),
    x_llm_model:  str = Header(default=""),
):
    if not req.snapshot.strip():
        raise HTTPException(400, "snapshot cannot be empty")
    agent  = await get_agent(x_groq_key, x_tavily_key, x_llm_model, role="atlas")
    stored = await store_snapshot(agent, req.snapshot, req.cycle)
    return IngestResponse(stored=stored, cycle=req.cycle, ts=utcnow())

@app.post("/intel-query", response_model=IntelQueryResponse)
async def intel_query(
    req:          IntelQueryRequest,
    x_groq_key:   str = Header(default=""),
    x_tavily_key: str = Header(default=""),
    x_llm_model:  str = Header(default=""),
):
    if not req.query.strip():
        raise HTTPException(400, "query cannot be empty")

    log.info(f"Intel query: {req.query!r} (cycle={req.current_cycle})")
    agent   = await get_agent(x_groq_key, x_tavily_key, x_llm_model, role="atlas")
    sat_ids = extract_sat_ids(req.query) or [s["id"] for s in SAT_CATALOG if s["threat"] >= 2]

    history_result   = await recall_history(agent, sat_ids)
    proximity_alerts = check_proximity(req.satellite_snapshot) if req.satellite_snapshot else []

    tles               = await get_tles_cached()
    ground_tracks      = compute_ground_tracks(sat_ids, tles)
    ground_track_block = _format_ground_tracks_for_prompt(ground_tracks)

    current_pos = ""
    if req.satellite_snapshot:
        enriched = enrich_snapshot(req.satellite_snapshot)
        lines    = [l for l in enriched.splitlines() if any(s in l for s in sat_ids)]
        if lines:
            current_pos = "Current SGP4 positions:\n" + "\n".join(lines)

    proximity_block = ("Proximity alerts:\n" + "\n".join(proximity_alerts)) if proximity_alerts else ""

    # The system prompt (ATLAS persona) is already set on this agent.
    # The task only needs to contain data, not role instructions.
    task = "\n\n".join(filter(bool, [
        f"Query: {req.query}",
        f"Timestamp: {utcnow()} — Cycle: {req.current_cycle}",
        current_pos,
        ground_track_block,
        f"Movement history:\n{history_result}" if history_result != "No movement history yet." else "",
        proximity_block,
        "Produce a structured brief: MOVEMENT ANALYSIS / GEOPOLITICAL CONTEXT / "
        "ASSESSMENT (IF..THEN..RESULT) / CONFIDENCE / WATCH.\n"
        "End with: RELEVANT OBJECTS: [comma-separated satellite IDs]",
    ]))

    try:
        response = await _ask(agent, task, max_steps=6)
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"ATLAS error: {e}")
        raise HTTPException(500, str(e))

    return IntelQueryResponse(
        response=response, relevant_ids=parse_relevant_ids(response),
        history_sats=sat_ids, proximity=proximity_alerts,
        ground_tracks=ground_tracks, ts=utcnow(),
    )

@app.post("/agent", response_model=AgentResponse)
async def run_agent(
    req:          AgentRequest,
    x_groq_key:   str = Header(default=""),
    x_tavily_key: str = Header(default=""),
    x_llm_model:  str = Header(default=""),
):
    role = req.role.lower().strip()
    if role not in ROLE_SYSTEM_PROMPTS:
        raise HTTPException(400, f"Unknown role '{role}'. Use: {list(ROLE_SYSTEM_PROMPTS.keys())}")

    # Each role has its own EZAgent with system_prompt already set.
    # The task contains only data + user message — no role instructions needed here.
    enriched  = enrich_snapshot(req.satellite_snapshot) if req.satellite_snapshot else ""
    snap      = f"Satellite positions ({utcnow()}):\n{enriched}\n\n" if enriched else ""
    full_task = f"{snap}{req.user_message}"

    try:
        agent    = await get_agent(x_groq_key, x_tavily_key, x_llm_model, role=role)
        response = await _ask(agent, full_task, max_steps=6)
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Agent [{role}] error: {e}")
        raise HTTPException(500, str(e))

    return AgentResponse(
        role=role, response=response,
        relevant_ids=parse_relevant_ids(response), ts=utcnow(),
    )

@app.get("/history/{sat_id}")
async def satellite_history(sat_id: str, limit: int = 20):
    if sat_id not in VALID_IDS:
        raise HTTPException(404, f"Unknown satellite ID '{sat_id}'")
    agent   = await get_agent(role="atlas")
    results = await _recall(agent, f"SAT_HISTORY {sat_id}", limit=limit)
    return {
        "sat_id": sat_id, "name": SAT_BY_ID[sat_id]["name"],
        "owner": SAT_BY_ID[sat_id]["owner"], "threat": THREAT_LABELS[SAT_BY_ID[sat_id]["threat"]],
        "count": len(results),
        "history": [r.content if hasattr(r, "content") else str(r) for r in results],
        "ts": utcnow(),
    }

@app.get("/stats")
async def stats():
    agent = await get_agent(role="atlas")
    try:
        loop = asyncio.get_event_loop()
        s    = await loop.run_in_executor(None, agent.stats)
        return {"stats": s, "db": DB_PATH, "tavily": bool(TAVILY_KEY), "ts": utcnow()}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.delete("/clear")
async def clear_memory():
    global _agents
    async with _agents_lock:
        _agents.clear()
    return {"cleared": True, "ts": utcnow()}


@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    # workers=1 is MANDATORY — _agents is a process-global dict.
    # workers > 1 = each process gets its own empty dict = key set in
    # worker A is invisible to worker B.
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False, workers=1)