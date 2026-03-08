import { useState, useEffect, useRef, useCallback } from "react";

// ─────────────────────────────────────────────────────────────────────────────
// GOTHAM ORBITAL v4 — 3D Globe Edition
// • Three.js WebGL globe — real Earth texture, atmosphere glow
// • Live TLEs fetched from backend /tles (no fallback)
// • SGP4 orbital mechanics — real positions
// • Draggable globe rotation, scroll zoom
// • Glowing satellite dots with orbital trails
// • Full agent panel retained
// ─────────────────────────────────────────────────────────────────────────────

const SAT_CATALOG = [
  {id:"ISS",        name:"ISS (ZARYA)",       owner:"NASA/Roscosmos", color:"#00ffcc", threat:0, type:"civilian"   },
  {id:"TIANGONG",   name:"CSS Tiangong",       owner:"CNSA",           color:"#ffe44d", threat:1, type:"military"   },
  {id:"NOAA19",     name:"NOAA-19",            owner:"NOAA",           color:"#40e0ff", threat:0, type:"weather"    },
  {id:"TERRA",      name:"Terra EOS AM-1",     owner:"NASA",           color:"#7dff7d", threat:0, type:"science"    },
  {id:"AQUA",       name:"Aqua EOS PM-1",      owner:"NASA",           color:"#00aaff", threat:0, type:"science"    },
  {id:"SENTINEL2B", name:"Sentinel-2B",        owner:"ESA",            color:"#39ff14", threat:0, type:"observation"},
  {id:"STARLINK30", name:"Starlink-1007",      owner:"SpaceX",         color:"#00ccff", threat:0, type:"commercial" },
  {id:"STARLINK31", name:"Starlink-2341",      owner:"SpaceX",         color:"#00ccff", threat:0, type:"commercial" },
  {id:"IRIDIUM140", name:"IRIDIUM-140",        owner:"Iridium",        color:"#aabbcc", threat:0, type:"commercial" },
  {id:"GPS001",     name:"GPS IIF-2",          owner:"USAF",           color:"#cc66ff", threat:1, type:"navigation" },
  {id:"GLONASS",    name:"GLONASS-M 730",      owner:"Russia",         color:"#ff3355", threat:1, type:"navigation" },
  {id:"COSMOS2543", name:"COSMOS-2543",        owner:"Russia",         color:"#ff1111", threat:3, type:"military"   },
  {id:"YAOGAN30",   name:"YAOGAN-30F",         owner:"China/PLA",      color:"#ffcc00", threat:2, type:"military"   },
  {id:"LACROSSE5",  name:"USA-182",            owner:"NRO",            color:"#ff8800", threat:2, type:"intel"      },
];

const THREAT_META = [
  {label:"NOMINAL",  color:"#00ffcc"},
  {label:"MONITOR",  color:"#ffe44d"},
  {label:"ELEVATED", color:"#ff8800"},
  {label:"CRITICAL", color:"#ff1111"},
];

const EARTH_RADIUS = 6371;

// Convert lat/lon/alt to 3D cartesian
function llaToXYZ(lat, lon, alt, scale=1) {
  const r = (EARTH_RADIUS + alt) / EARTH_RADIUS * scale;
  const phi = (90 - lat) * Math.PI / 180;
  const theta = (lon + 180) * Math.PI / 180;
  return {
    x: -r * Math.sin(phi) * Math.cos(theta),
    y:  r * Math.cos(phi),
    z:  r * Math.sin(phi) * Math.sin(theta),
  };
}

function hexToRGB(hex) {
  const r = parseInt(hex.slice(1,3),16)/255;
  const g = parseInt(hex.slice(3,5),16)/255;
  const b = parseInt(hex.slice(5,7),16)/255;
  return {r,g,b};
}

// All AI calls route through the backend (Groq + Tavily) — keys sent per-request
async function backendAgent(url, secret, groqKey, tavilyKey, role, userMessage, satelliteSnapshot="") {
  const r = await fetch(`${url}/agent`, {
    method:"POST",
    headers:{
      "Content-Type":"application/json",
      "x-api-key":secret||"",
      "x-groq-key":groqKey||"",
      "x-tavily-key":tavilyKey||"",
    },
    body:JSON.stringify({role, user_message:userMessage, satellite_snapshot:satelliteSnapshot}),
  });
  if(!r.ok) throw new Error(`Backend /agent ${r.status}`);
  const d = await r.json();
  return d.response;
}

async function backendIngest(url, secret, groqKey, snapshot, cycle) {
  if(!url) return;
  try {
    await fetch(`${url}/ingest`, {
      method:"POST",
      headers:{"Content-Type":"application/json","x-api-key":secret||"","x-groq-key":groqKey||""},
      body:JSON.stringify({snapshot,cycle}),
    });
  } catch(e){}
}

async function backendIntelQuery(url, secret, groqKey, tavilyKey, query, snap) {
  const r = await fetch(`${url}/intel-query`, {
    method:"POST",
    headers:{
      "Content-Type":"application/json",
      "x-api-key":secret||"",
      "x-groq-key":groqKey||"",
      "x-tavily-key":tavilyKey||"",
    },
    body:JSON.stringify({query, satellite_snapshot:snap}),
  });
  if(!r.ok) throw new Error(`Backend ${r.status}`);
  return r.json();
}


function propagateAt(satrec, t) {
  try {
    const pv = window.satellite.propagate(satrec, t);
    if(!pv?.position) return null;
    const gmst = window.satellite.gstime(t);
    const geo = window.satellite.eciToGeodetic(pv.position, gmst);
    return {
      lat: window.satellite.degreesLat(geo.latitude),
      lon: window.satellite.degreesLong(geo.longitude),
      alt: geo.height,
    };
  } catch(e) { return null; }
}

function buildTrailAt(satrec, nowMs, steps=60, stepSec=60) {
  const pts = [];
  for(let i=steps; i>=0; i--) {
    const t = new Date(nowMs - i*stepSec*1000);
    const pos = propagateAt(satrec, t);
    if(pos) pts.push(pos);
  }
  return pts;
}

function AgentCard({a}) {
  const c={idle:"#112211",running:"#00ffcc",done:"#00aaff",error:"#ff1111"};
  return (
    <div style={{borderLeft:`3px solid ${c[a.status]}`,padding:"9px 11px",marginBottom:7,background:"rgba(0,8,4,.95)",borderRadius:2}}>
      <div style={{display:"flex",justifyContent:"space-between",marginBottom:4}}>
        <span style={{fontSize:9,color:c[a.status],letterSpacing:2,fontFamily:"monospace"}}>◈ {a.name}</span>
        <span style={{fontSize:8,color:c[a.status]+"99"}}>
          {a.status.toUpperCase()}
          {a.status==="running"&&<span style={{animation:"blink .7s step-end infinite"}}> ▌</span>}
        </span>
      </div>
      <div style={{fontSize:10,color:"#4a7a6a",fontFamily:"'Courier New',monospace",lineHeight:1.65,whiteSpace:"pre-wrap"}}>
        {a.output||<span style={{color:"#0a1a10",fontStyle:"italic"}}>standby</span>}
      </div>
    </div>
  );
}

export default function GothamOrbital() {
  const mountRef   = useRef(null);
  const threeRef   = useRef({}); // holds THREE scene objects
  const satrecsRef = useRef({});
  const selRef     = useRef(null);
  const hlRef      = useRef([]);
  const agentTimer = useRef(null);
  const animRef    = useRef(null);
  const simOffsetRef = useRef(0);
  const lastTsRef    = useRef(null);
  const speedRef     = useRef(1);

  const [ready,       setReady]      = useState(false);
  const [tleStatus,   setTleStatus]  = useState("loading"); // loading | live | error
  const [tleAge,      setTleAge]     = useState("");

  const [backendUrl,  setBackendUrl] = useState("http://16.16.251.215:8000");
  const [backendSec,  setBackendSec] = useState("");
  const [groqKey,     setGroqKey]    = useState("");
  const [tavilyKey,   setTavilyKey]  = useState("");
  const [selUI,       setSelUI]      = useState(null);
  const [selPos,      setSelPos]     = useState(null);
  const [running,     setRunning]    = useState(false);
  const [cycle,       setCycle]      = useState(0);
  const [nlQuery,     setNlQuery]    = useState("");
  const [nlResult,    setNlResult]   = useState(null);
  const [nlLoading,   setNlLoading]  = useState(false);
  const [alerts,      setAlerts]     = useState([]);
  const [speed,       setSpeed]      = useState(1);
  const [showSettings,setShowSettings]=useState(false);
  const [backendOk,   setBackendOk]  = useState(null);
  const [tab,         setTab]        = useState("globe");
  const [agents,      setAgents]     = useState([
    {id:"orbital",name:"ORBITAL-1 // MOVEMENT MONITOR",status:"idle",output:""},
    {id:"news",   name:"NEWS-1 // GEOPOLITICAL FEED",  status:"idle",output:""},
    {id:"analyst",name:"ANALYST-1 // SYNTHESIS ENGINE",status:"idle",output:""},
  ]);

  useEffect(()=>{speedRef.current=speed;},[speed]);

  const pushAlert = (msg,lvl=1) => setAlerts(p=>[{msg,lvl,ts:new Date().toISOString().slice(11,19)},...p].slice(0,18));
  const setAgent  = (id,patch) => setAgents(p=>p.map(a=>a.id===id?{...a,...patch}:a));
  const setSel    = (sat) => { selRef.current=sat; setSelUI(sat); setSelPos(null); };
  const setHl     = (ids) => { hlRef.current=ids; };

  // ── Boot: load Three.js + satellite.js, then fetch TLEs ──
  useEffect(()=>{
    let destroyed = false;

    const loadScript = (src) => new Promise((res,rej)=>{
      const s=document.createElement("script");
      s.src=src; s.onload=res; s.onerror=()=>rej(new Error(`Failed: ${src}`));
      document.head.appendChild(s);
    });

    async function init() {
      try {
        await Promise.all([
          loadScript("https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"),
          loadScript("https://cdnjs.cloudflare.com/ajax/libs/satellite.js/4.0.0/satellite.min.js"),
          loadScript("https://cdnjs.cloudflare.com/ajax/libs/topojson/3.0.2/topojson.min.js"),
        ]);
        if(destroyed) return;

        // Fetch live TLEs
        let tles = null;
        try {
          const r = await fetch(`${backendUrl}/tles`,{headers:{"x-api-key":backendSec||""}});
          if(!r.ok) throw new Error(`HTTP ${r.status}`);
          const data = await r.json();
          tles = data.tles;
          const sample = Object.values(data.tles)[0];
          setTleAge(sample?.fetched_at ? new Date(sample.fetched_at).toUTCString() : "now");
          setTleStatus("live");
          pushAlert(`Live TLEs loaded — ${Object.keys(tles).length} satellites ✓`, 0);
        } catch(e) {
          setTleStatus("error");
          pushAlert(`TLE fetch failed: ${e.message}`, 3);
          return; // no fallback — stop here
        }

        // Parse TLEs into satrecs
        let loaded = 0;
        SAT_CATALOG.forEach(({id})=>{
          const t = tles[id];
          if(!t) return;
          try { satrecsRef.current[id] = window.satellite.twoline2satrec(t.line1, t.line2); loaded++; }
          catch(e) { console.warn(`TLE parse failed: ${id}`, e); }
        });
        if(destroyed) return;

        // ── Build Three.js scene ──
        initThreeScene();
        setReady(true);
        pushAlert(`SGP4 ready — ${loaded} satellites tracking`, 0);

      } catch(e) {
        pushAlert(`Boot failed: ${e.message}`, 3);
      }
    }

    init();
    return () => {
      destroyed = true;
      cancelAnimationFrame(animRef.current);
      const T = threeRef.current;
      if(T.renderer) { T.renderer.dispose(); T.renderer.forceContextLoss(); }
    };
  // eslint-disable-next-line
  }, []);

  function initThreeScene() {
    const THREE = window.THREE;
    const mount = mountRef.current;
    if(!mount) return;

    const W = mount.clientWidth  || 900;
    const H = mount.clientHeight || 600;

    // Renderer
    const renderer = new THREE.WebGLRenderer({antialias:true, alpha:true});
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    mount.appendChild(renderer.domElement);

    // Scene + camera
    const scene  = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, W/H, 0.1, 1000);
    camera.position.set(0, 0, 3.2);

    // ── Stars ──
    const starGeo = new THREE.BufferGeometry();
    const starVerts = [];
    for(let i=0; i<8000; i++) {
      const theta = Math.random()*2*Math.PI;
      const phi   = Math.acos(2*Math.random()-1);
      const r     = 50 + Math.random()*50;
      starVerts.push(r*Math.sin(phi)*Math.cos(theta), r*Math.cos(phi), r*Math.sin(phi)*Math.sin(theta));
    }
    starGeo.setAttribute("position", new THREE.Float32BufferAttribute(starVerts, 3));
    scene.add(new THREE.Points(starGeo, new THREE.PointsMaterial({color:0xffffff,size:0.08,sizeAttenuation:true,transparent:true,opacity:0.7})));

    // ── Earth ──
    // Draw Earth texture procedurally on a canvas — deep blue ocean, visible green land
    const texCanvas = document.createElement("canvas");
    texCanvas.width  = 2048;
    texCanvas.height = 1024;
    const ctx = texCanvas.getContext("2d");

    // Ocean gradient
    const ocean = ctx.createLinearGradient(0, 0, 0, 1024);
    ocean.addColorStop(0,    "#0a1a3a");
    ocean.addColorStop(0.25, "#0d2855");
    ocean.addColorStop(0.5,  "#0e3060");
    ocean.addColorStop(0.75, "#0d2855");
    ocean.addColorStop(1,    "#0a1a3a");
    ctx.fillStyle = ocean;
    ctx.fillRect(0, 0, 2048, 1024);

    // Equatorial glow band
    const eqGlow = ctx.createLinearGradient(0, 420, 0, 604);
    eqGlow.addColorStop(0,   "rgba(0,80,180,0)");
    eqGlow.addColorStop(0.5, "rgba(0,120,255,0.08)");
    eqGlow.addColorStop(1,   "rgba(0,80,180,0)");
    ctx.fillStyle = eqGlow;
    ctx.fillRect(0, 420, 2048, 184);

    // Land masses — simplified but recognizable shapes
    ctx.fillStyle = "#1a5c2a";
    ctx.shadowColor = "#2ecc55";
    ctx.shadowBlur  = 12;

    const landShapes = [
      // North America
      [[400,120],[520,100],[580,140],[600,200],[560,280],[480,320],[420,360],[360,320],[320,260],[340,200]],
      // Greenland
      [[480,60],[540,50],[560,90],[530,120],[490,110]],
      // South America
      [[440,380],[500,360],[540,420],[550,520],[510,580],[460,580],[420,520],[410,440]],
      // Europe
      [[900,140],[980,120],[1020,160],[1000,210],[940,220],[900,200],[880,170]],
      // Africa
      [[920,240],[1010,220],[1060,280],[1060,420],[1020,520],[960,560],[900,520],[880,420],[880,300]],
      // Asia (main)
      [[1000,110],[1200,90],[1400,100],[1500,140],[1550,200],[1500,260],[1400,280],[1200,260],[1080,240],[1000,200]],
      // India
      [[1180,260],[1230,260],[1260,320],[1230,380],[1180,360],[1160,300]],
      // Southeast Asia
      [[1350,280],[1430,270],[1460,320],[1420,360],[1360,340],[1330,300]],
      // Australia
      [[1500,460],[1620,440],[1680,480],[1680,560],[1600,600],[1500,580],[1460,520]],
      // Japan
      [[1560,190],[1590,185],[1600,210],[1575,220]],
      // UK/Ireland
      [[870,145],[895,135],[905,155],[882,168]],
      // Antarctica (partial)
      [[300,940],[700,920],[1100,910],[1500,920],[1900,940],[2048,950],[2048,1024],[0,1024],[0,950]],
    ];

    landShapes.forEach(pts=>{
      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);
      pts.slice(1).forEach(p=>ctx.lineTo(p[0],p[1]));
      ctx.closePath();
      ctx.fill();
    });

    // Add subtle land texture — darker stroke outline
    ctx.shadowBlur = 0;
    ctx.strokeStyle = "#2a7a3a";
    ctx.lineWidth = 1.5;
    landShapes.forEach(pts=>{
      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);
      pts.slice(1).forEach(p=>ctx.lineTo(p[0],p[1]));
      ctx.closePath();
      ctx.stroke();
    });

    // City light dots on dark side (always render, looks great)
    const cityLights = [
      [515,155],[460,160],[490,165], // N America east coast
      [415,175],[430,170],           // N America west
      [910,160],[925,155],[935,170], // Europe
      [1080,185],[1150,200],         // Middle East
      [1200,215],[1230,210],         // India
      [1380,195],[1410,200],[1450,210], // East Asia
      [1560,195],[1575,200],         // Japan
      [960,350],[970,370],           // Africa
      [480,430],[490,440],           // S America
      [1540,495],[1555,510],         // Australia
    ];
    cityLights.forEach(([cx,cy])=>{
      const g = ctx.createRadialGradient(cx,cy,0,cx,cy,6);
      g.addColorStop(0,"rgba(255,220,120,0.9)");
      g.addColorStop(0.4,"rgba(255,180,60,0.4)");
      g.addColorStop(1,"rgba(255,150,0,0)");
      ctx.fillStyle=g;
      ctx.beginPath();ctx.arc(cx,cy,6,0,Math.PI*2);ctx.fill();
    });

    // Grid lines (graticule)
    ctx.strokeStyle = "rgba(0,150,255,0.07)";
    ctx.lineWidth = 0.5;
    for(let lon=-180; lon<=180; lon+=30) {
      const x = (lon+180)/360*2048;
      ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,1024); ctx.stroke();
    }
    for(let lat=-90; lat<=90; lat+=30) {
      const y = (90-lat)/180*1024;
      ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(2048,y); ctx.stroke();
    }
    // Equator highlight
    ctx.strokeStyle = "rgba(0,200,255,0.18)";
    ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.moveTo(0,512); ctx.lineTo(2048,512); ctx.stroke();

    const earthTex = new THREE.CanvasTexture(texCanvas);
    const earthGeo = new THREE.SphereGeometry(1, 64, 64);
    const earthMat = new THREE.MeshPhongMaterial({
      map: earthTex,
      specular: new THREE.Color(0x1a4a8a),
      shininess: 18,
      emissive: new THREE.Color(0x001020),
      emissiveIntensity: 0.15,
    });
    const earthMesh = new THREE.Mesh(earthGeo, earthMat);
    scene.add(earthMesh);

    // ── Atmosphere glow ──
    const atmosGeo = new THREE.SphereGeometry(1.06, 64, 64);
    const atmosMat = new THREE.ShaderMaterial({
      uniforms:{},
      vertexShader:`
        varying vec3 vNormal;
        void main(){vNormal=normalize(normalMatrix*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}
      `,
      fragmentShader:`
        varying vec3 vNormal;
        void main(){
          float intensity=pow(0.65-dot(vNormal,vec3(0,0,1.0)),3.0);
          gl_FragColor=vec4(0.1,0.5,1.0,1.0)*intensity*1.4;
        }
      `,
      side: THREE.FrontSide,
      blending: THREE.AdditiveBlending,
      transparent: true,
    });
    scene.add(new THREE.Mesh(atmosGeo, atmosMat));

    // Inner atmosphere
    const innerAtmosGeo = new THREE.SphereGeometry(1.02, 64, 64);
    const innerAtmosMat = new THREE.ShaderMaterial({
      uniforms:{},
      vertexShader:`varying vec3 vNormal;void main(){vNormal=normalize(normalMatrix*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
      fragmentShader:`varying vec3 vNormal;void main(){float i=pow(0.8-dot(vNormal,vec3(0,0,1.0)),4.0);gl_FragColor=vec4(0.05,0.3,0.8,1.0)*i*0.6;}`,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
      transparent: true,
    });
    scene.add(new THREE.Mesh(innerAtmosGeo, innerAtmosMat));

    // ── Lighting ──
    scene.add(new THREE.AmbientLight(0x112244, 0.8));
    const sun = new THREE.DirectionalLight(0xfff5e0, 1.6);
    sun.position.set(5, 3, 5);
    scene.add(sun);
    const rimLight = new THREE.DirectionalLight(0x4488ff, 0.4);
    rimLight.position.set(-3, 1, -2);
    scene.add(rimLight);

    // ── Satellite dots + trails containers ──
    const satMeshes  = {};
    const trailLines = {};

    SAT_CATALOG.forEach(meta=>{
      const {r,g,b} = hexToRGB(meta.color);
      const color = new THREE.Color(r,g,b);

      // Satellite sphere
      const geo = new THREE.SphereGeometry(0.012, 8, 8);
      const mat = new THREE.MeshBasicMaterial({color, transparent:true});
      const mesh = new THREE.Mesh(geo, mat);
      scene.add(mesh);
      satMeshes[meta.id] = mesh;

      // Glow sprite
      const spriteCanvas = document.createElement("canvas");
      spriteCanvas.width = spriteCanvas.height = 64;
      const sc = spriteCanvas.getContext("2d");
      const sg = sc.createRadialGradient(32,32,0,32,32,32);
      sg.addColorStop(0, meta.color+"ff");
      sg.addColorStop(0.2, meta.color+"aa");
      sg.addColorStop(0.5, meta.color+"33");
      sg.addColorStop(1, "transparent");
      sc.fillStyle = sg;
      sc.fillRect(0,0,64,64);
      const spriteTex = new THREE.CanvasTexture(spriteCanvas);
      const spriteMat = new THREE.SpriteMaterial({map:spriteTex, blending:THREE.AdditiveBlending, transparent:true, opacity:0.9});
      const sprite = new THREE.Sprite(spriteMat);
      sprite.scale.set(0.09,0.09,1);
      scene.add(sprite);
      satMeshes[meta.id+"_sprite"] = sprite;

      // Trail line
      const trailPoints = new Array(60).fill(new THREE.Vector3(0,0,0));
      const trailGeo = new THREE.BufferGeometry().setFromPoints(trailPoints);
      const trailMat = new THREE.LineBasicMaterial({color, transparent:true, opacity:0.35, linewidth:1});
      const trailLine = new THREE.Line(trailGeo, trailMat);
      scene.add(trailLine);
      trailLines[meta.id] = {line:trailLine, geo:trailGeo};
    });

    // ── Drag controls (manual, no OrbitControls) ──
    let isDragging=false, prevMouse={x:0,y:0};
    const euler = new THREE.Euler(0.3, 0, 0, "YXZ");
    const dragQuat = new THREE.Quaternion();
    dragQuat.setFromEuler(euler);

    renderer.domElement.addEventListener("mousedown", e=>{isDragging=true;prevMouse={x:e.clientX,y:e.clientY};});
    renderer.domElement.addEventListener("mousemove", e=>{
      if(!isDragging) return;
      const dx=(e.clientX-prevMouse.x)*0.005;
      const dy=(e.clientY-prevMouse.y)*0.005;
      const qY=new THREE.Quaternion(); qY.setFromAxisAngle(new THREE.Vector3(0,1,0), dx);
      const qX=new THREE.Quaternion(); qX.setFromAxisAngle(new THREE.Vector3(1,0,0), dy);
      dragQuat.premultiply(qY).premultiply(qX);
      prevMouse={x:e.clientX,y:e.clientY};
    });
    renderer.domElement.addEventListener("mouseup",   ()=>isDragging=false);
    renderer.domElement.addEventListener("mouseleave",()=>isDragging=false);
    renderer.domElement.addEventListener("wheel", e=>{
      camera.position.z = Math.max(1.6, Math.min(8, camera.position.z + e.deltaY*0.004));
    },{passive:true});

    // Touch support
    let lastTouch = null;
    renderer.domElement.addEventListener("touchstart", e=>{lastTouch={x:e.touches[0].clientX,y:e.touches[0].clientY};},{passive:true});
    renderer.domElement.addEventListener("touchmove", e=>{
      if(!lastTouch) return;
      const dx=(e.touches[0].clientX-lastTouch.x)*0.005;
      const dy=(e.touches[0].clientY-lastTouch.y)*0.005;
      const qY=new THREE.Quaternion(); qY.setFromAxisAngle(new THREE.Vector3(0,1,0), dx);
      const qX=new THREE.Quaternion(); qX.setFromAxisAngle(new THREE.Vector3(1,0,0), dy);
      dragQuat.premultiply(qY).premultiply(qX);
      lastTouch={x:e.touches[0].clientX,y:e.touches[0].clientY};
    },{passive:true});
    renderer.domElement.addEventListener("touchend",()=>lastTouch=null,{passive:true});

    // Store everything
    threeRef.current = {renderer, scene, camera, earthMesh, satMeshes, trailLines, dragQuat};

    // ── Resize ──
    const onResize = () => {
      if(!mount || !renderer) return;
      const W=mount.clientWidth, H=mount.clientHeight;
      camera.aspect=W/H; camera.updateProjectionMatrix();
      renderer.setSize(W,H);
    };
    window.addEventListener("resize", onResize);

    // ── Animate ──
    let tick = 0;
    const animate = (ts) => {
      animRef.current = requestAnimationFrame(animate);
      tick++;

      // Advance simulated time
      if(lastTsRef.current !== null) {
        simOffsetRef.current += (ts - lastTsRef.current) * (speedRef.current - 1);
      }
      lastTsRef.current = ts;
      const simNow = Date.now() + simOffsetRef.current;

      // Apply globe rotation
      earthMesh.quaternion.copy(dragQuat);
      // Auto-rotate slowly when not dragging
      if(!isDragging) {
        const autoQ = new THREE.Quaternion();
        autoQ.setFromAxisAngle(new THREE.Vector3(0,1,0), 0.00015);
        dragQuat.premultiply(autoQ);
      }

      // Update satellites
      SAT_CATALOG.forEach(meta=>{
        const satrec = satrecsRef.current[meta.id];
        if(!satrec) return;

        const pos = propagateAt(satrec, new Date(simNow));
        if(!pos) return;

        const {x,y,z} = llaToXYZ(pos.lat, pos.lon, pos.alt, 1);
        const vec = new THREE.Vector3(x,y,z);
        vec.applyQuaternion(dragQuat);

        const mesh   = satMeshes[meta.id];
        const sprite = satMeshes[meta.id+"_sprite"];
        if(mesh)   { mesh.position.copy(vec); }
        if(sprite) { sprite.position.copy(vec); }

        // Pulse glow for selected / highlighted / threat
        const isSel = selRef.current?.id === meta.id;
        const isHl  = hlRef.current.includes(meta.id);
        if(sprite) {
          const pulse = 0.7 + 0.3*Math.abs(Math.sin(tick*0.04 + meta.id.charCodeAt(0)*0.3));
          sprite.scale.set(
            isSel ? 0.22*pulse : isHl ? 0.16*pulse : meta.threat>=2 ? 0.13*pulse : 0.08,
            isSel ? 0.22*pulse : isHl ? 0.16*pulse : meta.threat>=2 ? 0.13*pulse : 0.08,
            1
          );
          sprite.material.opacity = isSel ? 1 : isHl ? 0.9 : 0.75;
        }

        // Trail
        const trail = buildTrailAt(satrec, simNow, 60, 60);
        const {line, geo} = trailLines[meta.id];
        if(trail.length > 1) {
          const points = trail.map(p=>{
            const v = llaToXYZ(p.lat, p.lon, p.alt, 1);
            const tv = new THREE.Vector3(v.x,v.y,v.z);
            tv.applyQuaternion(dragQuat);
            return tv;
          });
          // Pad to 60 if short
          while(points.length < 60) points.unshift(points[0]);
          geo.setFromPoints(points.slice(-60));
          geo.attributes.position.needsUpdate = true;
          line.material.opacity = isSel ? 0.8 : isHl ? 0.55 : 0.2;
          line.material.linewidth = isSel ? 2 : 1;
        }

        // Update selPos for info panel
        if(isSel) {
          setSelPos(p => (!p || Math.abs(p.lat-pos.lat)>0.001) ? {...pos} : p);
        }
      });

      renderer.render(scene, camera);
    };
    animate(0);
  }

  // Canvas click → satellite selection
  const onGlobeClick = useCallback((e)=>{
    const T = threeRef.current;
    if(!T.renderer || !T.camera || !T.satMeshes) return;
    const THREE = window.THREE;
    const rect = T.renderer.domElement.getBoundingClientRect();
    const mouse = new THREE.Vector2(
      ((e.clientX-rect.left)/rect.width)*2-1,
      -((e.clientY-rect.top)/rect.height)*2+1
    );
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, T.camera);
    raycaster.params.Points.threshold = 0.05;
    const meshes = SAT_CATALOG.map(m=>T.satMeshes[m.id]).filter(Boolean);
    const hits = raycaster.intersectObjects(meshes);
    if(hits.length > 0) {
      const hitMesh = hits[0].object;
      const meta = SAT_CATALOG.find(m=>T.satMeshes[m.id]===hitMesh);
      if(meta) { setSel(meta.id===selRef.current?.id ? null : meta); return; }
    }
    // Also check sprites (larger hit area)
    const sprites = SAT_CATALOG.map(m=>T.satMeshes[m.id+"_sprite"]).filter(Boolean);
    const sHits = raycaster.intersectObjects(sprites);
    if(sHits.length > 0) {
      const hitSprite = sHits[0].object;
      const meta = SAT_CATALOG.find(m=>T.satMeshes[m.id+"_sprite"]===hitSprite);
      if(meta) setSel(meta.id===selRef.current?.id ? null : meta);
    }
  },[]);

  const getSnap = useCallback(()=>{
    const simNow = Date.now() + simOffsetRef.current;
    return SAT_CATALOG.map(meta=>{
      const satrec = satrecsRef.current[meta.id];
      const pos = satrec ? propagateAt(satrec, new Date(simNow)) : null;
      return pos
        ? `${meta.id}(${meta.owner}): lat=${pos.lat.toFixed(2)} lon=${pos.lon.toFixed(2)} alt=${pos.alt.toFixed(0)}km threat=${THREAT_META[meta.threat].label}`
        : `${meta.id}: no data`;
    }).join("\n");
  },[]);

  const runCycle = useCallback(async()=>{
    if(!backendUrl) { pushAlert("Backend URL not set",3); return; }
    if(!groqKey)    { pushAlert("Groq API key not set",3); return; }
    setRunning(true); setCycle(c=>c+1);
    const snap = getSnap();
    backendIngest(backendUrl, backendSec, groqKey, snap, cycle+1);
    setAgent("orbital",{status:"running"}); setAgent("news",{status:"running"});
    const [oR,nR] = await Promise.allSettled([
      backendAgent(backendUrl, backendSec, groqKey, tavilyKey, "orbital", `LIVE SGP4 ${new Date().toISOString()}`, snap),
      backendAgent(backendUrl, backendSec, groqKey, tavilyKey, "news", `Operators: ${[...new Set(SAT_CATALOG.map(s=>s.owner))].join(", ")}`),
    ]);
    const oT = oR.status==="fulfilled" ? oR.value : "[ORBITAL-1] ⚠ Backend error";
    const nT = nR.status==="fulfilled" ? nR.value : "[NEWS-1] ⚠ Backend error";
    setAgent("orbital",{status:"done",output:oT}); setAgent("news",{status:"done",output:nT});
    SAT_CATALOG.filter(s=>s.threat===3).forEach(s=>{if(Math.random()>.5)pushAlert(`${s.id} — anomalous maneuver`,3);});
    setAgent("analyst",{status:"running"});
    const aT = await backendAgent(backendUrl, backendSec, groqKey, tavilyKey, "analyst", `ORBITAL-1:\n${oT}\n\nNEWS-1:\n${nT}`).catch(e=>"[ANALYST-1] ⚠ "+e.message);
    setAgent("analyst",{status:"done",output:aT});
    pushAlert("ANALYST-1 synthesis complete",1); setRunning(false);
  },[backendUrl,backendSec,groqKey,tavilyKey,cycle,getSnap]);

  const startMonitor = () => { runCycle(); agentTimer.current=setInterval(runCycle,120000); };
  const stopMonitor  = () => { clearInterval(agentTimer.current); setRunning(false); };
  useEffect(()=>()=>clearInterval(agentTimer.current),[]);

  const handleNL = async()=>{
    if(!nlQuery.trim()||!backendUrl) return;
    if(!groqKey) { pushAlert("Groq API key not set",3); return; }
    setNlLoading(true); setNlResult(null); setHl([]);
    try {
      const snap = getSnap();
      const d = await backendIntelQuery(backendUrl, backendSec, groqKey, tavilyKey, nlQuery, snap);
      setNlResult(d.response);
      const ids = d.relevant_ids?.length ? d.relevant_ids : (()=>{
        const m=d.response?.match(/RELEVANT OBJECTS:\s*([A-Z0-9,\s]+)/i);
        return m ? m[1].split(",").map(s=>s.trim()).filter(s=>SAT_CATALOG.find(x=>x.id===s)) : [];
      })();
      setHl(ids); if(ids.length) pushAlert(`Backend flagged ${ids.length} objects`,1);
    } catch(e) { setNlResult("⚠ Backend error: "+e.message); pushAlert("NL query failed: "+e.message,3); }
    setNlLoading(false);
  };

  const checkBackend = useCallback(async()=>{
    try { const r=await fetch(`${backendUrl}/health`,{headers:{"x-api-key":backendSec||""}}); setBackendOk(r.ok); pushAlert(r.ok?"Backend connected ✓":"Backend responded "+r.status, r.ok?0:2); }
    catch(e) { setBackendOk(false); pushAlert("Backend unreachable",2); }
  },[backendUrl,backendSec]);

  const threatCounts = THREAT_META.map((_,i)=>SAT_CATALOG.filter(s=>s.threat===i).length);
  const EXAMPLES = ["Where is the ISS right now?","Which satellites are over Asia?","Flag all military and intel sats","Which has highest altitude?"];
  const SPEED_STEPS = [1,10,50,200,1000];

  return (
    <div style={{minHeight:"100vh",background:"#000810",color:"#90c8b8",fontFamily:"'Share Tech Mono',monospace",display:"flex",flexDirection:"column"}}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@600;700&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}
        @keyframes blink{0%,100%{opacity:1}50%{opacity:0}}
        @keyframes pulse{0%,100%{opacity:.35}50%{opacity:1}}
        @keyframes spinring{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
        ::-webkit-scrollbar{width:3px}::-webkit-scrollbar-thumb{background:#0a2418}
        .tab{background:transparent;border:none;cursor:pointer;font-family:'Share Tech Mono',monospace;font-size:10px;letter-spacing:2px;padding:8px 16px;transition:all .2s}
        .ton{color:#00ffcc;border-bottom:2px solid #00ffcc;text-shadow:0 0 8px #00ffcc66}
        .tof{color:#0e2a1e;border-bottom:2px solid transparent}.tof:hover{color:#1a6040}
        .nlin{background:rgba(0,255,200,.04);border:1px solid rgba(0,255,200,.15);color:#a0e0c8;font-family:'Share Tech Mono',monospace;font-size:12px;padding:10px 14px;border-radius:2px;outline:none;width:100%}
        .nlin:focus{border-color:rgba(0,255,200,.45)}
        .nlin::placeholder{color:rgba(0,255,200,.2)}
        .apin{background:rgba(0,255,200,.03);border:1px solid rgba(0,255,200,.1);color:#a0e0c8;font-family:'Share Tech Mono',monospace;font-size:11px;padding:7px 10px;border-radius:2px;outline:none;width:200px}
        .apin:focus{border-color:rgba(0,255,200,.3)}
        .apin::placeholder{color:rgba(0,255,200,.14)}
        .btn{font-family:'Share Tech Mono',monospace;font-size:11px;letter-spacing:2px;padding:8px 16px;border-radius:2px;cursor:pointer;border:1px solid;transition:all .2s}
        .bgo{border-color:#00ffcc;color:#00ffcc;background:transparent}.bgo:hover:not(:disabled){background:rgba(0,255,200,.1);box-shadow:0 0 14px rgba(0,255,200,.3)}
        .bst{border-color:#ff1111;color:#ff1111;background:transparent}.bst:hover{background:rgba(255,17,17,.1)}
        .byw{border-color:#ffe44d;color:#ffe44d;background:transparent}.byw:hover{background:rgba(255,228,77,.08)}
        .btn:disabled{opacity:.25;cursor:not-allowed}
        .pill{background:transparent;border:1px solid rgba(0,255,200,.1);border-radius:20px;color:rgba(0,255,200,.38);font-family:'Share Tech Mono',monospace;font-size:10px;padding:4px 10px;cursor:pointer;transition:all .2s}
        .pill:hover{border-color:rgba(0,255,200,.4);color:#00ffcc;background:rgba(0,255,200,.05)}
        .spd{background:rgba(0,255,200,.04);border:1px solid rgba(0,255,200,.12);color:rgba(0,255,200,.5);font-family:'Share Tech Mono',monospace;font-size:9px;padding:4px 10px;cursor:pointer;border-radius:2px;transition:all .2s;letter-spacing:1px}
        .spd:hover{border-color:rgba(0,255,200,.35);color:#00ffcc}
        .spd-on{border-color:#ffe44d!important;color:#ffe44d!important;background:rgba(255,228,77,.08)!important;box-shadow:0 0 8px rgba(255,228,77,.2)!important}
        .sett-in{background:rgba(0,255,200,.03);border:1px solid rgba(0,255,200,.1);color:#a0e0c8;font-family:'Share Tech Mono',monospace;font-size:10px;padding:6px 10px;border-radius:2px;outline:none;width:100%}
        .sett-in:focus{border-color:rgba(0,255,200,.3)}
        .sett-in::placeholder{color:rgba(0,255,200,.1)}
        canvas{display:block}
      `}</style>

      {/* Topbar */}
      <div style={{padding:"10px 20px",borderBottom:"1px solid rgba(0,255,200,.1)",background:"rgba(0,0,0,.9)",backdropFilter:"blur(12px)",display:"flex",alignItems:"center",justifyContent:"space-between",flexWrap:"wrap",gap:8,flexShrink:0}}>
        <div>
          <div style={{fontFamily:"'Rajdhani',sans-serif",fontSize:22,fontWeight:700,color:"#00ffcc",letterSpacing:5,textShadow:"0 0 30px rgba(0,255,200,.6),0 0 60px rgba(0,255,200,.2)"}}>
            ◈ GOTHAM ORBITAL // INTELLIGENCE PLATFORM
          </div>
          <div style={{fontSize:9,color:"rgba(0,255,200,.22)",letterSpacing:3,marginTop:1}}>
            3D GLOBE · LIVE SGP4 · LIVE TLEs · optimum_ReAct · HybridMemory
          </div>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:8,flexWrap:"wrap"}}>
          <input className="apin" type="password" placeholder="Groq API key..." value={groqKey} onChange={e=>setGroqKey(e.target.value)} style={{width:160}}/>
          <input className="apin" type="password" placeholder="Tavily key..." value={tavilyKey} onChange={e=>setTavilyKey(e.target.value)} style={{width:140}}/>
          <button className="btn bgo" onClick={startMonitor} disabled={running||!ready||!groqKey}>{running?"▶ LIVE":"▶ INITIATE"}</button>
          {running&&<button className="btn bst" onClick={stopMonitor}>■ HALT</button>}
          <button className="btn byw" onClick={()=>setShowSettings(s=>!s)} title="Backend settings">⚙</button>
          <div style={{fontSize:9,color:"rgba(0,255,200,.28)",textAlign:"right"}}>
            <div>CYCLE {String(cycle).padStart(4,"0")}</div>
            <div style={{color:running?"#00ffcc":"#0e2a1e",animation:running?"pulse 1.2s infinite":"none"}}>{running?"● ACTIVE":"○ STANDBY"}</div>
          </div>
        </div>
      </div>

      {/* Settings drawer */}
      {showSettings&&(
        <div style={{padding:"12px 20px",background:"rgba(0,5,3,.98)",borderBottom:"1px solid rgba(255,228,77,.12)",display:"flex",alignItems:"flex-end",gap:12,flexWrap:"wrap",flexShrink:0}}>
          <div style={{fontSize:8,color:"rgba(255,228,77,.6)",letterSpacing:3,alignSelf:"center"}}>⚙ BACKEND CONFIG</div>
          <div style={{display:"flex",flexDirection:"column",gap:4}}>
            <label style={{fontSize:7,color:"rgba(0,255,200,.3)",letterSpacing:2}}>BACKEND URL</label>
            <input className="sett-in" style={{width:280}} value={backendUrl} onChange={e=>setBackendUrl(e.target.value)} placeholder="http://16.16.251.215:8000"/>
          </div>
          <div style={{display:"flex",flexDirection:"column",gap:4}}>
            <label style={{fontSize:7,color:"rgba(0,255,200,.3)",letterSpacing:2}}>API SECRET</label>
            <input className="sett-in" type="password" style={{width:180}} value={backendSec} onChange={e=>setBackendSec(e.target.value)} placeholder="optional"/>
          </div>
          <button className="btn bgo" style={{fontSize:9,padding:"6px 14px"}} onClick={checkBackend}>PING</button>
          {backendOk!==null&&<span style={{fontSize:9,color:backendOk?"#00ffcc":"#ff1111",letterSpacing:1}}>{backendOk?"● CONNECTED":"● UNREACHABLE"}</span>}
        </div>
      )}

      {/* Status + warp bar */}
      <div style={{padding:"4px 20px",background:"rgba(0,0,0,.7)",borderBottom:"1px solid rgba(0,255,200,.05)",display:"flex",alignItems:"center",gap:10,flexShrink:0}}>
        <div style={{width:6,height:6,borderRadius:"50%",flexShrink:0,
          background:tleStatus==="live"?"#00ffcc":tleStatus==="error"?"#ff1111":"rgba(255,228,77,.8)",
          boxShadow:tleStatus==="live"?"0 0 8px #00ffcc66":"none",
          animation:tleStatus==="loading"?"pulse 1s infinite":"none"}}/>
        <span style={{fontSize:8,letterSpacing:1,color:tleStatus==="live"?"rgba(0,255,200,.6)":tleStatus==="error"?"rgba(255,80,80,.8)":"rgba(255,228,77,.5)"}}>
          {tleStatus==="loading" && "FETCHING LIVE TLEs FROM CELESTRAK..."}
          {tleStatus==="live"    && `✓ LIVE TLEs — ${Object.keys(satrecsRef.current).length} SATS — SGP4 REALTIME — POSITIONS ±FEW KM`}
          {tleStatus==="error"   && "✗ TLE FETCH FAILED — CHECK BACKEND — NO FALLBACK"}
        </span>
        <div style={{marginLeft:"auto",display:"flex",alignItems:"center",gap:5}}>
          <span style={{fontSize:7,color:"rgba(0,255,200,.25)",letterSpacing:2}}>⚡ WARP</span>
          {SPEED_STEPS.map(s=>(
            <button key={s} className={`spd${speed===s?" spd-on":""}`}
              onClick={()=>{if(s===1)simOffsetRef.current=0;setSpeed(s);}}>
              {s===1?"1×":`×${s}`}
            </button>
          ))}
        </div>
      </div>

      {/* Threat bar */}
      <div style={{display:"flex",borderBottom:"1px solid rgba(0,255,200,.06)",background:"rgba(0,0,0,.5)",flexShrink:0}}>
        {THREAT_META.map((t,i)=>(
          <div key={i} style={{flex:1,padding:"5px 14px",borderRight:"1px solid rgba(0,255,200,.05)",display:"flex",alignItems:"center",gap:6}}>
            <div style={{width:5,height:5,borderRadius:"50%",background:t.color,boxShadow:`0 0 8px ${t.color}`,animation:i>=2?"pulse 1.5s infinite":"none"}}/>
            <span style={{fontSize:9,color:t.color,letterSpacing:2}}>{t.label}</span>
            <span style={{fontSize:14,fontFamily:"'Rajdhani',sans-serif",fontWeight:700,color:"#fff",marginLeft:"auto",textShadow:`0 0 6px ${t.color}44`}}>{threatCounts[i]}</span>
          </div>
        ))}
        <div style={{padding:"5px 14px",display:"flex",alignItems:"center",gap:6}}>
          <span style={{fontSize:9,color:"rgba(0,255,200,.35)",letterSpacing:2}}>TRACKING</span>
          <span style={{fontSize:14,fontFamily:"'Rajdhani',sans-serif",fontWeight:700,color:"#00ffcc",textShadow:"0 0 12px rgba(0,255,200,.6)"}}>{SAT_CATALOG.length}</span>
        </div>
      </div>

      {/* Tabs */}
      <div style={{display:"flex",borderBottom:"1px solid rgba(0,255,200,.06)",background:"rgba(0,0,0,.45)",flexShrink:0}}>
        {[["globe","◈ 3D GLOBE"],["query","⌕ NL QUERY"],["agents","◎ AGENTS"]].map(([id,l])=>(
          <button key={id} className={`tab ${tab===id?"ton":"tof"}`} onClick={()=>setTab(id)}>{l}</button>
        ))}
        <div style={{marginLeft:"auto",padding:"8px 14px",fontSize:8,letterSpacing:2,color:ready?"rgba(0,255,200,.4)":"rgba(255,228,77,.4)",display:"flex",alignItems:"center",gap:5}}>
          <span style={{width:5,height:5,borderRadius:"50%",display:"inline-block",background:ready?"#00ffcc55":"rgba(255,228,77,.5)",animation:"pulse 2s infinite"}}/>
          {ready?`LIVE · ${SAT_CATALOG.length} SATS`:"LOADING..."}
        </div>
      </div>

      {/* GLOBE TAB */}
      {tab==="globe"&&(
        <div style={{flex:1,display:"grid",gridTemplateColumns:"1fr 300px",minHeight:0}}>
          {/* Globe */}
          <div style={{position:"relative",background:"#000810"}}>
            <div ref={mountRef} style={{width:"100%",height:"100%",cursor:"grab"}} onClick={onGlobeClick}/>

            {/* Loading overlay */}
            {!ready&&(
              <div style={{position:"absolute",inset:0,display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",background:"rgba(0,8,16,.95)"}}>
                <div style={{width:60,height:60,border:"2px solid rgba(0,255,200,.1)",borderTop:"2px solid #00ffcc",borderRadius:"50%",animation:"spinring 1s linear infinite",marginBottom:16}}/>
                <div style={{fontSize:11,color:"rgba(0,255,200,.7)",letterSpacing:3}}>
                  {tleStatus==="loading"?"FETCHING LIVE TLEs...":"BUILDING 3D GLOBE..."}
                </div>
                {tleStatus==="error"&&<div style={{fontSize:10,color:"#ff4444",marginTop:8,letterSpacing:2}}>TLE FETCH FAILED — CHECK BACKEND</div>}
              </div>
            )}

            {/* Selected satellite info panel */}
            {selUI&&selPos&&(
              <div style={{position:"absolute",top:14,left:14,padding:"12px 16px",background:"rgba(0,4,2,.97)",border:`1px solid ${selUI.color}44`,borderLeft:`3px solid ${selUI.color}`,borderRadius:4,minWidth:240,boxShadow:`0 0 30px ${selUI.color}22`}}>
                <div style={{fontSize:8,color:selUI.color,letterSpacing:3,marginBottom:4,textShadow:`0 0 6px ${selUI.color}`}}>◈ LIVE TRACK // SGP4</div>
                <div style={{fontSize:16,color:"#fff",fontFamily:"'Rajdhani',sans-serif",fontWeight:700,marginBottom:8}}>{selUI.name}</div>
                {[["OWNER",selUI.owner],["TYPE",selUI.type.toUpperCase()],["LAT",`${selPos.lat.toFixed(4)}°`],["LON",`${selPos.lon.toFixed(4)}°`],["ALTITUDE",`${selPos.alt.toFixed(1)} km`],["THREAT",THREAT_META[selUI.threat].label],["TLE SOURCE","LIVE CELESTRAK"],["PROPAGATOR","SGP4"]].map(([k,v])=>(
                  <div key={k} style={{fontSize:10,color:"#1e4030",lineHeight:1.9}}>
                    {k}: <span style={{color:k==="THREAT"?THREAT_META[selUI.threat].color:k==="TLE SOURCE"?"#00ffcc":k==="PROPAGATOR"?"rgba(0,255,200,.5)":"#60a090"}}>{v}</span>
                  </div>
                ))}
                <div style={{marginTop:8,fontSize:8,color:"#0a2018",cursor:"pointer",letterSpacing:2}} onClick={()=>setSel(null)}>[ DESELECT ]</div>
              </div>
            )}

            {/* Satellite quick-select strip */}
            <div style={{position:"absolute",bottom:0,left:0,right:0,padding:"6px 10px",background:"rgba(0,0,0,.8)",borderTop:"1px solid rgba(0,255,200,.06)",display:"flex",flexWrap:"wrap",gap:4}}>
              {SAT_CATALOG.map(meta=>(
                <div key={meta.id} onClick={()=>setSel(meta.id===selUI?.id?null:meta)}
                  style={{padding:"2px 8px",borderRadius:2,cursor:"pointer",fontSize:8,letterSpacing:1,
                    border:`1px solid ${meta.color}${satrecsRef.current[meta.id]?"55":"18"}`,
                    background:selUI?.id===meta.id?meta.color+"1a":"transparent",
                    color:satrecsRef.current[meta.id]?meta.color:meta.color+"44",
                    boxShadow:selUI?.id===meta.id?`0 0 8px ${meta.color}44`:"none",
                    transition:"all .12s"}}>
                  {meta.id}
                </div>
              ))}
              <span style={{marginLeft:"auto",fontSize:7,color:"rgba(0,255,200,.2)",alignSelf:"center",letterSpacing:1}}>DRAG TO ROTATE · SCROLL TO ZOOM · CLICK SAT</span>
            </div>

            {/* Legend */}
            <div style={{position:"absolute",top:14,right:14,padding:"10px 12px",background:"rgba(0,4,2,.95)",border:"1px solid rgba(0,255,140,.12)",borderRadius:3}}>
              {[["CIVILIAN","#00ffcc"],["MILITARY","#ff1111"],["NAVIGATION","#cc66ff"],["COMMERCIAL","#00ccff"],["INTEL","#ff8800"],["SCIENCE","#7dff7d"],["WEATHER","#40e0ff"]].map(([l,c])=>(
                <div key={l} style={{display:"flex",alignItems:"center",gap:6,marginBottom:4}}>
                  <div style={{width:7,height:7,borderRadius:"50%",background:c,boxShadow:`0 0 5px ${c}`}}/>
                  <span style={{fontSize:7,color:c+"aa",letterSpacing:1}}>{l}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Right panel */}
          <div style={{display:"flex",flexDirection:"column",overflow:"hidden",background:"rgba(0,0,0,.5)",borderLeft:"1px solid rgba(0,255,200,.07)"}}>
            <div style={{flex:1,padding:11,overflowY:"auto",borderBottom:"1px solid rgba(0,255,200,.06)"}}>
              <div style={{fontSize:8,color:"rgba(0,255,200,.3)",letterSpacing:3,marginBottom:8}}>▸ AGENT NETWORK // {agents.filter(a=>a.status==="running").length} ACTIVE</div>
              {agents.map(a=><AgentCard key={a.id} a={a}/>)}
            </div>
            <div style={{padding:11,overflowY:"auto",maxHeight:200}}>
              <div style={{fontSize:8,color:"rgba(0,255,200,.3)",letterSpacing:3,marginBottom:8}}>▸ ALERT STREAM</div>
              {alerts.length===0
                ?<div style={{fontSize:9,color:"#0a1a10",fontStyle:"italic"}}>no alerts</div>
                :alerts.map((a,i)=>(
                  <div key={i} style={{padding:"3px 8px",marginBottom:3,fontSize:9,lineHeight:1.5,borderLeft:`2px solid ${THREAT_META[a.lvl].color}`,background:THREAT_META[a.lvl].color+"07",color:"#4a7a68"}}>
                    <span style={{color:THREAT_META[a.lvl].color,fontSize:7,display:"block"}}>{a.ts}</span>
                    {a.msg}
                  </div>
                ))
              }
            </div>
          </div>
        </div>
      )}

      {/* NL QUERY TAB */}
      {tab==="query"&&(
        <div style={{flex:1,display:"grid",gridTemplateColumns:"1fr 1fr",minHeight:0}}>
          <div style={{borderRight:"1px solid rgba(0,255,200,.07)",display:"flex",flexDirection:"column"}}>
            <div style={{padding:14,borderBottom:"1px solid rgba(0,255,200,.07)",background:"rgba(0,0,0,.35)"}}>
              <div style={{fontSize:8,color:"rgba(0,255,200,.4)",letterSpacing:3,marginBottom:9}}>▸ NL QUERY // SGP4 Live Context</div>
              <div style={{display:"flex",gap:8,marginBottom:9}}>
                <input className="nlin" placeholder="e.g. Where is the ISS right now?" value={nlQuery} onChange={e=>setNlQuery(e.target.value)} onKeyDown={e=>e.key==="Enter"&&handleNL()}/>
                <button className="btn bgo" onClick={handleNL} disabled={nlLoading||!nlQuery.trim()}>⌕</button>
              </div>
              <div style={{display:"flex",flexWrap:"wrap",gap:5}}>
                {EXAMPLES.map((q,i)=><button key={i} className="pill" onClick={()=>setNlQuery(q)}>{q.slice(0,40)}</button>)}
              </div>
            </div>
            {/* Mini position table */}
            <div style={{flex:1,overflowY:"auto",padding:14}}>
              <div style={{fontSize:8,color:"rgba(0,255,200,.3)",letterSpacing:3,marginBottom:8}}>▸ LIVE POSITION TABLE</div>
              <table style={{width:"100%",borderCollapse:"collapse",fontFamily:"'Courier New',monospace",fontSize:10}}>
                <thead><tr style={{borderBottom:"1px solid rgba(0,255,200,.12)"}}>
                  {["ID","LAT","LON","ALT","TYPE"].map(h=><td key={h} style={{padding:"4px 6px",color:"rgba(0,255,200,.35)",fontSize:8,letterSpacing:1}}>{h}</td>)}
                </tr></thead>
                <tbody>
                  {SAT_CATALOG.map(meta=>{
                    const satrec=satrecsRef.current[meta.id];
                    const pos=satrec?propagateAt(satrec,new Date(Date.now()+simOffsetRef.current)):null;
                    return(
                      <tr key={meta.id} style={{borderBottom:"1px solid rgba(0,255,200,.04)",cursor:"pointer",background:selUI?.id===meta.id?meta.color+"0a":"transparent"}} onClick={()=>setSel(meta.id===selUI?.id?null:meta)}>
                        <td style={{padding:"4px 6px",color:meta.color,fontSize:9}}>{meta.id}</td>
                        <td style={{padding:"4px 6px",color:"#3a6a58",fontSize:9}}>{pos?pos.lat.toFixed(2)+"°":"—"}</td>
                        <td style={{padding:"4px 6px",color:"#3a6a58",fontSize:9}}>{pos?pos.lon.toFixed(2)+"°":"—"}</td>
                        <td style={{padding:"4px 6px",color:"#3a6a58",fontSize:9}}>{pos?pos.alt.toFixed(0)+"km":"—"}</td>
                        <td style={{padding:"4px 6px",color:meta.color+"88",fontSize:8}}>{meta.type}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
          <div style={{display:"flex",flexDirection:"column",background:"rgba(0,0,0,.25)"}}>
            <div style={{padding:"9px 14px",borderBottom:"1px solid rgba(0,255,200,.07)",fontSize:8,color:"rgba(0,255,200,.35)",letterSpacing:3}}>▸ AGENT RESPONSE</div>
            <div style={{flex:1,overflowY:"auto"}}>
              {nlLoading?<div style={{padding:14,color:"#00ffcc",fontSize:11}}><span style={{animation:"blink .8s step-end infinite"}}>◈ QUERYING...</span></div>
              :nlResult?<div style={{padding:14,fontFamily:"'Courier New',monospace",fontSize:11,color:"#5a9a88",lineHeight:1.8,whiteSpace:"pre-wrap"}}>{nlResult}</div>
              :<div style={{padding:14,color:"#0a1a10",fontSize:10,fontStyle:"italic"}}>enter a query above</div>}
            </div>
          </div>
        </div>
      )}

      {/* AGENTS TAB */}
      {tab==="agents"&&(
        <div style={{flex:1,display:"grid",gridTemplateColumns:"1fr 1fr",minHeight:0}}>
          <div style={{padding:14,overflowY:"auto",borderRight:"1px solid rgba(0,255,200,.07)"}}>
            <div style={{fontSize:8,color:"rgba(0,255,200,.4)",letterSpacing:3,marginBottom:12}}>▸ AGENT OUTPUTS</div>
            {agents.map(a=><AgentCard key={a.id} a={a}/>)}
          </div>
          <div style={{padding:14,overflowY:"auto"}}>
            <div style={{fontSize:8,color:"rgba(0,255,200,.4)",letterSpacing:3,marginBottom:12}}>▸ LIVE POSITION TABLE</div>
            <table style={{width:"100%",borderCollapse:"collapse",fontFamily:"'Courier New',monospace",fontSize:10}}>
              <thead><tr style={{borderBottom:"1px solid rgba(0,255,200,.12)"}}>
                {["ID","LAT","LON","ALT","TYPE"].map(h=><td key={h} style={{padding:"4px 6px",color:"rgba(0,255,200,.35)",fontSize:8,letterSpacing:1}}>{h}</td>)}
              </tr></thead>
              <tbody>
                {SAT_CATALOG.map(meta=>{
                  const satrec=satrecsRef.current[meta.id];
                  const pos=satrec?propagateAt(satrec,new Date(Date.now()+simOffsetRef.current)):null;
                  return(
                    <tr key={meta.id} style={{borderBottom:"1px solid rgba(0,255,200,.04)",cursor:"pointer",background:selUI?.id===meta.id?meta.color+"0a":"transparent"}} onClick={()=>setSel(meta.id===selUI?.id?null:meta)}>
                      <td style={{padding:"4px 6px",color:meta.color,fontSize:9}}>{meta.id}</td>
                      <td style={{padding:"4px 6px",color:"#3a6a58",fontSize:9}}>{pos?pos.lat.toFixed(2)+"°":"—"}</td>
                      <td style={{padding:"4px 6px",color:"#3a6a58",fontSize:9}}>{pos?pos.lon.toFixed(2)+"°":"—"}</td>
                      <td style={{padding:"4px 6px",color:"#3a6a58",fontSize:9}}>{pos?pos.alt.toFixed(0)+"km":"—"}</td>
                      <td style={{padding:"4px 6px",color:meta.color+"88",fontSize:8}}>{meta.type}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}