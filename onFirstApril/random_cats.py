import os
import random
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp
import discord
from discord.ext import commands


CHANNEL_IDS = [
    1358888500845346866,
    1358913164493852682,
]

TIMEZONE_NAME = "Europe/Prague"

CAT_TEXT = "Check this out:"

# muzes nechat prazdne, The Cat API cast bude fungovat i bez nej v jednodussim rezimu,
# ale kdyz si vygenerujes klic, dej ho do .env jako THE_CAT_API_KEY
THE_CAT_API_KEY = os.getenv("THE_CAT_API_KEY", "")

# zapinani/vypinani
ENABLE_ENV_NAME = "ENABLE_RANDOM_CATS"
APRIL_ONLY_ENV_NAME = "RANDOM_CATS_ONLY_ON_FIRST_APRIL"


class RandomCats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.loop_task = None
        self.last_url = None
        self.http_session = None
        print("[random_cats] __init__ called", flush=True)

    async def cog_load(self):
        print("[random_cats] cog_load called", flush=True)
        timeout = aiohttp.ClientTimeout(total=15)
        self.http_session = aiohttp.ClientSession(timeout=timeout)
        self.loop_task = asyncio.create_task(self.run_loop())

    async def cog_unload(self):
        print("[random_cats] cog_unload called", flush=True)

        if self.loop_task:
            self.loop_task.cancel()

        if self.http_session and not self.http_session.closed:
            await self.http_session.close()

    def is_enabled(self) -> bool:
        return os.getenv(ENABLE_ENV_NAME, "true").lower() == "true"

    def april_only(self) -> bool:
        return os.getenv(APRIL_ONLY_ENV_NAME, "false").lower() == "true"

    def can_send_now(self) -> bool:
        if not self.is_enabled():
            return False

        if not self.april_only():
            return True

        now = datetime.now(ZoneInfo(TIMEZONE_NAME))
        return now.month == 4 and now.day == 1

    async def fetch_from_the_cat_api(self) -> str | None:
        url = "https://api.thecatapi.com/v1/images/search"
        headers = {}

        if THE_CAT_API_KEY:
            headers["x-api-key"] = THE_CAT_API_KEY

        try:
            async with self.http_session.get(url, headers=headers) as response:
                if response.status != 200:
                    print(f"[random_cats] The Cat API bad status: {response.status}", flush=True)
                    return None

                data = await response.json()
                if not data:
                    return None

                image_url = data[0].get("url")
                return image_url
        except Exception as e:
            print(f"[random_cats] The Cat API error: {type(e).__name__}: {e}", flush=True)
            return None

    async def fetch_from_cataas(self) -> str | None:
        # cataas umi vratit JSON s URL
        url = "https://cataas.com/cat?json=true"

        try:
            async with self.http_session.get(url) as response:
                if response.status != 200:
                    print(f"[random_cats] CATAAS bad status: {response.status}", flush=True)
                    return None

                data = await response.json()
                image_path = data.get("url")

                if not image_path:
                    return None

                if image_path.startswith("http://") or image_path.startswith("https://"):
                    return image_path

                return f"https://cataas.com{image_path}"
        except Exception as e:
            print(f"[random_cats] CATAAS error: {type(e).__name__}: {e}", flush=True)
            return None

    async def fetch_random_cat_url(self) -> str | None:
        # nahodne prohazuje zdroje
        fetchers = [
            self.fetch_from_the_cat_api,
            self.fetch_from_cataas,
        ]
        random.shuffle(fetchers)

        for fetcher in fetchers:
            image_url = await fetcher()
            if image_url:
                return image_url

        return None

    async def pick_cat_url(self) -> str | None:
        if self.http_session is None or self.http_session.closed:
            return None

        # zkusime nekolikrat, aby se neopakovala hned stejna URL
        for _ in range(5):
            image_url = await self.fetch_random_cat_url()
            if image_url and image_url != self.last_url:
                self.last_url = image_url
                return image_url

        # fallback, i kdyby se opakovalo
        image_url = await self.fetch_random_cat_url()
        if image_url:
            self.last_url = image_url
        return image_url

    async def send_to_channel(self, channel_id: int, image_url: str):
        try:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                channel = await self.bot.fetch_channel(channel_id)

            await channel.send(f"{CAT_TEXT} {image_url}")
            print(f"[random_cats] sent ok to channel {channel_id}", flush=True)

        except discord.Forbidden:
            print(f"[random_cats] no permission for channel {channel_id}", flush=True)
        except discord.HTTPException as e:
            print(f"[random_cats] discord error in channel {channel_id}: {e}", flush=True)
        except Exception as e:
            print(f"[random_cats] unexpected error in channel {channel_id}: {e}", flush=True)

    async def run_loop(self):
        print("[random_cats] run_loop started", flush=True)
        await self.bot.wait_until_ready()
        print(f"[random_cats] bot ready as {self.bot.user} | id = {self.bot.user.id}", flush=True)

        while not self.bot.is_closed():
            try:
                if not self.can_send_now():
                    await asyncio.sleep(30)
                    continue

                image_url = await self.pick_cat_url()
                if not image_url:
                    print("[random_cats] no cat url fetched", flush=True)
                    await asyncio.sleep(30)
                    continue

                for channel_id in CHANNEL_IDS:
                    await self.send_to_channel(channel_id, image_url)

                delay = random.randint(30, 90)
                print(f"[random_cats] sleeping for {delay}s", flush=True)
                await asyncio.sleep(delay)

            except asyncio.CancelledError:
                print("[random_cats] loop cancelled", flush=True)
                break
            except Exception as e:
                print(f"[random_cats] ERROR: {type(e).__name__}: {e}", flush=True)
                await asyncio.sleep(15)


async def setup(bot: commands.Bot):
    print("[random_cats] setup called", flush=True)
    await bot.add_cog(RandomCats(bot))
