import json
import random
import time
import asyncio
import os
import aiohttp
from typing import Dict, List, Optional

PROXIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw_proxies.json")

class ProxyEngine:
    def __init__(self):
        self.all_proxies: List[str] = []
        self.live_proxies: List[str] = []
        self.protocols: Dict[str, int] = {}
        self.last_check_time: float = 0
        self.is_checking: bool = False
        self.lock = asyncio.Lock()
        self.stats = {
            "total": 0,
            "live": 0,
            "tested": 0,
            "dead": 0,
            "protocols": {}
        }
        self.load_proxies()

    def load_proxies(self):
        if os.path.exists(PROXIES_FILE):
            try:
                with open(PROXIES_FILE, "r") as f:
                    self.all_proxies = json.load(f)
            except Exception as e:
                print(f"[!] Error loading proxies: {e}")
                self.all_proxies = []

        self.protocols = {}
        for p in self.all_proxies:
            proto = p.split("://")[0] if "://" in p else "http"
            self.protocols[proto] = self.protocols.get(proto, 0) + 1

        self.stats["total"] = len(self.all_proxies)
        self.stats["protocols"] = self.protocols
        # Initially assume all are candidates
        self.live_proxies = list(self.all_proxies)
        self.stats["live"] = len(self.live_proxies)
        print(f"[ProxyEngine] Loaded {len(self.all_proxies)} proxies across protocols: {self.protocols}")

    def get_random_proxy(self, protocol: Optional[str] = None) -> Optional[str]:
        pool = self.live_proxies if self.live_proxies else self.all_proxies
        if protocol:
            p_lower = protocol.lower()
            filtered = [p for p in pool if p.lower().startswith(f"{p_lower}://")]
            if filtered:
                return random.choice(filtered)
        if pool:
            return random.choice(pool)
        return None

    def get_all_proxies(self, protocol: Optional[str] = None, only_live: bool = False) -> List[str]:
        pool = self.live_proxies if (only_live and self.live_proxies) else self.all_proxies
        if protocol:
            p_lower = protocol.lower()
            return [p for p in pool if p.lower().startswith(f"{p_lower}://")]
        return pool

    def add_proxies(self, new_lines: List[str]) -> int:
        added = 0
        existing = set(self.all_proxies)
        for line in new_lines:
            line = line.strip()
            if not line:
                continue
            if not line.startswith(("http://", "https://", "socks4://", "socks5://")):
                line = f"http://{line}"
            if line not in existing:
                self.all_proxies.append(line)
                existing.add(line)
                added += 1

        if added > 0:
            with open(PROXIES_FILE, "w") as f:
                json.dump(self.all_proxies, f, indent=2)
            self.load_proxies()
        return added

    async def check_proxy(self, proxy_url: str, session: aiohttp.ClientSession, test_url: str = "http://httpbin.org/ip") -> bool:
        try:
            # aiohttp handles http/https natively and socks via aiohttp-socks
            async with session.get(test_url, proxy=proxy_url, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        return False

    async def health_check_round(self, sample_size: int = 150):
        if self.is_checking or not self.all_proxies:
            return
        self.is_checking = True
        try:
            candidates = random.sample(self.all_proxies, min(sample_size, len(self.all_proxies)))
            verified = []

            # Only test http/https with pure aiohttp for fast response
            http_candidates = [c for c in candidates if c.startswith(("http://", "https://"))]
            async with aiohttp.ClientSession() as session:
                tasks = [self.check_proxy(p, session) for p in http_candidates]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for p, is_ok in zip(http_candidates, results):
                    if is_ok is True:
                        verified.append(p)

            async with self.lock:
                if verified:
                    # Update live pool keeping non-http as fallbacks
                    socks_proxies = [p for p in self.all_proxies if p.startswith(("socks4://", "socks5://"))]
                    self.live_proxies = verified + socks_proxies
                    self.stats["live"] = len(self.live_proxies)
                self.last_check_time = time.time()
                print(f"[ProxyEngine] Health check finished. Verified HTTP: {len(verified)}. Active pool: {len(self.live_proxies)}")
        except Exception as e:
            print(f"[!] Health check error: {e}")
        finally:
            self.is_checking = False

# Global instance
engine = ProxyEngine()
