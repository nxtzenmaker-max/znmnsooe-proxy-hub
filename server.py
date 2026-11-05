import os
import asyncio
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import aiohttp

from proxy_engine import engine

app = FastAPI(
    title="ZnMnsooePay Rotating Proxy Hub",
    description="High-Speed Rotating Proxy Balancer & API for znmnsooepay.store",
    version="1.0.0"
)

# Enable CORS for cross-domain requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount public directory for frontend dashboard
PUBLIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")
if os.path.exists(PUBLIC_DIR):
    app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")

@app.on_event("startup")
async def startup_event():
    # Schedule periodic health-check in background
    async def periodic_checker():
        await asyncio.sleep(5)
        while True:
            try:
                await engine.health_check_round(sample_size=100)
            except Exception as e:
                print(f"[!] Error in background health check: {e}")
            await asyncio.sleep(300) # Every 5 minutes

    asyncio.create_task(periodic_checker())

@app.get("/", response_class=HTMLResponse)
async def serve_home():
    index_path = os.path.join(PUBLIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>ZnMnsooePay Rotating Proxy Gateway Online</h1>"

@app.get("/api/status")
async def get_status():
    return {
        "status": "online",
        "service": "ZnMnsooePay Proxy Gateway",
        "domain": "znmnsooepay.store",
        "engine": "RJN's AI Async Proxy Balancer",
        "total_proxies": engine.stats["total"],
        "live_pool": engine.stats["live"],
        "protocols": engine.stats["protocols"],
        "last_health_check": engine.last_check_time,
        "is_checking": engine.is_checking
    }

@app.get("/api/proxy")
async def get_single_proxy(
    protocol: Optional[str] = Query(None, description="Filter by protocol: socks5, http, https, socks4"),
    format: Optional[str] = Query("json", description="Output format: json or text")
):
    proxy = engine.get_random_proxy(protocol=protocol)
    if not proxy:
        raise HTTPException(status_code=503, detail="No active proxy available matching filter")

    proto = proxy.split("://")[0]
    host_port = proxy.split("://")[1]
    ip, port = host_port.split(":") if ":" in host_port else (host_port, "")

    if format == "text":
        return PlainTextResponse(proxy)

    return {
        "proxy": proxy,
        "protocol": proto,
        "ip": ip,
        "port": port,
        "endpoint": f"http://znmnsooepay.store/api/proxy",
        "domain": "znmnsooepay.store"
    }

@app.get("/api/proxies.txt", response_class=PlainTextResponse)
async def get_proxies_text(
    protocol: Optional[str] = Query(None, description="Filter protocol"),
    only_live: bool = Query(False, description="Filter only verified live")
):
    proxies = engine.get_all_proxies(protocol=protocol, only_live=only_live)
    return "\n".join(proxies)

class AddProxiesRequest(BaseModel):
    proxies: List[str]

@app.post("/api/add")
async def add_proxies_endpoint(req: AddProxiesRequest):
    added = engine.add_proxies(req.proxies)
    return {
        "success": True,
        "added": added,
        "new_total": len(engine.all_proxies)
    }

@app.get("/api/fetch")
async def fetch_through_proxy(url: str = Query(..., description="Target URL to fetch via rotating proxy")):
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL scheme")

    # Pick a random working HTTP/HTTPS proxy
    proxy = engine.get_random_proxy(protocol="http") or engine.get_random_proxy(protocol="https")
    if not proxy:
        proxy = engine.get_random_proxy()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                content = await resp.read()
                return HTMLResponse(
                    content=content,
                    status_code=resp.status,
                    headers={"X-Rotated-Proxy": str(proxy)}
                )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Proxy fetch error through {proxy}: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
