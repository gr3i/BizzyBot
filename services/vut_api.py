from __future__ import annotations

import asyncio
import logging
import time

import aiohttp


logger = logging.getLogger(__name__)


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
        token_url: str = "https://id.vut.cz/auth/common/oauth2/token",
        scope: str = "",
        token_auth_method: str = "basic",
        api_base: str = DEFAULT_BASE,
    ):
        self._api_key = api_key
        self._owner_id = str(owner_id)

        self._use_client_credentials = use_client_credentials
        self._allow_static_token_fallback = allow_static_token_fallback

        self._client_id = client_id
        self._client_secret = client_secret
        self._token_url = token_url
        self._scope = scope.strip()
        self._token_auth_method = (token_auth_method or "basic").strip().lower()
        self._api_base = api_base.rstrip("/")

        self._generated_access_token: str | None = None
        self._generated_token_expires_at: float = 0
        self._token_lock = asyncio.Lock()

        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        timeout = aiohttp.ClientTimeout(total=10)
        self.session = aiohttp.ClientSession(timeout=timeout)

        logger.info(
            "VUT API client started. mode=%s, static_fallback=%s, api_base=%s",
            "client_credentials" if self._use_client_credentials else "static_token",
            self._allow_static_token_fallback,
            self._api_base,
        )

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    def _static_token_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Author": self._owner_id,
        }

    async def _request_generated_access_token(self, auth_method: str) -> dict:
        if not self.session:
            raise RuntimeError("VutApiClient neni inicializovany. Zavolej start().")

        data = {
            "grant_type": "client_credentials",
        }

        if self._scope:
            data["scope"] = self._scope

        request_kwargs = {
            "data": data,
        }

        if auth_method == "post":
            data["client_id"] = self._client_id
            data["client_secret"] = self._client_secret
        else:
            request_kwargs["auth"] = aiohttp.BasicAuth(
                self._client_id,
                self._client_secret,
            )

        logger.info(
            "Requesting VUT access token. auth_method=%s, scope_set=%s",
            auth_method,
            bool(self._scope),
        )

        async with self.session.post(self._token_url, **request_kwargs) as response:
            if response.status in (401, 403):
                logger.warning(
                    "VUT token request rejected. auth_method=%s, http_status=%s",
                    auth_method,
                    response.status,
                )
                raise InvalidApiKey("Neplatne VUT client_id/client_secret.")

            if response.status == 429:
                logger.warning("VUT token request rate limited.")
                raise RateLimited("Prekrocen limit generovani VUT access tokenu.")

            if response.status != 200:
                text = await response.text()
                logger.warning(
                    "VUT token endpoint failed. auth_method=%s, http_status=%s, response=%s",
                    auth_method,
                    response.status,
                    text[:500],
                )
                raise VutApiError(
                    f"Token endpoint vratil HTTP {response.status}: {text[:500]}"
                )

            payload = await response.json()
            logger.info("VUT access token generated successfully.")
            return payload

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

            auth_methods = [self._token_auth_method]

            if self._token_auth_method == "basic":
                auth_methods.append("post")
            elif self._token_auth_method == "post":
                auth_methods.append("basic")

            last_error: Exception | None = None

            for auth_method in auth_methods:
                try:
                    payload = await self._request_generated_access_token(auth_method)
                    break
                except InvalidApiKey as error:
                    last_error = error
                    logger.warning(
                        "VUT access token attempt failed because credentials were rejected. auth_method=%s",
                        auth_method,
                    )
                    continue
                except VutApiError as error:
                    last_error = error
                    logger.warning(
                        "VUT access token attempt failed. auth_method=%s, error=%s",
                        auth_method,
                        error,
                    )
                    continue
            else:
                if last_error:
                    raise last_error

                raise VutApiError("Nepodarilo se ziskat VUT access token.")

            access_token = payload.get("access_token")
            expires_in = int(payload.get("expires_in", 3600))

            if not access_token:
                logger.warning("VUT token response does not contain access_token.")
                raise VutApiError("Token response neobsahuje access_token.")

            self._generated_access_token = access_token
            self._generated_token_expires_at = time.time() + expires_in

            logger.info("VUT access token cached. expires_in=%s seconds", expires_in)

            return self._generated_access_token

    async def _generated_token_headers(self) -> dict[str, str]:
        access_token = await self._get_generated_access_token()

        return {
            "Authorization": f"Bearer {access_token}",
            "Author": self._owner_id,
        }

    async def _get_json_with_headers(
        self,
        user_id: str,
        headers: dict[str, str],
        auth_source: str,
    ) -> dict | None:
        if not self.session:
            raise RuntimeError("VutApiClient neni inicializovany. Zavolej start().")

        url = f"{self._api_base}/{user_id}/pusobeni-osoby"

        logger.info(
            "Calling VUT API. user_id=%s, auth_source=%s",
            user_id,
            auth_source,
        )

        async with self.session.get(url, headers=headers) as response:
            if response.status in (401, 403):
                logger.warning(
                    "VUT API rejected credentials. user_id=%s, auth_source=%s, http_status=%s",
                    user_id,
                    auth_source,
                    response.status,
                )
                raise InvalidApiKey("Invalid VUT API credentials")

            if response.status == 429:
                logger.warning(
                    "VUT API rate limited. user_id=%s, auth_source=%s",
                    user_id,
                    auth_source,
                )
                raise RateLimited("Rate limit exceeded")

            if response.status != 200:
                logger.info(
                    "VUT API returned no usable data. user_id=%s, auth_source=%s, http_status=%s",
                    user_id,
                    auth_source,
                    response.status,
                )
                return None

            logger.info(
                "VUT API request successful. user_id=%s, auth_source=%s",
                user_id,
                auth_source,
            )

            return await response.json()

    async def _get_user_details_static_token(self, user_id: str) -> dict | None:
        if not self._api_key:
            raise VutApiError("VUT_API_KEY neni nastaveny.")

        return await self._get_json_with_headers(
            user_id=user_id,
            headers=self._static_token_headers(),
            auth_source="static_token",
        )

    async def _get_user_details_generated_token(self, user_id: str) -> dict | None:
        headers = await self._generated_token_headers()

        try:
            return await self._get_json_with_headers(
                user_id=user_id,
                headers=headers,
                auth_source="client_credentials",
            )
        except InvalidApiKey:
            logger.warning(
                "Generated VUT access token was rejected. Clearing token cache and retrying once."
            )

            self._generated_access_token = None
            self._generated_token_expires_at = 0

            headers = await self._generated_token_headers()

            return await self._get_json_with_headers(
                user_id=user_id,
                headers=headers,
                auth_source="client_credentials_retry",
            )

    async def get_user_details(self, user_id: str) -> dict | None:
        user_id = user_id.strip().lower()

        if not self._use_client_credentials:
            logger.info("Using old static VUT token as primary auth method.")
            return await self._get_user_details_static_token(user_id)

        try:
            logger.info("Using new VUT client credentials as primary auth method.")
            return await self._get_user_details_generated_token(user_id)

        except (InvalidApiKey, RateLimited, VutApiError) as primary_error:
            logger.warning(
                "Primary VUT client credentials auth failed. error=%s",
                primary_error,
            )

            if not self._allow_static_token_fallback:
                logger.error(
                    "Static token fallback is disabled. Verification cannot continue."
                )
                raise

            if not self._api_key:
                logger.error(
                    "Static token fallback is enabled, but VUT_API_KEY is not configured."
                )
                raise

            logger.warning("Trying old static VUT token fallback.")

            try:
                result = await self._get_user_details_static_token(user_id)
                logger.info("Old static VUT token fallback finished successfully.")
                return result
            except (InvalidApiKey, RateLimited, VutApiError) as fallback_error:
                logger.exception(
                    "Old static VUT token fallback also failed. error=%s",
                    fallback_error,
                )
                raise
