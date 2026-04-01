import os
import random
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands


CHANNEL_IDS = [
    1358888500845346866,
    1358913164493852682,
]

TIMEZONE_NAME = "Europe/Prague"

LINKS = [
    "https://www.youtube.com/watch?v=cd5QuZq5jmg",
    "https://www.youtube.com/watch?v=k85mRPqvMbE&list=RDk85mRPqvMbE&start_radio=1",
    "https://www.youtube.com/watch?v=WqmGFfNco0g",
    "https://www.youtube.com/watch?v=v6jw6KRIOmw&list=RDv6jw6KRIOmw&start_radio=1",
    "https://www.youtube.com/watch?v=mEJ_jxFJU_0",
    "https://www.youtube.com/watch?v=UeQlXoyy8K8&list=RDUeQlXoyy8K8&start_radio=1",
]


class RandomLinks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.loop_task = None
        self.last_link = None
        print("[random_links] __init__ called", flush=True)

    async def cog_load(self):
        print("[random_links] cog_load called", flush=True)
        self.loop_task = asyncio.create_task(self.run_loop())

    async def cog_unload(self):
        print("[random_links] cog_unload called", flush=True)
        if self.loop_task:
            self.loop_task.cancel()

    def is_enabled(self) -> bool:
        value = os.getenv("ENABLE_RANDOM_LINKS", "true").lower() == "true"
        print(f"[random_links] ENABLE_RANDOM_LINKS = {value}", flush=True)
        return value

    def april_only(self) -> bool:
        value = os.getenv("RANDOM_LINKS_ONLY_ON_FIRST_APRIL", "false").lower() == "true"
        print(f"[random_links] RANDOM_LINKS_ONLY_ON_FIRST_APRIL = {value}", flush=True)
        return value

    def can_send_now(self) -> bool:
        if not self.is_enabled():
            print("[random_links] can_send_now = False (disabled)", flush=True)
            return False

        if not self.april_only():
            return True

        now = datetime.now(ZoneInfo(TIMEZONE_NAME))
        result = now.month == 4 and now.day == 1
        print(f"[random_links] now = {now.isoformat()} | can_send_now = {result}", flush=True)
        return result

    def pick_link(self) -> str | None:
        if not LINKS:
            return None

        available_links = [link for link in LINKS if link != self.last_link]
        if not available_links:
            available_links = LINKS[:]

        link = random.choice(available_links)
        self.last_link = link
        return link

    async def send_to_channel(self, channel_id: int, message_text: str):
        try:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                channel = await self.bot.fetch_channel(channel_id)

            sent_message = await channel.send(message_text)
            print(
                f"[random_links] sent ok | channel_id = {channel_id} | message_id = {sent_message.id}",
                flush=True
            )

        except discord.Forbidden:
            print(f"[random_links] ERROR: no permission for channel {channel_id}", flush=True)
        except discord.HTTPException as e:
            print(f"[random_links] ERROR: discord error in channel {channel_id}: {e}", flush=True)
        except Exception as e:
            print(f"[random_links] ERROR: unexpected error in channel {channel_id}: {e}", flush=True)

    async def run_loop(self):
        print("[random_links] run_loop started", flush=True)
        await self.bot.wait_until_ready()
        print(f"[random_links] bot ready as {self.bot.user} | id = {self.bot.user.id}", flush=True)

        while not self.bot.is_closed():
            try:
                if not self.can_send_now():
                    await asyncio.sleep(30)
                    continue

                link = self.pick_link()
                if link is None:
                    print("[random_links] LINKS is empty", flush=True)
                    await asyncio.sleep(30)
                    continue

                message_text = f"Check this out: {link}"
                print(f"[random_links] chosen link = {link}", flush=True)

                for channel_id in CHANNEL_IDS:
                    await self.send_to_channel(channel_id, message_text)

                delay = random.randint(15, 45)
                print(f"[random_links] sleeping for {delay}s", flush=True)
                await asyncio.sleep(delay)

            except asyncio.CancelledError:
                print("[random_links] loop cancelled", flush=True)
                break
            except Exception as e:
                print(f"[random_links] ERROR: {type(e).__name__}: {e}", flush=True)
                await asyncio.sleep(15)


async def setup(bot: commands.Bot):
    print("[random_links] setup called", flush=True)
    await bot.add_cog(RandomLinks(bot))
