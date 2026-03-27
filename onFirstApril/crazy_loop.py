import os
import random
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands


CHANNEL_ID = 1487121536686096564
TIMEZONE_NAME = "Europe/Prague"

MESSAGES = [
    "Crazy?",
    "I was crazy once,",
    "They locked me in a room,",
    "a rubber room,",
    "a rubber room with rats,",
    "and rats make me crazy.",
]


class CrazyLoop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_index = 0
        self.bot.loop.create_task(self.run_loop())

    def is_enabled(self) -> bool:
        return os.getenv("ENABLE_CRAZY_LOOP", "true").lower() == "true"

    def april_only(self) -> bool:
        return os.getenv("CRAZY_LOOP_ONLY_ON_FIRST_APRIL", "false").lower() == "true"

    def can_send_now(self) -> bool:
        if not self.is_enabled():
            return False

        if not self.april_only():
            return True

        now = datetime.now(ZoneInfo(TIMEZONE_NAME))
        return now.month == 4 and now.day == 1

    async def run_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            try:
                if not self.can_send_now():
                    await asyncio.sleep(30)
                    continue

                channel = self.bot.get_channel(CHANNEL_ID)
                if channel is None:
                    try:
                        channel = await self.bot.fetch_channel(CHANNEL_ID)
                    except Exception as e:
                        print(f"[crazy_loop] Could not fetch channel: {e}")
                        await asyncio.sleep(30)
                        continue

                await channel.send(MESSAGES[self.message_index])
                print(f"[crazy_loop] Sent message index {self.message_index}")

                self.message_index = (self.message_index + 1) % len(MESSAGES)

                if random.random() < 0.15:
                    delay = random.randint(45, 90)
                else:
                    delay = random.randint(5, 10)

                await asyncio.sleep(delay)

            except Exception as e:
                print(f"[crazy_loop] Error while sending message: {e}")
                await asyncio.sleep(15)


async def setup(bot: commands.Bot):
    await bot.add_cog(CrazyLoop(bot))
