import asyncio
import logging
import os

from services.vut_api import VutApiClient
from config import Config


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


async def main():
    cfg = Config()

    if cfg.vut_use_client_credentials:
        missing = []

        if not cfg.vut_client_id:
            missing.append("VUT_CLIENT_ID")

        if not cfg.vut_client_secret:
            missing.append("VUT_CLIENT_SECRET")

        if not cfg.vut_token_url:
            missing.append("VUT_TOKEN_URL")

        if missing:
            print("Chybi promenne v .env: " + ", ".join(missing))
            return

        print("Testuji VUT API pres client credentials.")

        if cfg.vut_allow_static_token_fallback:
            print("Static token fallback je zapnuty.")
        else:
            print("Static token fallback je vypnuty.")

    else:
        if not cfg.vut_api_key:
            print(
                "VUT_API_KEY se nenacetl. Zkontroluj .env nebo zapni VUT_USE_CLIENT_CREDENTIALS=true."
            )
            return

        print(f"Testuji VUT API pres stary staticky token: {cfg.vut_api_key[:8]}...")

    client = VutApiClient(
        api_key=cfg.vut_api_key,
        owner_id=cfg.owner_id,
        use_client_credentials=cfg.vut_use_client_credentials,
        allow_static_token_fallback=cfg.vut_allow_static_token_fallback,
        client_id=cfg.vut_client_id,
        client_secret=cfg.vut_client_secret,
        token_url=cfg.vut_token_url,
        scope=cfg.vut_scope,
        token_auth_method=cfg.vut_token_auth_method,
        api_base=cfg.vut_api_base,
    )

    await client.start()

    try:
        user_id = input("Zadej VUT login nebo cislo, napr. xlogin00 / 123456: ").strip()
        data = await client.get_user_details(user_id)

        print("\nOdpoved z API:")
        print(data)

    except Exception as error:
        print(f"Chyba: {error}")

    finally:
        await client.close()


asyncio.run(main())
