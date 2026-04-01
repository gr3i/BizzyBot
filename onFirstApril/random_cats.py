import os
import random
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp
import discord
from discord.ext import commands


TIMEZONE_NAME = "Europe/Prague"
THE_CAT_API_KEY = os.getenv("THE_CAT_API_KEY", "")

ENABLE_ENV_NAME = "ENABLE_RANDOM_CATS"
APRIL_ONLY_ENV_NAME = "RANDOM_CATS_ONLY_ON_FIRST_APRIL"

CHANNEL_CONFIGS = [
    {
        "channel_id": 1358888500845346866,
        "delay_min": 15,
        "delay_max": 45,
    },
    {
        "channel_id": 1358913164493852682,
        "delay_min": 20,
        "delay_max": 40,
    },
]


class RandomCats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.http_session = None
        self.channel_tasks = []
        self.last_url_by_channel = {}
        print("[random_cats] __init__ called", flush=True)

    async def cog_load(self):
        print("[random_cats] cog_load called", flush=True)
        timeout = aiohttp.ClientTimeout(total=15)
        self.http_session = aiohttp.ClientSession(timeout=timeout)

        for config in CHANNEL_CONFIGS:
            task = asyncio.create_task(self.run_channel_loop(config))
            self.channel_tasks.append(task)

    async def cog_unload(self):
        print("[random_cats] cog_unload called", flush=True)

        for task in self.channel_tasks:
            task.cancel()

        if self.channel_tasks:
            await asyncio.gather(*self.channel_tasks, return_exceptions=True)

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

                return data[0].get("url")
        except Exception as e:
            print(f"[random_cats] The Cat API error: {type(e).__name__}: {e}", flush=True)
            return None

    async def fetch_from_cataas(self) -> str | None:
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

    async def pick_cat_url_for_channel(self, channel_id: int) -> str | None:
        last_url = self.last_url_by_channel.get(channel_id)

        for _ in range(5):
            image_url = await self.fetch_random_cat_url()
            if image_url and image_url != last_url:
                self.last_url_by_channel[channel_id] = image_url
                return image_url

        image_url = await self.fetch_random_cat_url()
        if image_url:
            self.last_url_by_channel[channel_id] = image_url
        return image_url

    async def send_to_channel(self, channel_id: int, image_url: str):
        try:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                channel = await self.bot.fetch_channel(channel_id)

            embed = discord.Embed()
            embed.set_image(url=image_url)

            await channel.send(embed=embed)
            print(f"[random_cats] sent ok to channel {channel_id}", flush=True)

        except discord.Forbidden:
            print(f"[random_cats] no permission for channel {channel_id}", flush=True)
        except discord.HTTPException as e:
            print(f"[random_cats] discord error in channel {channel_id}: {e}", flush=True)
        except Exception as e:
            print(f"[random_cats] unexpected error in channel {channel_id}: {e}", flush=True)

    async def run_channel_loop(self, config: dict):
        channel_id = config["channel_id"]
        delay_min = config["delay_min"]
        delay_max = config["delay_max"]

        print(
            f"[random_cats] run_channel_loop started | channel_id={channel_id} "
            f"| delay={delay_min}-{delay_max}s",
            flush=True
        )

        await self.bot.wait_until_ready()

        initial_delay = random.randint(1, max(2, delay_max))
        print(
            f"[random_cats] initial delay for channel {channel_id}: {initial_delay}s",
            flush=True
        )
        await asyncio.sleep(initial_delay)

        while not self.bot.is_closed():
            try:
                if not self.can_send_now():
                    await asyncio.sleep(30)
                    continue

                image_url = await self.pick_cat_url_for_channel(channel_id)
                if not image_url:
                    print(f"[random_cats] no cat url fetched for channel {channel_id}", flush=True)
                    await asyncio.sleep(30)
                    continue

                await self.send_to_channel(channel_id, image_url)

                delay = random.randint(delay_min, delay_max)
                print(
                    f"[random_cats] sleeping for {delay}s | channel_id={channel_id}",
                    flush=True
                )
                await asyncio.sleep(delay)

            except asyncio.CancelledError:
                print(f"[random_cats] channel loop cancelled | channel_id={channel_id}", flush=True)
                break
            except Exception as e:
                print(
                    f"[random_cats] ERROR in channel {channel_id}: {type(e).__name__}: {e}",
                    flush=True
                )
                await asyncio.sleep(15)


async def setup(bot: commands.Bot):
    print("[random_cats] setup called", flush=True)
    await bot.add_cog(RandomCats(bot))
