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

TARGET_CHANNEL_IDS = {
    1358888500845346866,
    1358913164493852682,
}

# pravdepodobnost, ze bot na zpravu odpovi kockou
# 0.10 = 10 %
REPLY_CHANCE = 0.10

# minimalni rozestup mezi kockami v jednom kanalu
CHANNEL_COOLDOWN_SECONDS = 20


class RandomCats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.http_session = None
        self.last_url_by_channel = {}
        self.last_sent_at_by_channel = {}
        print("[random_cats] __init__ called", flush=True)

    async def cog_load(self):
        print("[random_cats] cog_load called", flush=True)
        timeout = aiohttp.ClientTimeout(total=15)
        self.http_session = aiohttp.ClientSession(timeout=timeout)

    async def cog_unload(self):
        print("[random_cats] cog_unload called", flush=True)
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

    def is_target_channel(self, channel_id: int) -> bool:
        return channel_id in TARGET_CHANNEL_IDS

    def passes_random_chance(self) -> bool:
        return random.random() < REPLY_CHANCE

    def is_channel_on_cooldown(self, channel_id: int) -> bool:
        now_ts = asyncio.get_running_loop().time()
        last_ts = self.last_sent_at_by_channel.get(channel_id)

        if last_ts is None:
            return False

        return (now_ts - last_ts) < CHANNEL_COOLDOWN_SECONDS

    def mark_channel_sent_now(self, channel_id: int):
        self.last_sent_at_by_channel[channel_id] = asyncio.get_running_loop().time()

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

    async def send_cat_to_channel(self, channel: discord.abc.Messageable, channel_id: int, image_url: str):
        try:
            embed = discord.Embed()
            embed.set_image(url=image_url)

            await channel.send(embed=embed)
            self.mark_channel_sent_now(channel_id)
            print(f"[random_cats] sent ok to channel {channel_id}", flush=True)

        except discord.Forbidden:
            print(f"[random_cats] no permission for channel {channel_id}", flush=True)
        except discord.HTTPException as e:
            print(f"[random_cats] discord error in channel {channel_id}: {e}", flush=True)
        except Exception as e:
            print(f"[random_cats] unexpected error in channel {channel_id}: {e}", flush=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if not self.can_send_now():
            return

        if not self.is_target_channel(message.channel.id):
            return

        if self.is_channel_on_cooldown(message.channel.id):
            return

        if not self.passes_random_chance():
            return

        image_url = await self.pick_cat_url_for_channel(message.channel.id)
        if not image_url:
            print(f"[random_cats] no cat url fetched for channel {message.channel.id}", flush=True)
            return

        await self.send_cat_to_channel(message.channel, message.channel.id, image_url)


async def setup(bot: commands.Bot):
    print("[random_cats] setup called", flush=True)
    await bot.add_cog(RandomCats(bot))
