# bot/services/vut_api.py
from __future__ import annotations

import asyncio
import time

import aiohttp


class VutApiError(Exception):
    pass


class InvalidApiKey(VutApiError):
    pass


class RateLimited(VutApiError):
    pass


class VutApiClient:
    DEFAULT_BASE = "https://www.vut.cz/api/person/v1"

    def __init__(
        self,
        api_key: str,
        owner_id: str | int,
        use_client_credentials: bool = False,
        allow_static_token_fallback: bool = True,
        client_id: str = "",
        client_secret: str = "",
        token_url: str = "",
        api_base: str = DEFAULT_BASE,
    ):
        self._api_key = api_key
        self._owner_id = str(owner_id)

        self._use_client_credentials = use_client_credentials
        self._allow_static_token_fallback = allow_static_token_fallback

        self._client_id = client_id
        self._client_secret = client_secret
        self._token_url = token_url
        self._api_base = api_base.rstrip("/")

        self._generated_access_token: str | None = None
        self._generated_token_expires_at: float = 0
        self._token_lock = asyncio.Lock()

        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        timeout = aiohttp.ClientTimeout(total=10)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    def _static_token_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Author": self._owner_id,
        }

    async def _get_generated_access_token(self) -> str:
        if not self.session:
            raise RuntimeError("VutApiClient neni inicializovany. Zavolej start().")

        if self._generated_access_token and time.time() < self._generated_token_expires_at - 60:
            return self._generated_access_token

        async with self._token_lock:
            if self._generated_access_token and time.time() < self._generated_token_expires_at - 60:
                return self._generated_access_token

            if not self._client_id or not self._client_secret or not self._token_url:
                raise VutApiError("Client credentials nejsou nastavene.")

            data = {
                "grant_type": "client_credentials",
            }

            auth = aiohttp.BasicAuth(self._client_id, self._client_secret)

            async with self.session.post(self._token_url, data=data, auth=auth) as response:
                if response.status in (401, 403):
                    raise InvalidApiKey("Neplatne VUT client_id/client_secret.")

                if response.status == 429:
                    raise RateLimited("Prekrocen limit generovani VUT access tokenu.")

                if response.status != 200:
                    text = await response.text()
                    raise VutApiError(f"Token endpoint vratil HTTP {response.status}: {text}")

                payload = await response.json()

            access_token = payload.get("access_token")
            expires_in = int(payload.get("expires_in", 3600))

            if not access_token:
                raise VutApiError("Token response neobsahuje access_token.")

            self._generated_access_token = access_token
            self._generated_token_expires_at = time.time() + expires_in

            return self._generated_access_token

    async def _generated_token_headers(self) -> dict[str, str]:
        access_token = await self._get_generated_access_token()

        return {
            "Authorization": f"Bearer {access_token}",
            "Author": self._owner_id,
        }

    async def _get_json_with_headers(self, user_id: str, headers: dict[str, str]) -> dict | None:
        if not self.session:
            raise RuntimeError("VutApiClient neni inicializovany. Zavolej start().")

        url = f"{self._api_base}/{user_id}/pusobeni-osoby"

        async with self.session.get(url, headers=headers) as response:
            if response.status in (401, 403):
                raise InvalidApiKey("Invalid VUT API credentials")

            if response.status == 429:
                raise RateLimited("Rate limit exceeded")

            if response.status != 200:
                return None

            return await response.json()

    async def _get_user_details_static_token(self, user_id: str) -> dict | None:
        if not self._api_key:
            raise VutApiError("VUT_API_KEY neni nastaveny.")

        return await self._get_json_with_headers(user_id, self._static_token_headers())

    async def _get_user_details_generated_token(self, user_id: str) -> dict | None:
        headers = await self._generated_token_headers()

        try:
            return await self._get_json_with_headers(user_id, headers)
        except InvalidApiKey:
            # Token can be expired/revoked earlier than expected. Clear cache once.
            self._generated_access_token = None
            self._generated_token_expires_at = 0

            headers = await self._generated_token_headers()
            return await self._get_json_with_headers(user_id, headers)

    async def get_user_details(self, user_id: str) -> dict | None:
        """
        user_id = 6mistne VUT cislo nebo login, napr. xlogin00.
        Vraci dict, nebo None, kdyz login/ID neexistuje.
        """
        user_id = user_id.strip().lower()

        if not self._use_client_credentials:
            return await self._get_user_details_static_token(user_id)

        try:
            return await self._get_user_details_generated_token(user_id)

        except (InvalidApiKey, RateLimited, VutApiError) as error:
            if not self._allow_static_token_fallback:
                raise

            print(f"[VUT API] Generated token failed, trying static token fallback: {error}")
            return await self._get_user_details_static_token(user_id)
