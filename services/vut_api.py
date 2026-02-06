# bot/services/vut_api.py
from __future__ import annotations
import aiohttp

class VutApiError(Exception):
    pass

class InvalidApiKey(VutApiError):
    pass

class RateLimited(VutApiError):
    pass

class VutApiClient:
    BASE = "https://www.vut.cz/api/person/v1"

    def __init__(self, api_key: str, owner_id: str | int):
        self._api_key = api_key
        self._owner_id = str(owner_id)
        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Author": self._owner_id,
        }
        timeout = aiohttp.ClientTimeout(total=10)
        self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_user_details(self, user_id: str) -> dict | None:
        """
        user_id = 6mistné VUT cislo nebo login (napr. xlogin00).
        Vraci dict (JSON) nebo None, kdyz login/ID neexistuje.
        """
        if not self.session:
            raise RuntimeError("VutApiClient neni inicializovany. Zavolej start().")

        url = f"{self.BASE}/{user_id}/pusobeni-osoby"
        async with self.session.get(url) as res:
            if res.status != 200:
                if res.status in (401, 403):
                    raise InvalidApiKey("Invalid API key")
                if res.status == 429:
                    raise RateLimited("Rate limit exceeded")
                # 404 apod. – login/ID nenalezeno
                return None
            return await res.json()

