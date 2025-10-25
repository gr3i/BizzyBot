import asyncio
from services.vut_api import VutApiClient
from config import Config

async def main():
    cfg = Config()
    if not cfg.vut_api_key:
        print("VUT_API_KEY se nenačetl. Zkontroluj .env.")
        return
    print(f"Načtený API klíč: {cfg.vut_api_key[:8]}...")

    client = VutApiClient(cfg.vut_api_key, "local-test")
    await client.start()
    try:
        user_id = input("Zadej VUT login nebo číslo (např. 123456 / xlogin00): ").strip()
        data = await client.get_user_details(user_id)
        print("\nOdpověď z API:")
        print(data)
    except Exception as e:
        print(f"Chyba: {e}")
    finally:
        await client.close()

asyncio.run(main())

