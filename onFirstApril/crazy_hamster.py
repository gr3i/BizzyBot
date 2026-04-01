import os
import random
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands


CHANNEL_ID = 1358913164493852682
TIMEZONE_NAME = "Europe/Prague"


MESSAGES = [
    "Měl jsem hlídat",
    "Tetě křečka.",
    "Dala mi ho se slovy,",
    "Ať u mě chvíli přečká.",
    "Ale křečka",
    "Uhlídati",
    "Nelze jen tak lehce,",
    "Obzvlášť když se vám moc nechce.",
    "Po pokoji,",
    "Ať si běhá",
    "Na gauč jsem si lehnul,",
    "Vzápětí se ani nehnul.",
    "Tlačilo mě",
    "Do zad kromě",
    "Polštářů i cosi,",
    "Už se vidím: Teto prosím:",
    "Hej teto! (teto)",
    "Já ho zabil (zabil)",
    "Už se to nestane",
    "Jo, ten už asi nevstane",
    "Hej teto! (to je)",
    "Nekřič na mě (v kelu)",
    "Já ho prostě neviděl,",
    "Už dost jsem se nastyděl",
    "Hej teto!",
    "Tak jsem kouknul",
    "Co mě tlačí",
    "Seděl jsem jenom na televizním ovladači",
    "Ale křeččí",
    "švitoření",
    "Slyšet není",
    "Jenom zvláštní smrad se line od topení.",
    "Zase se mi",
    "Dech zatajil",
    "Spečeného křečka bych před tetou neobhájil",
    "A dřív než tam",
    "Sebou seknu",
    "Měl bych asi vymyslet",
    "Jak řeknu potom tetě",
    "Hej teto! (teto)",
    "Já ho zabil (zabil)",
    "Už se to nestane",
    "Jo, ten už asi nevstane",
    "Hej teto! (to je)",
    "Nekřič na mě (v kelu)",
    "Já ho prostě neviděl,",
    "Už dost jsem se nastyděl",
    "Hej teto!",
    "Hej teto!",
    "Já ho fakt zabil",
    "Ten bídák sežral magnet",
    "A k topení se přitavil",
    "Hej teto",
    "Co na to říci?",
    "Můžeš si ho maximálně připnout na lednici",
    "Hej teto! (teto)",
    "Já ho zabil (zabil)",
    "Už se to nestane",
    "Jo, ten už asi nevstane",
    "Hej teto! (to je)",
    "Nekřič na mě (v kelu)",
    "Já ho prostě neviděl,",
    "Už dost jsem se nastyděl",
    "Hej teto!",
]


class CrazyHamster(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_index = 0
        self.loop_task = None
        print("[crazy_hamster] __init__ called", flush=True)

    async def cog_load(self):
        print("[crazy_hamster] cog_load called", flush=True)
        self.loop_task = asyncio.create_task(self.run_loop())

    async def cog_unload(self):
        print("[crazy_hamster] cog_unload called", flush=True)
        if self.loop_task:
            self.loop_task.cancel()

    def is_enabled(self) -> bool:
        value = os.getenv("ENABLE_CRAZY_LOOP", "true").lower() == "true"
        print(f"[crazy_hamster] ENABLE_CRAZY_LOOP = {value}", flush=True)
        return value

    def april_only(self) -> bool:
        value = os.getenv("CRAZY_LOOP_ONLY_ON_FIRST_APRIL", "false").lower() == "true"
        print(f"[crazy_hamster] CRAZY_LOOP_ONLY_ON_FIRST_APRIL = {value}", flush=True)
        return value

    def can_send_now(self) -> bool:
        if not self.is_enabled():
            print("[crazy_hamster] can_send_now = False (disabled)", flush=True)
            return False

        if not self.april_only():
            print("[crazy_hamster] can_send_now = True (not april only)", flush=True)
            return True

        now = datetime.now(ZoneInfo(TIMEZONE_NAME))
        result = now.month == 4 and now.day == 1
        print(f"[crazy_hamster] now = {now.isoformat()} | can_send_now = {result}", flush=True)
        return result

    async def run_loop(self):
        print("[crazy_hamster] run_loop started", flush=True)
        await self.bot.wait_until_ready()
        print(f"[crazy_hamster] bot ready as {self.bot.user} | id = {self.bot.user.id}", flush=True)

        while not self.bot.is_closed():
            try:
                if not self.can_send_now():
                    print("[crazy_hamster] sleeping 30s because cannot send now", flush=True)
                    await asyncio.sleep(30)
                    continue

                channel = self.bot.get_channel(CHANNEL_ID)
                if channel is None:
                    print(f"[crazy_hamster] channel {CHANNEL_ID} not in cache, fetching", flush=True)
                    channel = await self.bot.fetch_channel(CHANNEL_ID)

                print(f"[crazy_hamster] sending to channel = {channel} | id = {channel.id}", flush=True)
                print(f"[crazy_hamster] next index = {self.message_index}", flush=True)
                print(f"[crazy_hamster] next message = {MESSAGES[self.message_index]!r}", flush=True)

                sent_message = await channel.send(MESSAGES[self.message_index])
                print(
                    f"[crazy_hamster] sent ok | sent_message_id = {sent_message.id} "
                    f"| bot_user_id = {self.bot.user.id}",
                    flush=True
                )

                self.message_index = (self.message_index + 1) % len(MESSAGES)

                delay = random.randint(1, 4)

                print(f"[crazy_hamster] sleeping for {delay}s", flush=True)
                await asyncio.sleep(delay)

            except asyncio.CancelledError:
                print("[crazy_hamster] loop cancelled", flush=True)
                break
            except Exception as e:
                print(f"[crazy_hamster] ERROR: {type(e).__name__}: {e}", flush=True)
                await asyncio.sleep(15)


async def setup(bot: commands.Bot):
    print("[crazy_hamster] setup called", flush=True)
    await bot.add_cog(CrazyHamster(bot))
