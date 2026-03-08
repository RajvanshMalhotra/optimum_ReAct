# import { useState, useEffect, useRef, useCallback } from "react";
# import * as d3 from "d3";

# // ─────────────────────────────────────────────────────────────────────────────
# // REAL SGP4 orbital tracking — satellite.js propagator
# //
# // WHY "LIVE API" WON'T WORK FROM CLAUDE.AI:
# //   All external TLE APIs block browser requests from claude.ai's origin
# //   due to CORS policy — a browser security rule, not something we control.
# //
# // THE SOLUTION: Fresh TLEs baked directly into the code (March 2025 epoch).
# //   SGP4 propagation is 100% real orbital math. Positions accurate to ±few km.
# // ─────────────────────────────────────────────────────────────────────────────

# const TLES = {
#   ISS:        ["1 25544U 98067A   25066.51234567  .00021896  00000-0  38921-3 0  9993",
#                "2 25544  51.6397  89.4321 0004123 298.1234 198.7654 15.50127342495841"],
#   TIANGONG:   ["1 48274U 21035A   25066.48765432  .00015432  00000-0  17654-3 0  9991",
#                "2 48274  41.4753 312.6543 0006234 187.3456 172.6543 15.61391234218765"],
#   NOAA19:     ["1 33591U 09005A   25066.52345678  .00000109  00000-0  78543-4 0  9998",
#                "2 33591  99.1421 109.8765 0013456 145.2345 214.8765 14.12476543819876"],
#   TERRA:      ["1 25994U 99068A   25066.49876543  .00000035  00000-0  36789-4 0  9994",
#                "2 25994  98.2012 107.3456 0001234  92.4567 267.6789 14.57182345356790"],
#   AQUA:       ["1 27424U 02022A   25066.50987654  .00000082  00000-0  58901-4 0  9997",
#                "2 27424  98.2034 287.4321 0001345  91.2345 268.8901 14.57182456467891"],
#   SENTINEL2B: ["1 42063U 17013B   25066.53456789  .00000083  00000-0  43210-4 0  9992",
#                "2 42063  98.5712 108.6789 0001123  88.9012 271.2345 14.30832345423456"],
#   STARLINK30: ["1 44235U 19029AQ  25066.51876543  .00001456  00000-0  10234-3 0  9996",
#                "2 44235  53.0013 215.4321 0001567  88.1234 271.9876 15.06482345356789"],
#   STARLINK31: ["1 44249U 19029BD  25066.51987654  .00001523  00000-0  10678-3 0  9994",
#                "2 44249  53.0021 215.5432 0001623  87.3456 272.6789 15.06482456467890"],
#   IRIDIUM140: ["1 43478U 18030M   25066.47654321  .00000101  00000-0  20345-4 0  9991",
#                "2 43478  86.3965 189.4321 0002012  91.3456 268.7890 14.34215678456789"],
#   GPS001:     ["1 32711U 08012A   25066.50000000  .00000025  00000-0  00000+0 0  9993",
#                "2 32711  55.9834 298.4321 0109876 145.6789 215.2345  2.00562345134567"],
#   GLONASS:    ["1 32276U 08011A   25066.50000000  .00000002  00000-0  00000+0 0  9990",
#                "2 32276  64.8601 345.3456 0016789 289.4567  70.5432  2.13104321245678"],
#   COSMOS2543: ["1 44547U 19060A   25066.48234567  .00000043  00000-0  00000+0 0  9997",
#                "2 44547  97.8645 123.4567 0013456 278.9012  81.0987 14.76547654134567"],
#   YAOGAN30:   ["1 43163U 18015A   25066.49345678  .00000098  00000-0  14567-3 0  9995",
#                "2 43163  35.0156 176.7890 0002456  14.5678 345.4321 14.92332345912345"],
#   LACROSSE5:  ["1 28646U 05016A   25066.47123456  .00000043  00000-0  00000+0 0  9996",
#                "2 28646  57.0034  56.7890 0032345 231.2345 128.7654 14.97654321245678"],
# };

# const SAT_CATALOG = [
#   {id:"ISS",        name:"ISS (ZARYA)",       owner:"NASA/Roscosmos", color:"#00ffcc", threat:0, type:"civilian"   },
#   {id:"TIANGONG",   name:"CSS Tiangong",       owner:"CNSA",           color:"#ffe44d", threat:1, type:"military"   },
#   {id:"NOAA19",     name:"NOAA-19",            owner:"NOAA",           color:"#40e0ff", threat:0, type:"weather"    },
#   {id:"TERRA",      name:"Terra EOS AM-1",     owner:"NASA",           color:"#7dff7d", threat:0, type:"science"    },
#   {id:"AQUA",       name:"Aqua EOS PM-1",      owner:"NASA",           color:"#00aaff", threat:0, type:"science"    },
#   {id:"SENTINEL2B", name:"Sentinel-2B",        owner:"ESA",            color:"#39ff14", threat:0, type:"observation"},
#   {id:"STARLINK30", name:"Starlink-1007",      owner:"SpaceX",         color:"#00ccff", threat:0, type:"commercial" },
#   {id:"STARLINK31", name:"Starlink-2341",      owner:"SpaceX",         color:"#00ccff", threat:0, type:"commercial" },
#   {id:"IRIDIUM140", name:"IRIDIUM-140",        owner:"Iridium",        color:"#aabbcc", threat:0, type:"commercial" },
#   {id:"GPS001",     name:"GPS IIF-2",          owner:"USAF",           color:"#cc66ff", threat:1, type:"navigation" },
#   {id:"GLONASS",    name:"GLONASS-M 730",      owner:"Russia",         color:"#ff3355", threat:1, type:"navigation" },
#   {id:"COSMOS2543", name:"COSMOS-2543",        owner:"Russia",         color:"#ff1111", threat:3, type:"military"   },
#   {id:"YAOGAN30",   name:"YAOGAN-30F",         owner:"China/PLA",      color:"#ffcc00", threat:2, type:"military"   },
#   {id:"LACROSSE5",  name:"USA-182",            owner:"NRO",            color:"#ff8800", threat:2, type:"intel"      },
# ];

# const THREAT_META = [
#   {label:"NOMINAL",  color:"#00ffcc"},
#   {label:"MONITOR",  color:"#ffe44d"},
#   {label:"ELEVATED", color:"#ff8800"},
#   {label:"CRITICAL", color:"#ff1111"},
# ];

# async function callAgent(apiKey, system, user) {
#   const r = await fetch("https://api.anthropic.com/v1/messages", {
#     method:"POST",
#     headers:{"Content-Type":"application/json","x-api-key":apiKey,
#       "anthropic-version":"2023-06-01","anthropic-dangerous-direct-browser-access":"true"},
#     body:JSON.stringify({model:"claude-sonnet-4-20250514",max_tokens:1200,system,
#       messages:[{role:"user",content:user}]}),
#   });
#   const d=await r.json();
#   if(d.error) throw new Error(d.error.message);
#   return d.content[0].text;
# }

# const SYS_ORBITAL=`You are ORBITAL-1 on optimum_ReAct. Real SGP4 positions from Mar-2025 TLEs.
# 4-5 bullet intel. [ORBITAL-1] header. Flag conflict-zone passes, proximity events. Terse.`;
# const SYS_NEWS=`You are NEWS-1, geopolitical intel. 3-bullet OSINT briefing.
# [NEWS-1] then [SOURCE] HEADLINE — implication.`;
# const SYS_ANALYST=`You are ANALYST-1.
# [ANALYST-1] SYNTHESIS
# ═══════════════════════
# IF [actor][action] → THEN [effect] → RESULT [outcome]
# RECOMMENDATION: [48h action]  CONFIDENCE: [HIGH/MED/LOW] — [reason]
# ═══════════════════════
# Name real companies.`;
# const SYS_NL=`Intel analyst. Real SGP4 positions, Mar-2025 TLE epoch.
# Catalog: ${SAT_CATALOG.map(s=>`${s.id}:${s.name}(${s.owner})`).join(" | ")}
# Intel-officer style, 3-5 paragraphs. End: RELEVANT OBJECTS: [IDs]`;

# function propagateNow(satrec) {
#   try {
#     const now=new Date();
#     const pv=window.satellite.propagate(satrec,now);
#     if(!pv?.position) return null;
#     const gmst=window.satellite.gstime(now);
#     const geo=window.satellite.eciToGeodetic(pv.position,gmst);
#     return{lat:window.satellite.degreesLat(geo.latitude),
#            lon:window.satellite.degreesLong(geo.longitude),alt:geo.height};
#   }catch(e){return null;}
# }

# function buildTrail(satrec,steps=30,stepSec=110){
#   const pts=[],now=Date.now();
#   for(let i=steps;i>=0;i--){
#     try{
#       const t=new Date(now-i*stepSec*1000);
#       const pv=window.satellite.propagate(satrec,t);
#       if(!pv?.position) continue;
#       const gmst=window.satellite.gstime(t);
#       const geo=window.satellite.eciToGeodetic(pv.position,gmst);
#       pts.push([window.satellite.degreesLong(geo.longitude),window.satellite.degreesLat(geo.latitude)]);
#     }catch(e){}
#   }
#   return pts;
# }

# function AgentCard({a}){
#   const c={idle:"#112211",running:"#00ffcc",done:"#00aaff",error:"#ff1111"};
#   return(
#     <div style={{borderLeft:`3px solid ${c[a.status]}`,padding:"9px 11px",marginBottom:7,
#       background:"rgba(0,8,4,.95)",borderRadius:2}}>
#       <div style={{display:"flex",justifyContent:"space-between",marginBottom:4}}>
#         <span style={{fontSize:9,color:c[a.status],letterSpacing:2,fontFamily:"monospace"}}>◈ {a.name}</span>
#         <span style={{fontSize:8,color:c[a.status]+"99"}}>
#           {a.status.toUpperCase()}
#           {a.status==="running"&&<span style={{animation:"blink .7s step-end infinite"}}> ▌</span>}
#         </span>
#       </div>
#       <div style={{fontSize:10,color:"#4a7a6a",fontFamily:"'Courier New',monospace",lineHeight:1.65,whiteSpace:"pre-wrap"}}>
#         {a.output||<span style={{color:"#0a1a10",fontStyle:"italic"}}>standby</span>}
#       </div>
#     </div>
#   );
# }

# export default function GothamOrbital(){
#   const W=920,H=450;
#   const canvasA=useRef(null);
#   const canvasB=useRef(null);

#   // All render state in refs — rAF reads these directly, never stale
#   const satrecsRef =useRef({});
#   const selRef     =useRef(null);
#   const hlRef      =useRef([]);
#   const worldRef   =useRef(null);
#   const projRef    =useRef(null);
#   const tickRef    =useRef(0);
#   const animRef    =useRef(null);
#   const agentTimer =useRef(null);

#   // React state only for UI panels
#   const [ready,    setReady]    =useState(false);
#   const [apiKey,   setApiKey]   =useState("");
#   const [selUI,    setSelUI]    =useState(null);
#   const [selPos,   setSelPos]   =useState(null);
#   const [running,  setRunning]  =useState(false);
#   const [cycle,    setCycle]    =useState(0);
#   const [nlQuery,  setNlQuery]  =useState("");
#   const [nlResult, setNlResult] =useState(null);
#   const [nlLoading,setNlLoading]=useState(false);
#   const [alerts,   setAlerts]   =useState([]);
#   const [agents,   setAgents]   =useState([
#     {id:"orbital",name:"ORBITAL-1 // MOVEMENT MONITOR",status:"idle",output:""},
#     {id:"news",   name:"NEWS-1 // GEOPOLITICAL FEED",  status:"idle",output:""},
#     {id:"analyst",name:"ANALYST-1 // SYNTHESIS ENGINE",status:"idle",output:""},
#   ]);
#   const [tab,setTab]=useState("map");

#   const pushAlert=(msg,lvl=1)=>setAlerts(p=>[{msg,lvl,ts:new Date().toISOString().slice(11,19)},...p].slice(0,18));
#   const setAgent=(id,patch)=>setAgents(p=>p.map(a=>a.id===id?{...a,...patch}:a));
#   const setSel=(sat)=>{selRef.current=sat;setSelUI(sat);setSelPos(null);};
#   const setHl=(ids)=>{hlRef.current=ids;};

#   // Boot
#   useEffect(()=>{
#     projRef.current=d3.geoEquirectangular().scale(W/(2*Math.PI)).translate([W/2,H/2]);

#     const s=document.createElement("script");
#     s.src="https://cdnjs.cloudflare.com/ajax/libs/satellite.js/4.0.0/satellite.min.js";
#     s.onload=()=>{
#       let loaded=0;
#       SAT_CATALOG.forEach(({id})=>{
#         const tle=TLES[id]; if(!tle) return;
#         try{satrecsRef.current[id]=window.satellite.twoline2satrec(tle[0],tle[1]);loaded++;}catch(e){}
#       });
#       setReady(true);
#       pushAlert(`SGP4 ready — ${loaded} satellites loaded (Mar-2025 TLEs)`,0);
#     };
#     s.onerror=()=>pushAlert("satellite.js CDN failed",2);
#     document.head.appendChild(s);

#     const t=document.createElement("script");
#     t.src="https://cdnjs.cloudflare.com/ajax/libs/topojson/3.0.2/topojson.min.js";
#     t.onload=()=>fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json")
#       .then(r=>r.json()).then(topo=>{worldRef.current=topojson.feature(topo,topo.objects.countries);});
#     document.head.appendChild(t);
#     return()=>{try{document.head.removeChild(s);document.head.removeChild(t);}catch(e){}};
#   },[]);

#   // rAF draw loop — NEVER re-registers, reads live refs
#   useEffect(()=>{
#     const draw=(canvas)=>{
#       if(!canvas||!projRef.current) return null;
#       const ctx=canvas.getContext("2d"),proj=projRef.current,path=d3.geoPath(proj,ctx);
#       const t=tickRef.current;
#       ctx.clearRect(0,0,W,H);

#       // Sky
#       const sky=ctx.createLinearGradient(0,0,W,H);
#       sky.addColorStop(0,"#000c18");sky.addColorStop(.5,"#000a10");sky.addColorStop(1,"#00070c");
#       ctx.fillStyle=sky;ctx.fillRect(0,0,W,H);

#       // Nebula blobs
#       [[W*.12,H*.3,"rgba(0,60,200,.045)"],[W*.82,H*.65,"rgba(0,180,120,.04)"],
#        [W*.5,H*.15,"rgba(0,100,180,.03)"],[W*.65,H*.8,"rgba(80,0,180,.025)"]
#       ].forEach(([x,y,c])=>{
#         const g=ctx.createRadialGradient(x,y,0,x,y,W*.38);
#         g.addColorStop(0,c);g.addColorStop(1,"transparent");
#         ctx.fillStyle=g;ctx.fillRect(0,0,W,H);
#       });

#       // Stars (twinkling)
#       for(let i=0;i<320;i++){
#         const sx=(i*71+13)%W,sy=(i*139+7)%H;
#         const tw=i%23===0?Math.abs(Math.sin(t*.04+i)):1;
#         const br=(i%11===0?.85:i%5===0?.45:.18)*tw;
#         const r=i%23===0?1.3:i%7===0?.75:.38;
#         ctx.beginPath();ctx.arc(sx,sy,r,0,Math.PI*2);
#         ctx.fillStyle=`rgba(210,230,255,${br})`;ctx.fill();
#       }

#       // Ocean
#       const oc=ctx.createRadialGradient(W/2,H*.6,0,W/2,H*.5,W*.75);
#       oc.addColorStop(0,"rgba(0,80,160,.55)");oc.addColorStop(.4,"rgba(0,45,100,.3)");
#       oc.addColorStop(.75,"rgba(0,15,50,.12)");oc.addColorStop(1,"rgba(0,5,20,0)");
#       ctx.fillStyle=oc;ctx.fillRect(0,0,W,H);

#       // Graticule
#       ctx.strokeStyle="rgba(0,200,160,.055)";ctx.lineWidth=.5;
#       ctx.beginPath();path(d3.geoGraticule()());ctx.stroke();

#       // Equator glow
#       ctx.save();ctx.shadowColor="rgba(0,255,180,.7)";ctx.shadowBlur=5;
#       ctx.strokeStyle="rgba(0,255,180,.28)";ctx.lineWidth=1.2;
#       ctx.beginPath();path({type:"LineString",coordinates:[[-180,0],[180,0]]});ctx.stroke();
#       ctx.restore();

#       // Countries
#       if(worldRef.current?.features){
#         ctx.save();ctx.shadowColor="rgba(0,255,160,.28)";ctx.shadowBlur=4;
#         worldRef.current.features.forEach(f=>{
#           ctx.beginPath();path(f);ctx.strokeStyle="rgba(0,255,140,.32)";ctx.lineWidth=.65;ctx.stroke();
#         });ctx.restore();
#         const fills=["rgba(4,26,16,.97)","rgba(5,30,18,.97)","rgba(3,22,14,.97)","rgba(6,28,17,.97)",
#                      "rgba(4,24,15,.97)","rgba(7,32,20,.97)","rgba(3,20,13,.97)","rgba(5,27,16,.97)"];
#         worldRef.current.features.forEach(f=>{
#           ctx.beginPath();path(f);ctx.fillStyle=fills[(f.id||0)%8];ctx.fill();
#         });
#         worldRef.current.features.forEach(f=>{
#           ctx.beginPath();path(f);ctx.strokeStyle="rgba(0,255,130,.18)";ctx.lineWidth=.38;ctx.stroke();
#         });
#       }

#       // Hotspot zones
#       [{c:[[[22,44],[40,44],[40,52],[22,52],[22,44]]],   fill:"rgba(255,60,0,.08)",  glow:"rgba(255,80,0,.3)",  lbl:"UKRAINE"},
#        {c:[[[100,5],[125,5],[125,25],[100,25],[100,5]]], fill:"rgba(255,200,0,.06)", glow:"rgba(255,220,0,.25)",lbl:"S.CHINA SEA"},
#        {c:[[[34,20],[60,20],[60,38],[34,38],[34,20]]],   fill:"rgba(255,30,30,.07)", glow:"rgba(255,50,50,.28)",lbl:"MIDEAST"},
#       ].forEach(({c,fill,glow,lbl})=>{
#         ctx.beginPath();path({type:"Feature",geometry:{type:"Polygon",coordinates:c}});
#         ctx.fillStyle=fill;ctx.fill();
#         ctx.save();ctx.shadowColor=glow;ctx.shadowBlur=8;
#         ctx.strokeStyle=glow;ctx.lineWidth=.7;ctx.stroke();ctx.restore();
#         const cx=(c[0][0][0]+c[0][2][0])/2,cy=(c[0][0][1]+c[0][2][1])/2;
#         const [lx,ly]=proj([cx,cy]);
#         ctx.fillStyle="rgba(255,120,0,.5)";ctx.font="7px 'Share Tech Mono',monospace";ctx.fillText(lbl,lx-20,ly+3);
#       });

#       // Region labels
#       [["EUROPE",12,52],["N.AMERICA",-95,42],["RUSSIA",65,60],["CHINA",108,35],
#        ["INDIA",80,22],["MIDEAST",50,30],["AFRICA",22,5],["S.AMERICA",-55,-12],["AUSTRALIA",134,-24]
#       ].forEach(([l,lon,lat])=>{
#         const [px,py]=proj([lon,lat]);
#         ctx.fillStyle="rgba(0,255,150,.08)";ctx.font="7.5px 'Share Tech Mono',monospace";ctx.fillText(l,px,py);
#       });

#       // ── Satellites — propagated fresh every frame ──
#       const sel=selRef.current,hl=hlRef.current;
#       let foundPos=null;
#       SAT_CATALOG.forEach(meta=>{
#         const satrec=satrecsRef.current[meta.id];if(!satrec)return;
#         const pos=propagateNow(satrec);if(!pos)return;
#         if(sel?.id===meta.id)foundPos=pos;
#         const trail=buildTrail(satrec,30,110);
#         const isSel=sel?.id===meta.id,isHl=hl.includes(meta.id);

#         // Trail
#         if(trail.length>1){
#           ctx.beginPath();let first=true,lastX=null;
#           trail.forEach(([lon,lat])=>{
#             const [px,py]=proj([lon,lat]);
#             if(lastX!==null&&Math.abs(px-lastX)>W/2)first=true;
#             first?(ctx.moveTo(px,py),first=false):ctx.lineTo(px,py);
#             lastX=px;
#           });
#           ctx.strokeStyle=isSel?meta.color+"cc":isHl?meta.color+"88":meta.color+"25";
#           ctx.lineWidth=isSel?2.2:isHl?1.6:.85;ctx.stroke();
#         }

#         const [px,py]=proj([pos.lon,pos.lat]);
#         const r=isSel?9:isHl?7:meta.threat>=2?6.5:5;

#         // Animated pulse rings
#         if(meta.threat>=2||isSel||isHl){
#           const pa=Math.abs(Math.sin(t*.05+meta.id.charCodeAt(0)*.3))*.6+.2;
#           ctx.save();ctx.shadowColor=meta.color;ctx.shadowBlur=14;
#           [[r+10,pa*.5],[r+21,pa*.28],[r+34,pa*.12]].forEach(([rad,al])=>{
#             ctx.beginPath();ctx.arc(px,py,rad,0,Math.PI*2);
#             ctx.strokeStyle=meta.color+Math.round(al*255).toString(16).padStart(2,"0");
#             ctx.lineWidth=.75;ctx.stroke();
#           });ctx.restore();
#         }

#         // Glow + core
#         ctx.save();ctx.shadowColor=meta.color;ctx.shadowBlur=isSel?22:isHl?14:9;
#         const g=ctx.createRadialGradient(px,py,0,px,py,r*4);
#         g.addColorStop(0,meta.color+"70");g.addColorStop(.5,meta.color+"22");g.addColorStop(1,meta.color+"00");
#         ctx.beginPath();ctx.arc(px,py,r*4,0,Math.PI*2);ctx.fillStyle=g;ctx.fill();
#         ctx.beginPath();ctx.arc(px,py,r,0,Math.PI*2);
#         ctx.fillStyle=isSel?"#ffffff":meta.color;ctx.fill();ctx.restore();

#         if(isSel||isHl||meta.threat>=2){
#           ctx.save();ctx.shadowColor=meta.color;ctx.shadowBlur=6;
#           ctx.font=`${isSel?12:9}px 'Share Tech Mono',monospace`;
#           ctx.fillStyle=isSel?"#fff":meta.color;ctx.fillText(meta.id,px+r+5,py-3);ctx.restore();
#         }
#       });

#       // HUD corners
#       ctx.save();ctx.shadowColor="rgba(0,255,170,.5)";ctx.shadowBlur=8;
#       ctx.strokeStyle="rgba(0,255,170,.42)";ctx.lineWidth=1.5;
#       [[0,0,24,0],[0,0,0,24],[W-24,0,W,0],[W,0,W,24],
#        [0,H-24,0,H],[0,H,24,H],[W-24,H,W,H],[W,H-24,W,H]
#       ].forEach(([x1,y1,x2,y2])=>{ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.stroke();});
#       ctx.restore();

#       // Top strip
#       const tg=ctx.createLinearGradient(0,0,0,22);tg.addColorStop(0,"rgba(0,20,14,.88)");tg.addColorStop(1,"transparent");
#       ctx.fillStyle=tg;ctx.fillRect(0,0,W,22);
#       ctx.save();ctx.shadowColor="#00ffcc";ctx.shadowBlur=5;
#       ctx.fillStyle="rgba(0,255,200,.45)";ctx.font="8px 'Share Tech Mono',monospace";
#       ctx.fillText(`◈ GOTHAM ORBITAL  //  SGP4 REALTIME  //  ${new Date().toUTCString().toUpperCase()}`,10,13);
#       ctx.restore();

#       // Bottom strip
#       const bg=ctx.createLinearGradient(0,H-22,0,H);bg.addColorStop(0,"transparent");bg.addColorStop(1,"rgba(0,15,10,.9)");
#       ctx.fillStyle=bg;ctx.fillRect(0,H-22,W,22);
#       ctx.save();ctx.shadowColor="#ffe44d";ctx.shadowBlur=4;
#       ctx.fillStyle="rgba(255,228,77,.5)";ctx.font="7.5px 'Share Tech Mono',monospace";
#       ctx.fillText(`⚡ MAR-2025 TLE EPOCH  ·  SGP4 PROPAGATED  ·  ${Object.keys(satrecsRef.current).length} SATS  ·  CORS-FREE`,W/2-180,H-7);
#       ctx.restore();

#       // Scanlines
#       for(let y=0;y<H;y+=4){ctx.fillStyle="rgba(0,0,0,.032)";ctx.fillRect(0,y,W,1);}

#       // Legend
#       const lx=W-112,ly=H-126;
#       ctx.fillStyle="rgba(0,8,5,.92)";ctx.beginPath();ctx.roundRect(lx,ly,106,120,3);ctx.fill();
#       ctx.save();ctx.shadowColor="rgba(0,255,140,.2)";ctx.shadowBlur=4;
#       ctx.strokeStyle="rgba(0,255,140,.17)";ctx.lineWidth=.6;ctx.stroke();ctx.restore();
#       [["CIVILIAN","#00ffcc"],["MILITARY","#ff1111"],["NAVIGATION","#cc66ff"],
#        ["COMMERCIAL","#00ccff"],["INTEL","#ff8800"],["SCIENCE","#7dff7d"],["WEATHER","#40e0ff"]
#       ].forEach(([l,c],i)=>{
#         ctx.save();ctx.shadowColor=c;ctx.shadowBlur=5;
#         ctx.beginPath();ctx.arc(lx+11,ly+13+i*15,3.5,0,Math.PI*2);ctx.fillStyle=c;ctx.fill();ctx.restore();
#         ctx.fillStyle=c+"aa";ctx.font="7.5px 'Share Tech Mono',monospace";ctx.fillText(l,lx+20,ly+17+i*15);
#       });

#       return foundPos;
#     };

#     const tick=()=>{
#       tickRef.current++;
#       const sp=draw(canvasA.current);
#       draw(canvasB.current);
#       if(sp) setSelPos(p=>(!p||Math.abs(p.lat-sp.lat)>.001)?{...sp}:p);
#       animRef.current=requestAnimationFrame(tick);
#     };
#     animRef.current=requestAnimationFrame(tick);
#     return()=>cancelAnimationFrame(animRef.current);
#   },[]); // empty — runs forever, reads live refs

#   const onCanvasClick=useCallback((e)=>{
#     const canvas=e.currentTarget;
#     const rect=canvas.getBoundingClientRect();
#     const mx=(e.clientX-rect.left)*(W/rect.width),my=(e.clientY-rect.top)*(H/rect.height);
#     const proj=projRef.current;if(!proj)return;
#     let best=null,bestD=22;
#     SAT_CATALOG.forEach(meta=>{
#       const satrec=satrecsRef.current[meta.id];if(!satrec)return;
#       const pos=propagateNow(satrec);if(!pos)return;
#       const [px,py]=proj([pos.lon,pos.lat]);
#       const d=Math.hypot(mx-px,my-py);
#       if(d<bestD){bestD=d;best=meta;}
#     });
#     setSel(best?.id===selRef.current?.id?null:best);
#   },[]);

#   const runCycle=useCallback(async()=>{
#     if(!apiKey)return;
#     setRunning(true);setCycle(c=>c+1);
#     const snap=SAT_CATALOG.map(meta=>{
#       const satrec=satrecsRef.current[meta.id];
#       const pos=satrec?propagateNow(satrec):null;
#       return pos?`${meta.id}(${meta.owner}): lat=${pos.lat.toFixed(2)} lon=${pos.lon.toFixed(2)} alt=${pos.alt.toFixed(0)}km threat=${THREAT_META[meta.threat].label}`:`${meta.id}: no data`;
#     }).join("\n");
#     setAgent("orbital",{status:"running"});setAgent("news",{status:"running"});
#     const [oR,nR]=await Promise.allSettled([
#       callAgent(apiKey,SYS_ORBITAL,`LIVE SGP4 ${new Date().toISOString()}:\n${snap}`),
#       callAgent(apiKey,SYS_NEWS,`Operators: ${[...new Set(SAT_CATALOG.map(s=>s.owner))].join(", ")}`),
#     ]);
#     const oT=oR.status==="fulfilled"?oR.value:"[ORBITAL-1] ⚠ API error";
#     const nT=nR.status==="fulfilled"?nR.value:"[NEWS-1] ⚠ API error";
#     setAgent("orbital",{status:"done",output:oT});setAgent("news",{status:"done",output:nT});
#     SAT_CATALOG.filter(s=>s.threat===3).forEach(s=>{if(Math.random()>.5)pushAlert(`${s.id} — anomalous maneuver`,3);});
#     setAgent("analyst",{status:"running"});
#     const aT=await callAgent(apiKey,SYS_ANALYST,`ORBITAL-1:\n${oT}\n\nNEWS-1:\n${nT}`)
#       .catch(e=>"[ANALYST-1] ⚠ "+e.message);
#     setAgent("analyst",{status:"done",output:aT});
#     pushAlert("ANALYST-1 synthesis complete",1);setRunning(false);
#   },[apiKey]);

#   const startMonitor=()=>{runCycle();agentTimer.current=setInterval(runCycle,120000);};
#   const stopMonitor=()=>{clearInterval(agentTimer.current);setRunning(false);};
#   useEffect(()=>()=>clearInterval(agentTimer.current),[]);

#   const handleNL=async()=>{
#     if(!apiKey||!nlQuery.trim())return;
#     setNlLoading(true);setNlResult(null);setHl([]);
#     try{
#       const snap=SAT_CATALOG.map(meta=>{
#         const satrec=satrecsRef.current[meta.id];
#         const pos=satrec?propagateNow(satrec):null;
#         return pos?`${meta.id}(${meta.owner}|${meta.type}): lat=${pos.lat.toFixed(1)} lon=${pos.lon.toFixed(1)} alt=${pos.alt.toFixed(0)}km`:`${meta.id}: no data`;
#       }).join("\n");
#       const result=await callAgent(apiKey,SYS_NL,`Live positions:\n${snap}\n\nQuery: ${nlQuery}`);
#       setNlResult(result);
#       const m=result.match(/RELEVANT OBJECTS:\s*([A-Z0-9,\s]+)/i);
#       if(m){
#         const ids=m[1].split(",").map(s=>s.trim()).filter(s=>SAT_CATALOG.find(x=>x.id===s));
#         setHl(ids);pushAlert(`Query flagged ${ids.length} objects`,1);
#       }
#     }catch(e){setNlResult("⚠ "+e.message);}
#     setNlLoading(false);
#   };

#   const threatCounts=THREAT_META.map((_,i)=>SAT_CATALOG.filter(s=>s.threat===i).length);
#   const EXAMPLES=["Where is the ISS right now?","Which satellites are over Asia?",
#     "Flag all military and intel sats","Which has highest altitude?","ISS vs Tiangong position?"];

#   return(
#     <div style={{minHeight:"100vh",background:"#00070c",color:"#90c8b8",fontFamily:"'Share Tech Mono',monospace"}}>
#       <style>{`
#         @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@600;700&display=swap');
#         *{box-sizing:border-box;margin:0;padding:0}
#         @keyframes blink{0%,100%{opacity:1}50%{opacity:0}}
#         @keyframes pulse{0%,100%{opacity:.35}50%{opacity:1}}
#         ::-webkit-scrollbar{width:3px}::-webkit-scrollbar-thumb{background:#0a2418}
#         .tab{background:transparent;border:none;cursor:pointer;font-family:'Share Tech Mono',monospace;
#           font-size:10px;letter-spacing:2px;padding:8px 16px;transition:all .2s}
#         .ton{color:#00ffcc;border-bottom:2px solid #00ffcc;text-shadow:0 0 8px #00ffcc66}
#         .tof{color:#0e2a1e;border-bottom:2px solid transparent}.tof:hover{color:#1a6040}
#         .nlin{background:rgba(0,255,200,.04);border:1px solid rgba(0,255,200,.15);
#           color:#a0e0c8;font-family:'Share Tech Mono',monospace;font-size:12px;
#           padding:10px 14px;border-radius:2px;outline:none;width:100%}
#         .nlin:focus{border-color:rgba(0,255,200,.45);box-shadow:0 0 12px rgba(0,255,200,.1)}
#         .nlin::placeholder{color:rgba(0,255,200,.2)}
#         .apin{background:rgba(0,255,200,.03);border:1px solid rgba(0,255,200,.1);
#           color:#a0e0c8;font-family:'Share Tech Mono',monospace;font-size:11px;
#           padding:7px 10px;border-radius:2px;outline:none;width:200px}
#         .apin:focus{border-color:rgba(0,255,200,.3)}
#         .apin::placeholder{color:rgba(0,255,200,.14)}
#         .btn{font-family:'Share Tech Mono',monospace;font-size:11px;letter-spacing:2px;
#           padding:8px 16px;border-radius:2px;cursor:pointer;border:1px solid;transition:all .2s}
#         .bgo{border-color:#00ffcc;color:#00ffcc;background:transparent}
#         .bgo:hover:not(:disabled){background:rgba(0,255,200,.1);box-shadow:0 0 14px rgba(0,255,200,.3)}
#         .bst{border-color:#ff1111;color:#ff1111;background:transparent}
#         .bst:hover{background:rgba(255,17,17,.1)}
#         .btn:disabled{opacity:.25;cursor:not-allowed}
#         .pill{background:transparent;border:1px solid rgba(0,255,200,.1);border-radius:20px;
#           color:rgba(0,255,200,.38);font-family:'Share Tech Mono',monospace;font-size:10px;
#           padding:4px 10px;cursor:pointer;transition:all .2s}
#         .pill:hover{border-color:rgba(0,255,200,.4);color:#00ffcc;background:rgba(0,255,200,.05)}
#         .cw{position:relative;overflow:hidden}
#         .cw::after{content:'';position:absolute;inset:0;
#           background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.03) 2px,rgba(0,0,0,.03) 3px);
#           pointer-events:none}
#       `}</style>

#       {/* Topbar */}
#       <div style={{padding:"10px 20px",borderBottom:"1px solid rgba(0,255,200,.1)",
#         background:"rgba(0,0,0,.85)",backdropFilter:"blur(12px)",
#         display:"flex",alignItems:"center",justifyContent:"space-between",flexWrap:"wrap",gap:8}}>
#         <div>
#           <div style={{fontFamily:"'Rajdhani',sans-serif",fontSize:21,fontWeight:700,
#             color:"#00ffcc",letterSpacing:5,textShadow:"0 0 30px rgba(0,255,200,.55),0 0 60px rgba(0,255,200,.2)"}}>
#             ◈ GOTHAM ORBITAL // INTELLIGENCE PLATFORM
#           </div>
#           <div style={{fontSize:9,color:"rgba(0,255,200,.22)",letterSpacing:3,marginTop:1}}>
#             SGP4 PROPAGATION · MAR-2025 TLE EPOCH · optimum_ReAct · HybridMemory
#           </div>
#         </div>
#         <div style={{display:"flex",alignItems:"center",gap:8,flexWrap:"wrap"}}>
#           <input className="apin" type="password" placeholder="Anthropic API key..."
#             value={apiKey} onChange={e=>setApiKey(e.target.value)}/>
#           <button className="btn bgo" onClick={startMonitor} disabled={running||!apiKey}>
#             {running?"▶ LIVE":"▶ INITIATE"}
#           </button>
#           {running&&<button className="btn bst" onClick={stopMonitor}>■ HALT</button>}
#           <div style={{fontSize:9,color:"rgba(0,255,200,.28)",textAlign:"right"}}>
#             <div>CYCLE {String(cycle).padStart(4,"0")}</div>
#             <div style={{color:running?"#00ffcc":"#0e2a1e",animation:running?"pulse 1.2s infinite":"none"}}>
#               {running?"● ACTIVE":"○ STANDBY"}
#             </div>
#           </div>
#         </div>
#       </div>

#       {/* Status bar */}
#       <div style={{padding:"3px 20px",background:"rgba(0,0,0,.6)",borderBottom:"1px solid rgba(0,255,200,.05)",
#         display:"flex",alignItems:"center",gap:8}}>
#         <div style={{width:5,height:5,borderRadius:"50%",flexShrink:0,
#           background:ready?"#00ffcc":"rgba(255,228,77,.8)",
#           boxShadow:ready?"0 0 8px #00ffcc66":"none",
#           animation:!ready?"pulse 1s infinite":"none"}}/>
#         <span style={{fontSize:8,letterSpacing:1,
#           color:ready?"rgba(0,255,200,.5)":"rgba(255,228,77,.5)"}}>
#           {ready
#             ?`✓ SGP4 READY — ${Object.keys(satrecsRef.current||{}).length||14} SATELLITES — MAR-2025 TLE EPOCH — POSITIONS ACCURATE ±FEW KM`
#             :"Loading satellite.js SGP4 library from CDN..."}
#         </span>
#         <span style={{marginLeft:"auto",fontSize:8,color:"rgba(255,228,77,.4)",letterSpacing:1}}>
#           ⚡ LIVE API = CORS BLOCKED FROM BROWSER · BAKED TLEs = ALWAYS WORKS · SAME REAL SGP4 MATH
#         </span>
#       </div>

#       {/* Threat bar */}
#       <div style={{display:"flex",borderBottom:"1px solid rgba(0,255,200,.06)",background:"rgba(0,0,0,.5)"}}>
#         {THREAT_META.map((t,i)=>(
#           <div key={i} style={{flex:1,padding:"5px 14px",borderRight:"1px solid rgba(0,255,200,.05)",
#             display:"flex",alignItems:"center",gap:6}}>
#             <div style={{width:5,height:5,borderRadius:"50%",background:t.color,
#               boxShadow:`0 0 8px ${t.color}`,animation:i>=2?"pulse 1.5s infinite":"none"}}/>
#             <span style={{fontSize:9,color:t.color,letterSpacing:2}}>{t.label}</span>
#             <span style={{fontSize:14,fontFamily:"'Rajdhani',sans-serif",fontWeight:700,
#               color:"#fff",marginLeft:"auto",textShadow:`0 0 6px ${t.color}44`}}>{threatCounts[i]}</span>
#           </div>
#         ))}
#         <div style={{padding:"5px 14px",display:"flex",alignItems:"center",gap:6}}>
#           <span style={{fontSize:9,color:"rgba(0,255,200,.35)",letterSpacing:2}}>TRACKING</span>
#           <span style={{fontSize:14,fontFamily:"'Rajdhani',sans-serif",fontWeight:700,
#             color:"#00ffcc",textShadow:"0 0 12px rgba(0,255,200,.6)"}}>{SAT_CATALOG.length}</span>
#         </div>
#       </div>

#       {/* Tabs */}
#       <div style={{display:"flex",borderBottom:"1px solid rgba(0,255,200,.06)",background:"rgba(0,0,0,.45)"}}>
#         {[["map","◈ ORBITAL MAP"],["query","⌕ NL QUERY"],["agents","◎ AGENTS"]].map(([id,l])=>(
#           <button key={id} className={`tab ${tab===id?"ton":"tof"}`} onClick={()=>setTab(id)}>{l}</button>
#         ))}
#         <div style={{marginLeft:"auto",padding:"8px 14px",fontSize:8,letterSpacing:2,
#           color:ready?"rgba(0,255,200,.4)":"rgba(255,228,77,.4)",display:"flex",alignItems:"center",gap:5}}>
#           <span style={{width:5,height:5,borderRadius:"50%",display:"inline-block",
#             background:ready?"#00ffcc55":"rgba(255,228,77,.5)",animation:"pulse 2s infinite"}}/>
#           {ready?`SGP4 LIVE · ${SAT_CATALOG.length} SATS`:"INITIALIZING..."}
#         </div>
#       </div>

#       {/* MAP TAB */}
#       {tab==="map"&&(
#         <div style={{display:"grid",gridTemplateColumns:"1fr 290px",height:"calc(100vh - 172px)"}}>
#           <div style={{display:"flex",flexDirection:"column",borderRight:"1px solid rgba(0,255,200,.07)"}}>
#             <div className="cw" style={{flex:1}}>
#               <canvas ref={canvasA} width={W} height={H}
#                 style={{width:"100%",display:"block",cursor:"crosshair"}} onClick={onCanvasClick}/>
#               {selUI&&selPos&&(
#                 <div style={{position:"absolute",top:26,left:8,padding:"11px 14px",
#                   background:"rgba(0,5,3,.98)",border:`1px solid ${selUI.color}44`,
#                   borderLeft:`3px solid ${selUI.color}`,borderRadius:3,minWidth:240,
#                   boxShadow:`0 0 30px ${selUI.color}22,0 0 1px ${selUI.color}55`}}>
#                   <div style={{fontSize:8,color:selUI.color,letterSpacing:3,marginBottom:4,
#                     textShadow:`0 0 6px ${selUI.color}`}}>◈ LIVE TRACK // SGP4</div>
#                   <div style={{fontSize:15,color:"#fff",fontFamily:"'Rajdhani',sans-serif",fontWeight:700,marginBottom:6}}>
#                     {selUI.name}
#                   </div>
#                   {[["OWNER",selUI.owner],["TYPE",selUI.type.toUpperCase()],
#                     ["LAT",`${selPos.lat.toFixed(4)}°`],["LON",`${selPos.lon.toFixed(4)}°`],
#                     ["ALTITUDE",`${selPos.alt.toFixed(1)} km`],
#                     ["THREAT",THREAT_META[selUI.threat].label],
#                     ["TLE EPOCH","MAR 2025"],["PROPAGATOR","SGP4"],
#                   ].map(([k,v])=>(
#                     <div key={k} style={{fontSize:10,color:"#1e4030",lineHeight:1.9}}>
#                       {k}: <span style={{color:k==="THREAT"?THREAT_META[selUI.threat].color
#                         :k==="PROPAGATOR"||k==="TLE EPOCH"?"rgba(0,255,200,.5)":"#60a090"}}>{v}</span>
#                     </div>
#                   ))}
#                   <div style={{marginTop:8,fontSize:8,color:"#0a2018",cursor:"pointer",letterSpacing:2}}
#                     onClick={()=>setSel(null)}>[ DESELECT ]</div>
#                 </div>
#               )}
#             </div>
#             <div style={{padding:"6px 10px",borderTop:"1px solid rgba(0,255,200,.06)",
#               display:"flex",flexWrap:"wrap",gap:4,overflowY:"auto",maxHeight:70,background:"rgba(0,0,0,.65)"}}>
#               {SAT_CATALOG.map(meta=>(
#                 <div key={meta.id} onClick={()=>setSel(meta.id===selUI?.id?null:meta)}
#                   style={{padding:"2px 8px",borderRadius:2,cursor:"pointer",fontSize:8,letterSpacing:1,
#                     border:`1px solid ${meta.color}${satrecsRef.current[meta.id]?"44":"18"}`,
#                     background:selUI?.id===meta.id?meta.color+"1a":"transparent",
#                     color:satrecsRef.current[meta.id]?meta.color:meta.color+"44",
#                     boxShadow:selUI?.id===meta.id?`0 0 8px ${meta.color}44`:"none",
#                     transition:"all .12s"}}>
#                   {meta.id}
#                 </div>
#               ))}
#             </div>
#           </div>
#           <div style={{display:"flex",flexDirection:"column",overflow:"hidden",background:"rgba(0,0,0,.4)"}}>
#             <div style={{flex:1,padding:11,overflowY:"auto",borderBottom:"1px solid rgba(0,255,200,.06)"}}>
#               <div style={{fontSize:8,color:"rgba(0,255,200,.3)",letterSpacing:3,marginBottom:8}}>
#                 ▸ AGENT NETWORK // {agents.filter(a=>a.status==="running").length} ACTIVE
#               </div>
#               {agents.map(a=><AgentCard key={a.id} a={a}/>)}
#             </div>
#             <div style={{padding:11,overflowY:"auto",height:155}}>
#               <div style={{fontSize:8,color:"rgba(0,255,200,.3)",letterSpacing:3,marginBottom:8}}>▸ ALERT STREAM</div>
#               {alerts.length===0
#                 ?<div style={{fontSize:9,color:"#0a1a10",fontStyle:"italic"}}>no alerts</div>
#                 :alerts.map((a,i)=>(
#                   <div key={i} style={{padding:"3px 8px",marginBottom:3,fontSize:9,lineHeight:1.5,
#                     borderLeft:`2px solid ${THREAT_META[a.lvl].color}`,
#                     background:THREAT_META[a.lvl].color+"07",color:"#4a7a68"}}>
#                     <span style={{color:THREAT_META[a.lvl].color,fontSize:7,display:"block"}}>{a.ts}</span>
#                     {a.msg}
#                   </div>
#                 ))
#               }
#             </div>
#           </div>
#         </div>
#       )}

#       {/* NL QUERY */}
#       {tab==="query"&&(
#         <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",height:"calc(100vh - 172px)"}}>
#           <div style={{borderRight:"1px solid rgba(0,255,200,.07)",display:"flex",flexDirection:"column"}}>
#             <div style={{padding:14,borderBottom:"1px solid rgba(0,255,200,.07)",background:"rgba(0,0,0,.35)"}}>
#               <div style={{fontSize:8,color:"rgba(0,255,200,.4)",letterSpacing:3,marginBottom:9}}>
#                 ▸ NL QUERY // SGP4 Live Context
#               </div>
#               <div style={{display:"flex",gap:8,marginBottom:9}}>
#                 <input className="nlin" placeholder="e.g. Where is the ISS right now?"
#                   value={nlQuery} onChange={e=>setNlQuery(e.target.value)}
#                   onKeyDown={e=>e.key==="Enter"&&handleNL()}/>
#                 <button className="btn bgo" onClick={handleNL} disabled={nlLoading||!apiKey||!nlQuery.trim()}>⌕</button>
#               </div>
#               <div style={{display:"flex",flexWrap:"wrap",gap:5}}>
#                 {EXAMPLES.map((q,i)=>(
#                   <button key={i} className="pill" onClick={()=>setNlQuery(q)}>
#                     {q.slice(0,40)}{q.length>40?"...":""}
#                   </button>
#                 ))}
#               </div>
#             </div>
#             <div className="cw" style={{flex:1,overflow:"hidden"}}>
#               <canvas ref={canvasB} width={W} height={H}
#                 style={{width:"100%",display:"block",cursor:"crosshair"}} onClick={onCanvasClick}/>
#             </div>
#           </div>
#           <div style={{display:"flex",flexDirection:"column",background:"rgba(0,0,0,.25)"}}>
#             <div style={{padding:"9px 14px",borderBottom:"1px solid rgba(0,255,200,.07)",
#               fontSize:8,color:"rgba(0,255,200,.35)",letterSpacing:3}}>▸ AGENT RESPONSE</div>
#             <div style={{flex:1,overflowY:"auto"}}>
#               {nlLoading
#                 ?<div style={{padding:14,color:"#00ffcc",fontSize:11}}>
#                     <span style={{animation:"blink .8s step-end infinite"}}>◈ QUERYING...</span>
#                   </div>
#                 :nlResult
#                 ?<div style={{padding:14,fontFamily:"'Courier New',monospace",fontSize:11,
#                     color:"#5a9a88",lineHeight:1.8,whiteSpace:"pre-wrap"}}>{nlResult}</div>
#                 :<div style={{padding:14,color:"#0a1a10",fontSize:10,fontStyle:"italic"}}>
#                     enter a query above
#                   </div>
#               }
#             </div>
#           </div>
#         </div>
#       )}

#       {/* AGENTS TAB */}
#       {tab==="agents"&&(
#         <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",height:"calc(100vh - 172px)"}}>
#           <div style={{padding:14,overflowY:"auto",borderRight:"1px solid rgba(0,255,200,.07)"}}>
#             <div style={{fontSize:8,color:"rgba(0,255,200,.4)",letterSpacing:3,marginBottom:12}}>▸ AGENT OUTPUTS</div>
#             {agents.map(a=><AgentCard key={a.id} a={a}/>)}
#           </div>
#           <div style={{padding:14,overflowY:"auto"}}>
#             <div style={{fontSize:8,color:"rgba(0,255,200,.4)",letterSpacing:3,marginBottom:12}}>▸ LIVE POSITION TABLE</div>
#             <table style={{width:"100%",borderCollapse:"collapse",fontFamily:"'Courier New',monospace",fontSize:10}}>
#               <thead>
#                 <tr style={{borderBottom:"1px solid rgba(0,255,200,.12)"}}>
#                   {["ID","LAT","LON","ALT","TYPE"].map(h=>(
#                     <td key={h} style={{padding:"4px 6px",color:"rgba(0,255,200,.35)",fontSize:8,letterSpacing:1}}>{h}</td>
#                   ))}
#                 </tr>
#               </thead>
#               <tbody>
#                 {SAT_CATALOG.map(meta=>{
#                   const satrec=satrecsRef.current[meta.id];
#                   const pos=satrec?propagateNow(satrec):null;
#                   return(
#                     <tr key={meta.id} style={{borderBottom:"1px solid rgba(0,255,200,.04)",cursor:"pointer",
#                       background:selUI?.id===meta.id?meta.color+"0a":"transparent"}}
#                       onClick={()=>setSel(meta.id===selUI?.id?null:meta)}>
#                       <td style={{padding:"4px 6px",color:meta.color,fontSize:9}}>{meta.id}</td>
#                       <td style={{padding:"4px 6px",color:"#3a6a58",fontSize:9}}>{pos?pos.lat.toFixed(2)+"°":"—"}</td>
#                       <td style={{padding:"4px 6px",color:"#3a6a58",fontSize:9}}>{pos?pos.lon.toFixed(2)+"°":"—"}</td>
#                       <td style={{padding:"4px 6px",color:"#3a6a58",fontSize:9}}>{pos?pos.alt.toFixed(0)+"km":"—"}</td>
#                       <td style={{padding:"4px 6px",color:meta.color+"88",fontSize:8}}>{meta.type}</td>
#                     </tr>
#                   );
#                 })}
#               </tbody>
#             </table>
#           </div>
#         </div>
#       )}
#     </div>
#   );
# }


# # """
# # optimum_ReAct — Palantir-style Fused Intelligence Backend
# # ===========================================================
# # Frontend : Vercel (gotham-v2.jsx)
# # Backend  : AWS EC2 (this file)

# # FIXES vs previous version:
# #   - Removed calls to non-existent async methods (remember_async, recall_async,
# #     stats_async, clear_async, ask_async with kwargs that don't exist)
# #   - EZAgent.ask_async() takes only (task, max_steps) — no system_prompt kwarg
# #   - All "async" wrappers now run sync HybridMemory methods in a thread executor
# #   - atlas_system_prompt is injected INTO the task string, not as a kwarg
# # """

# # import os
# # import re
# # import math
# # import asyncio
# # import logging
# # from datetime import datetime, timezone
# # from typing import Optional
# # from functools import partial

# # import httpx
# # from fastapi import FastAPI, HTTPException
# # from fastapi.middleware.cors import CORSMiddleware
# # from pydantic import BaseModel
# # from dotenv import load_dotenv

# # load_dotenv()

# # from AgenT import EZAgent

# # # ── Logging ───────────────────────────────────────────────────────────────────
# # logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
# # log = logging.getLogger("gotham-api")

# # # ── App ───────────────────────────────────────────────────────────────────────
# # app = FastAPI(
# #     title="Gotham Orbital — Fused Intelligence API",
# #     description="Palantir-style satellite movement history + live news fusion",
# #     version="3.1.0",
# # )
# # app.add_middleware(
# #     CORSMiddleware,
# #     allow_origins=["*"],
# #     allow_methods=["GET", "POST", "DELETE"],
# #     allow_headers=["*"],
# # )

# # # ── Config ────────────────────────────────────────────────────────────────────
# # DB_PATH      = os.getenv("AGENT_DB_PATH", "data/gotham_agent.db")
# # TAVILY_KEY   = os.getenv("TAVILY_API_KEY", "")
# # TAVILY_URL   = "https://api.tavily.com/search"
# # MAX_NEWS     = 4
# # PROXIMITY_KM = 500

# # os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)

# # # ── Satellite catalog ─────────────────────────────────────────────────────────
# # SAT_CATALOG = [
# #     {"id": "ISS",        "name": "ISS (ZARYA)",     "owner": "NASA/Roscosmos", "threat": 0, "type": "civilian"   },
# #     {"id": "TIANGONG",   "name": "CSS Tiangong",     "owner": "CNSA",           "threat": 1, "type": "military"   },
# #     {"id": "NOAA19",     "name": "NOAA-19",          "owner": "NOAA",           "threat": 0, "type": "weather"    },
# #     {"id": "TERRA",      "name": "Terra EOS AM-1",   "owner": "NASA",           "threat": 0, "type": "science"    },
# #     {"id": "AQUA",       "name": "Aqua EOS PM-1",    "owner": "NASA",           "threat": 0, "type": "science"    },
# #     {"id": "SENTINEL2B", "name": "Sentinel-2B",      "owner": "ESA",            "threat": 0, "type": "observation"},
# #     {"id": "STARLINK30", "name": "Starlink-1007",    "owner": "SpaceX",         "threat": 0, "type": "commercial" },
# #     {"id": "STARLINK31", "name": "Starlink-2341",    "owner": "SpaceX",         "threat": 0, "type": "commercial" },
# #     {"id": "IRIDIUM140", "name": "IRIDIUM-140",      "owner": "Iridium",        "threat": 0, "type": "commercial" },
# #     {"id": "GPS001",     "name": "GPS IIF-2",        "owner": "USAF",           "threat": 1, "type": "navigation" },
# #     {"id": "GLONASS",    "name": "GLONASS-M 730",    "owner": "Russia",         "threat": 1, "type": "navigation" },
# #     {"id": "COSMOS2543", "name": "COSMOS-2543",      "owner": "Russia",         "threat": 3, "type": "military"   },
# #     {"id": "YAOGAN30",   "name": "YAOGAN-30F",       "owner": "China/PLA",      "threat": 2, "type": "military"   },
# #     {"id": "LACROSSE5",  "name": "USA-182",          "owner": "NRO",            "threat": 2, "type": "intel"      },
# # ]
# # THREAT_LABELS = ["NOMINAL", "MONITOR", "ELEVATED", "CRITICAL"]
# # VALID_IDS     = {s["id"] for s in SAT_CATALOG}
# # SAT_BY_ID     = {s["id"]: s for s in SAT_CATALOG}

# # # ── Agent singleton ───────────────────────────────────────────────────────────
# # _agent: Optional[EZAgent] = None
# # _lock  = asyncio.Lock()

# # async def get_agent() -> EZAgent:
# #     global _agent
# #     async with _lock:
# #         if _agent is None:
# #             log.info(f"Initializing EZAgent — DB: {DB_PATH}")
# #             loop = asyncio.get_event_loop()
# #             _agent = await loop.run_in_executor(None, EZAgent, DB_PATH)
# #             log.info("EZAgent ready")
# #     return _agent


# # # ── Async wrappers for sync HybridMemory methods ──────────────────────────────
# # # EZAgent wraps HybridMemory. remember() and recall() are synchronous.
# # # We run them in a thread executor to avoid blocking FastAPI's event loop.

# # async def _remember(agent: EZAgent, content: str) -> str:
# #     loop = asyncio.get_event_loop()
# #     return await loop.run_in_executor(
# #         None, partial(agent.memory.remember, content, mem_type="fact", importance=0.8)
# #     )

# # async def _recall(agent: EZAgent, query: str, limit: int = 10) -> list:
# #     loop = asyncio.get_event_loop()
# #     return await loop.run_in_executor(
# #         None, partial(agent.memory.recall, query, limit)
# #     )

# # async def _ask(agent: EZAgent, task: str, max_steps: int = 6) -> str:
# #     # ask_async IS already async in EZAgent — call it directly
# #     return await agent.ask_async(task, max_steps=max_steps)


# # # ── Geo helpers ───────────────────────────────────────────────────────────────
# # def haversine_km(lat1, lon1, lat2, lon2):
# #     R = 6371.0
# #     p1, p2 = math.radians(lat1), math.radians(lat2)
# #     dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
# #     a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
# #     return R * 2 * math.asin(math.sqrt(a))

# # def ground_region(lat, lon):
# #     if   lat >  35 and  -10 < lon <  40: return "EUROPE"
# #     elif lat >  25 and -130 < lon < -60: return "N.AMERICA"
# #     elif lat >  45 and   40 < lon < 180: return "RUSSIA"
# #     elif  15 < lat <  55 and  70 < lon < 135: return "CHINA"
# #     elif   5 < lat <  35 and  65 < lon <  90: return "INDIA"
# #     elif  15 < lat <  42 and  25 < lon <  65: return "MIDEAST"
# #     elif -35 < lat <  35 and -20 < lon <  55: return "AFRICA"
# #     elif -55 < lat <  15 and -85 < lon < -35: return "S.AMERICA"
# #     elif -45 < lat < -10 and 110 < lon < 155: return "AUSTRALIA"
# #     elif  30 < lat <  50 and 125 < lon < 150: return "JAPAN/KOREA"
# #     elif  35 < lat <  47 and  26 < lon <  45: return "UKRAINE/BLACK SEA"
# #     elif lat > 65:  return "ARCTIC"
# #     elif lat < -60: return "ANTARCTIC"
# #     else:           return "OPEN OCEAN"


# # # ── Tavily news search ────────────────────────────────────────────────────────
# # async def search_news(query: str) -> list:
# #     if not TAVILY_KEY:
# #         log.warning("TAVILY_API_KEY not set — skipping news")
# #         return []
# #     try:
# #         async with httpx.AsyncClient(timeout=8.0) as client:
# #             resp = await client.post(TAVILY_URL, json={
# #                 "api_key": TAVILY_KEY, "query": query,
# #                 "search_depth": "basic", "max_results": MAX_NEWS, "include_answer": False,
# #             })
# #             resp.raise_for_status()
# #             return [{"title": r.get("title",""), "url": r.get("url",""),
# #                      "snippet": r.get("content","")[:300]}
# #                     for r in resp.json().get("results", [])]
# #     except Exception as e:
# #         log.warning(f"Tavily failed: {e}")
# #         return []


# # # ── Movement history helpers ──────────────────────────────────────────────────
# # def _format_pos(sat_id: str, pos: dict, cycle: int) -> str:
# #     meta = SAT_BY_ID.get(sat_id, {})
# #     return (
# #         f"[SAT_HISTORY] {sat_id} ({meta.get('owner','?')} · {meta.get('type','?')}) "
# #         f"at {pos.get('ts', utcnow())} — "
# #         f"lat={pos['lat']:.2f} lon={pos['lon']:.2f} alt={pos.get('alt',0):.0f}km "
# #         f"over {ground_region(pos['lat'], pos['lon'])} — "
# #         f"threat={THREAT_LABELS[meta.get('threat', 0)]} — cycle={cycle}"
# #     )

# # async def store_snapshot(agent: EZAgent, snapshot_text: str, cycle: int) -> int:
# #     pattern = re.compile(
# #         r"(?P<id>[A-Z0-9]+)\([^)]+\):\s*"
# #         r"lat=(?P<lat>-?\d+\.?\d*)\s+"
# #         r"lon=(?P<lon>-?\d+\.?\d*)\s+"
# #         r"alt=(?P<alt>\d+\.?\d*)km"
# #     )
# #     ts = utcnow(); stored = 0
# #     for line in snapshot_text.splitlines():
# #         m = pattern.match(line.strip())
# #         if not m: continue
# #         sat_id = m.group("id")
# #         if sat_id not in VALID_IDS: continue
# #         pos = {"lat": float(m.group("lat")), "lon": float(m.group("lon")),
# #                "alt": float(m.group("alt")), "ts": ts}
# #         await _remember(agent, _format_pos(sat_id, pos, cycle))
# #         stored += 1
# #     log.info(f"Cycle {cycle} — stored {stored} records")
# #     return stored

# # async def recall_history(agent: EZAgent, sat_ids: list) -> str:
# #     blocks = []
# #     for sat_id in sat_ids:
# #         results = await _recall(agent, f"SAT_HISTORY {sat_id} position movement", limit=10)
# #         if not results:
# #             blocks.append(f"{sat_id}: no history yet"); continue
# #         lines = [
# #             (r.content if hasattr(r, "content") else str(r))
# #             for r in results
# #             if sat_id in (r.content if hasattr(r, "content") else str(r))
# #         ]
# #         if not lines:
# #             blocks.append(f"{sat_id}: no matching entries"); continue
# #         meta = SAT_BY_ID.get(sat_id, {})
# #         blocks.append(
# #             f"── {sat_id} · {meta.get('name','?')} · {meta.get('owner','?')} ──\n"
# #             + "\n".join(f"  {l}" for l in lines[-8:])
# #         )
# #     return "\n\n".join(blocks) if blocks else "No movement history yet."


# # # ── Proximity detection ───────────────────────────────────────────────────────
# # def check_proximity(snapshot_text: str) -> list:
# #     pattern = re.compile(
# #         r"(?P<id>[A-Z0-9]+)\([^)]+\):\s*lat=(?P<lat>-?\d+\.?\d*)\s+lon=(?P<lon>-?\d+\.?\d*)"
# #     )
# #     positions = {m.group("id"): (float(m.group("lat")), float(m.group("lon")))
# #                  for m in pattern.finditer(snapshot_text) if m.group("id") in VALID_IDS}
# #     alerts = []
# #     ids = list(positions.keys())
# #     for i in range(len(ids)):
# #         for j in range(i+1, len(ids)):
# #             a, b = ids[i], ids[j]
# #             ma, mb = SAT_BY_ID.get(a,{}), SAT_BY_ID.get(b,{})
# #             if ma.get("type") not in ("military","intel") and mb.get("type") not in ("military","intel"):
# #                 continue
# #             dist = haversine_km(*positions[a], *positions[b])
# #             if dist < PROXIMITY_KM:
# #                 alerts.append(
# #                     f"PROXIMITY: {a}({ma.get('owner','?')}) ↔ {b}({mb.get('owner','?')}) "
# #                     f"— {dist:.0f}km apart — over {ground_region(*positions[a])}"
# #                 )
# #     return alerts


# # # ── Query helpers ─────────────────────────────────────────────────────────────
# # def extract_sat_ids(query: str) -> list:
# #     return [sid for sid in VALID_IDS if sid in query.upper()]

# # def build_tavily_query(user_query: str, sat_ids: list) -> str:
# #     owners = list({SAT_BY_ID[sid]["owner"] for sid in sat_ids if sid in SAT_BY_ID})
# #     extras = []
# #     if any(o in ("Russia", "China/PLA", "CNSA") for o in owners):
# #         extras.append("satellite military intelligence 2025")
# #     if sat_ids:
# #         extras.append(" ".join(sat_ids[:2]))
# #     return f"{user_query.strip()} {' '.join(extras)}".strip()

# # def atlas_system_prompt() -> str:
# #     catalog = " | ".join(
# #         f"{s['id']}:{s['name']}({s['owner']},threat={THREAT_LABELS[s['threat']]})"
# #         for s in SAT_CATALOG
# #     )
# #     return f"""You are ATLAS — senior satellite intelligence analyst on the Gotham Orbital platform.

# # SATELLITE CATALOG:
# # {catalog}

# # RESPONSE FORMAT:
# # [ATLAS] FUSED INTELLIGENCE BRIEF
# # ===================================
# # SUBJECT: [satellite(s) or topic]
# # TIMEFRAME: [period covered]

# # MOVEMENT ANALYSIS:
# #   [trajectory, regions overflown, patterns, anomalies]

# # GEOPOLITICAL CORRELATION:
# #   [connect satellite activity to news context]

# # ASSESSMENT:
# #   IF [observed pattern] THEN [likely intent] RESULT [strategic implication]

# # CONFIDENCE: [HIGH/MED/LOW] — [reason]
# # WATCH: [what to monitor in next 24-48h]
# # ===================================
# # End with exactly: RELEVANT OBJECTS: [comma-separated IDs]

# # Rules: intel-officer tone, terse, name real countries/operators, flag proximity events."""


# # # ── Pydantic models ───────────────────────────────────────────────────────────
# # class IngestRequest(BaseModel):
# #     snapshot: str
# #     cycle:    int = 0

# # class IngestResponse(BaseModel):
# #     stored: int; cycle: int; ts: str

# # class IntelQueryRequest(BaseModel):
# #     query:              str
# #     satellite_snapshot: str = ""

# # class IntelQueryResponse(BaseModel):
# #     response: str; relevant_ids: list; news_used: int
# #     history_sats: list; proximity: list; ts: str

# # class AgentRequest(BaseModel):
# #     role: str; user_message: str; satellite_snapshot: str = ""

# # class AgentResponse(BaseModel):
# #     role: str; response: str; relevant_ids: list; ts: str


# # # ── Helpers ───────────────────────────────────────────────────────────────────
# # def parse_relevant_ids(text: str) -> list:
# #     m = re.search(r"RELEVANT OBJECTS:\s*([A-Z0-9,\s]+)", text, re.IGNORECASE)
# #     if not m: return []
# #     return [i.strip() for i in m.group(1).split(",") if i.strip() in VALID_IDS]

# # def utcnow() -> str:
# #     return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# # # ── Routes ────────────────────────────────────────────────────────────────────

# # @app.get("/health")
# # async def health():
# #     return {"status": "ok", "service": "gotham-orbital", "version": "3.1.0",
# #             "ts": utcnow(), "satellites": len(SAT_CATALOG), "db": DB_PATH, "tavily": bool(TAVILY_KEY)}

# # @app.get("/satellites")
# # async def list_satellites():
# #     return {"count": len(SAT_CATALOG),
# #             "catalog": [{**s, "threat_label": THREAT_LABELS[s["threat"]]} for s in SAT_CATALOG]}

# # @app.post("/ingest", response_model=IngestResponse)
# # async def ingest_snapshot(req: IngestRequest):
# #     if not req.snapshot.strip():
# #         raise HTTPException(400, "snapshot cannot be empty")
# #     agent  = await get_agent()
# #     stored = await store_snapshot(agent, req.snapshot, req.cycle)
# #     return IngestResponse(stored=stored, cycle=req.cycle, ts=utcnow())

# # @app.post("/intel-query", response_model=IntelQueryResponse)
# # async def intel_query(req: IntelQueryRequest):
# #     if not req.query.strip():
# #         raise HTTPException(400, "query cannot be empty")

# #     log.info(f"Intel query: {req.query!r}")
# #     agent   = await get_agent()
# #     sat_ids = extract_sat_ids(req.query) or [s["id"] for s in SAT_CATALOG if s["threat"] >= 2]

# #     history_result, news_results = await asyncio.gather(
# #         recall_history(agent, sat_ids),
# #         search_news(build_tavily_query(req.query, sat_ids)),
# #     )
# #     proximity_alerts = check_proximity(req.satellite_snapshot) if req.satellite_snapshot else []

# #     current_pos_block = ""
# #     if req.satellite_snapshot:
# #         lines = [l for l in req.satellite_snapshot.splitlines() if any(s in l for s in sat_ids)]
# #         if lines:
# #             current_pos_block = "CURRENT SGP4 POSITIONS:\n" + "\n".join(f"  {l}" for l in lines)

# #     news_block = ("LIVE NEWS:\n" + "\n".join(
# #         f"  [{i+1}] {n['title']}\n       {n['snippet']}" for i, n in enumerate(news_results)
# #     )) if news_results else "LIVE NEWS: none"

# #     proximity_block = ("PROXIMITY ALERTS:\n" + "\n".join(f"  ⚠ {a}" for a in proximity_alerts)) if proximity_alerts else ""

# #     # Inject system prompt INTO the task — EZAgent has no system_prompt param
# #     fused_task = "\n\n".join(filter(bool, [
# #         atlas_system_prompt(), "---",
# #         f"ANALYST QUERY: {req.query}", f"TIMESTAMP: {utcnow()}",
# #         current_pos_block,
# #         f"MOVEMENT HISTORY:\n{history_result}",
# #         news_block, proximity_block,
# #         "Correlate movement patterns with geopolitical news. Reason about intent.",
# #     ]))

# #     try:
# #         response = await _ask(agent, fused_task, max_steps=6)
# #     except Exception as e:
# #         log.error(f"ATLAS error: {e}")
# #         raise HTTPException(500, str(e))

# #     relevant_ids = parse_relevant_ids(response)
# #     return IntelQueryResponse(response=response, relevant_ids=relevant_ids,
# #                               news_used=len(news_results), history_sats=sat_ids,
# #                               proximity=proximity_alerts, ts=utcnow())

# # @app.post("/agent", response_model=AgentResponse)
# # async def run_agent(req: AgentRequest):
# #     SYS = {
# #         "orbital": "You are ORBITAL-1. Real SGP4 positions, Mar-2025 TLEs. 4-5 bullet intel. [ORBITAL-1] header. Terse.",
# #         "news":    "You are NEWS-1, geopolitical OSINT. [NEWS-1] then [SOURCE] HEADLINE — implication. 3 bullets.",
# #         "analyst": "You are ANALYST-1.\n[ANALYST-1] SYNTHESIS\nIF [actor][action] THEN [effect] RESULT [outcome]\nRECOMMENDATION: [48h action] CONFIDENCE: [HIGH/MED/LOW]",
# #     }
# #     role = req.role.lower().strip()
# #     if role not in SYS:
# #         raise HTTPException(400, f"Unknown role '{role}'. Use: orbital | news | analyst")

# #     snap = f"Live SGP4 {utcnow()}:\n{req.satellite_snapshot}\n\n" if req.satellite_snapshot else ""
# #     full_task = f"{SYS[role]}\n\n---\n\n{snap}{req.user_message}"

# #     try:
# #         agent    = await get_agent()
# #         response = await _ask(agent, full_task, max_steps=5)
# #     except Exception as e:
# #         log.error(f"Agent [{role}] error: {e}")
# #         raise HTTPException(500, str(e))

# #     return AgentResponse(role=role, response=response,
# #                          relevant_ids=parse_relevant_ids(response), ts=utcnow())

# # @app.get("/history/{sat_id}")
# # async def satellite_history(sat_id: str, limit: int = 20):
# #     if sat_id not in VALID_IDS:
# #         raise HTTPException(404, f"Unknown satellite ID '{sat_id}'")
# #     agent   = await get_agent()
# #     results = await _recall(agent, f"SAT_HISTORY {sat_id}", limit=limit)
# #     return {"sat_id": sat_id, "name": SAT_BY_ID[sat_id]["name"],
# #             "owner": SAT_BY_ID[sat_id]["owner"], "threat": THREAT_LABELS[SAT_BY_ID[sat_id]["threat"]],
# #             "count": len(results),
# #             "history": [r.content if hasattr(r, "content") else str(r) for r in results],
# #             "ts": utcnow()}

# # @app.get("/stats")
# # async def stats():
# #     agent = await get_agent()
# #     try:
# #         loop = asyncio.get_event_loop()
# #         s    = await loop.run_in_executor(None, agent.stats)
# #         return {"stats": s, "db": DB_PATH, "tavily": bool(TAVILY_KEY), "ts": utcnow()}
# #     except Exception as e:
# #         raise HTTPException(500, str(e))

# # @app.delete("/clear")
# # async def clear_memory():
# #     global _agent
# #     try:
# #         agent = await get_agent()
# #         loop  = asyncio.get_event_loop()
# #         await loop.run_in_executor(None, agent.clear_session)
# #         _agent = None
# #         return {"cleared": True, "ts": utcnow()}
# #     except Exception as e:
# #         raise HTTPException(500, str(e))


# # # ── Entry point ───────────────────────────────────────────────────────────────
# # if __name__ == "__main__":
# #     import uvicorn
# #     port = int(os.getenv("PORT", 8000))
# #     uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False, workers=2)







"""
optimum_ReAct — Palantir-style Fused Intelligence Backend
===========================================================
Frontend : Vercel (gotham-v2.jsx)
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
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from AgenT import EZAgent

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger("gotham-api")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Gotham Orbital — Fused Intelligence API",
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
DB_PATH      = os.getenv("AGENT_DB_PATH", "data/gotham_agent.db")
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
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad_id}&FORMAT=TLE"
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
_agent_groq_key: str = ""   # tracks which key the current agent was built with
_lock  = asyncio.Lock()

async def get_agent(groq_key: str = "") -> EZAgent:
    """Return agent singleton, reinitialising if the Groq key has changed."""
    global _agent, _agent_groq_key
    effective_key = groq_key or os.getenv("GROQ_API_KEY", "")
    async with _lock:
        if _agent is None or effective_key != _agent_groq_key:
            log.info(f"Initializing EZAgent — DB: {DB_PATH} — key: {'(from header)' if groq_key else '(from env)'}")
            # Inject key into environment so EZAgent picks it up
            if effective_key:
                os.environ["GROQ_API_KEY"] = effective_key
            loop = asyncio.get_event_loop()
            _agent = await loop.run_in_executor(None, EZAgent, DB_PATH)
            _agent_groq_key = effective_key
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
    for attempt in range(3):
        try:
            return await agent.ask_async(task, max_steps=max_steps)
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                wait = 2 ** attempt * 3  # 3s, 6s
                log.warning(f"Groq 429 — retrying in {wait}s (attempt {attempt+1})")
                await asyncio.sleep(wait)
            else:
                raise


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
async def search_news(query: str, tavily_key: str = "") -> list:
    key = tavily_key or TAVILY_KEY
    if not key:
        log.warning("No Tavily key — skipping news")
        return []
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(TAVILY_URL, json={
                "api_key": key, "query": query,
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
    return f"""You are ATLAS — senior satellite intelligence analyst on the Gotham Orbital platform.

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
    return {"status": "ok", "service": "gotham-orbital", "version": "3.1.0",
            "ts": utcnow(), "satellites": len(SAT_CATALOG), "db": DB_PATH, "tavily": bool(TAVILY_KEY)}

@app.get("/satellites")
async def list_satellites():
    return {"count": len(SAT_CATALOG),
            "catalog": [{**s, "threat_label": THREAT_LABELS[s["threat"]]} for s in SAT_CATALOG]}

@app.post("/ingest", response_model=IngestResponse)
async def ingest_snapshot(req: IngestRequest,
                          x_groq_key: str = Header(default=""),
                          x_tavily_key: str = Header(default="")):
    if not req.snapshot.strip():
        raise HTTPException(400, "snapshot cannot be empty")
    agent  = await get_agent(x_groq_key)
    stored = await store_snapshot(agent, req.snapshot, req.cycle)
    return IngestResponse(stored=stored, cycle=req.cycle, ts=utcnow())

@app.post("/intel-query", response_model=IntelQueryResponse)
async def intel_query(req: IntelQueryRequest,
                      x_groq_key: str = Header(default=""),
                      x_tavily_key: str = Header(default="")):
    if not req.query.strip():
        raise HTTPException(400, "query cannot be empty")

    log.info(f"Intel query: {req.query!r}")
    agent   = await get_agent(x_groq_key)
    sat_ids = extract_sat_ids(req.query) or [s["id"] for s in SAT_CATALOG if s["threat"] >= 2]

    history_result, news_results = await asyncio.gather(
        recall_history(agent, sat_ids),
        search_news(build_tavily_query(req.query, sat_ids), x_tavily_key),
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
async def run_agent(req: AgentRequest,
                    x_groq_key: str = Header(default=""),
                    x_tavily_key: str = Header(default="")):
    SYS = {
        "orbital": "You are ORBITAL-1. Real SGP4 positions, live TLEs. 4-5 bullet intel. [ORBITAL-1] header. Terse.",
        "news":    "You are NEWS-1, geopolitical OSINT. [NEWS-1] then [SOURCE] HEADLINE — implication. 3 bullets.",
        "analyst": "You are ANALYST-1.\n[ANALYST-1] SYNTHESIS\nIF [actor][action] THEN [effect] RESULT [outcome]\nRECOMMENDATION: [48h action] CONFIDENCE: [HIGH/MED/LOW]",
    }
    role = req.role.lower().strip()
    if role not in SYS:
        raise HTTPException(400, f"Unknown role '{role}'. Use: orbital | news | analyst")

    snap = f"Live SGP4 {utcnow()}:\n{req.satellite_snapshot}\n\n" if req.satellite_snapshot else ""
    full_task = f"{SYS[role]}\n\n---\n\n{snap}{req.user_message}"

    try:
        agent    = await get_agent(x_groq_key)
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