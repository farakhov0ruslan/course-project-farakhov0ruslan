import asyncio
import random
from urllib.parse import urlparse

import httpx

_ALLOWED_HOSTS = {"api.stackexchange.com"}
_TIMEOUTS = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
_LIMITS = httpx.Limits(
    max_connections=20, max_keepalive_connections=10, keepalive_expiry=30.0
)


class SafeHttpClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=_TIMEOUTS, limits=_LIMITS, headers={"User-Agent": "notes-app/1.0"}
        )

    async def get_json(
        self, url: str, params: dict | None = None, *, retries: int = 3
    ) -> dict:
        host = urlparse(url).hostname or ""
        if host not in _ALLOWED_HOSTS:
            raise ValueError(f"Host not allowed: {host}")
        backoff = 0.2
        for attempt in range(retries + 1):
            r = await self._client.get(url, params=params)
            if r.status_code < 400:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 2.0) + random.random() * 0.1
                continue
            r.raise_for_status()
        raise RuntimeError("unreachable")

    async def aclose(self) -> None:
        await self._client.aclose()


safe_http = SafeHttpClient()
