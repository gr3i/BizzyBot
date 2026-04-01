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
    "--- POZOR: Zjištěno vniknutí do systému! ---",
    "Studenti z FIT VUT se nabourali na server...",
    "Instaluji virus: MARUSKA_V_SITI.exe",
    "Kdo tam?!",
    "KDO TAM?!",
    "FITáci jdou!",
    "FITÁCI JDOU!",
    "Jsme čas",
    "ZRAJE KLAS",
    "zraje klas",
    "PAK je MrÁz",
    "pak je mráz",
    "Kam jdeš?",
    "Co chceš?",
    "OSoBO",
    "osobo mnau",
    "--- CHYBA: Pohádka byla hacknuta! ---",
    "Jsme kód",
    "JSME KÓD",
    "zraje šrot",
    "ZRAJE ŠROT",
    "teče pot",
    "TEČE POT",
    "dpč, to kdo vymyslel tuhle kktinu...",
    "jsme čas",
    "zhasni jas",
    "dej nám pas!",
    "Uživateli, uploaduj data!",
    "Maruška.exe: Administrátoři zlatí, systém se mi krátí...",
    "Leden_Mainframe: Tvůj firewall je děravý jak síto, sestro.",
    "Červen_Vlákno: Vzhledem k její nízké latenci, dopřejme jí letní frekvence!",
    "--- KRITICKÁ CHYBA: Léto v cloudu, cvrček dostal ránu z proudu ---",
    "Spojení přerušeno...",
    "SPOJENÍ PŘERUŠENO!",
    "Uživatel Maruška je opět online...",
    "UŽIVATEL MARUŠKA JE OPĚT ONLINE...",
    "Co pak máš",
    "Co PaK mÁŠ",
    "Za ÚKol?",
    "za úkol",
    "Srdce chladná",
    "SRDCE CHLADNÁ",
    "RAMka žádná!",
    "RAMKA ŽÁDNÁ!",
    "Bratře Ledne",
    "ať se zvedne",
    "MODRÁ SMRT!",
    "M O D R Á S M R T !",
    "SYSTÉM SE ZHROUTIL!",
    "Jsme rok",
    "jsme kód",
    "ani krok",
    "ANI KROK!",
    "Smyčka se uzavírá",
    "SMYČKA SE UZAVÍRÁ",
    "Čas se restartuje...",
    "znovu a zas...",
    "ZNOVU A ZAS...",
    "--- RESTARTUJI POHÁDKU ---",
]


class CrazyLoop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_index = 0
        self.loop_task = None
        print("[crazy_moons] __init__ called")

    async def cog_load(self):
        print("[crazy_moons] cog_load called")
        self.loop_task = asyncio.create_task(self.run_loop())

    async def cog_unload(self):
        print("[crazy_moons] cog_unload called")
        if self.loop_task:
            self.loop_task.cancel()

    def is_enabled(self) -> bool:
        value = os.getenv("ENABLE_CRAZY_LOOP", "true").lower() == "true"
        print(f"[crazy_moons] ENABLE_CRAZY_LOOP = {value}")
        return value

    def april_only(self) -> bool:
        value = os.getenv("CRAZY_LOOP_ONLY_ON_FIRST_APRIL", "false").lower() == "true"
        print(f"[crazy_moons] CRAZY_LOOP_ONLY_ON_FIRST_APRIL = {value}")
        return value

    def can_send_now(self) -> bool:
        if not self.is_enabled():
            print("[crazy_moons] can_send_now = False (disabled)")
            return False

        if not self.april_only():
            print("[crazy_moons] can_send_now = True (not april only)")
            return True

        now = datetime.now(ZoneInfo(TIMEZONE_NAME))
        result = now.month == 4 and now.day == 1
        print(f"[crazy_moons] now = {now.isoformat()} | can_send_now = {result}")
        return result

    async def run_loop(self):
        print("[crazy_moons] run_loop started")
        await self.bot.wait_until_ready()
        print(f"[crazy_moons] bot ready as {self.bot.user} | id = {self.bot.user.id}")

        while not self.bot.is_closed():
            try:
                if not self.can_send_now():
                    print("[crazy_moons] sleeping 30s because cannot send now")
                    await asyncio.sleep(30)
                    continue

                channel = self.bot.get_channel(CHANNEL_ID)
                if channel is None:
                    print(f"[crazy_moons] channel {CHANNEL_ID} not in cache, fetching")
                    channel = await self.bot.fetch_channel(CHANNEL_ID)

                print(f"[crazy_moons] sending to channel = {channel} | id = {channel.id}")
                print(f"[crazy_moons] next index = {self.message_index}")
                print(f"[crazy_moons] next message = {MESSAGES[self.message_index]!r}")

                sent_message = await channel.send(MESSAGES[self.message_index])
                print(
                    f"[crazy_moons] sent ok | sent_message_id = {sent_message.id} "
                    f"| bot_user_id = {self.bot.user.id}"
                )

                self.message_index = (self.message_index + 1) % len(MESSAGES)

                if random.random() < 0.15:
                    delay = random.randint(45, 90)
                else:
                    delay = random.randint(5, 10)

                print(f"[crazy_moons] sleeping for {delay}s")
                await asyncio.sleep(delay)

            except asyncio.CancelledError:
                print("[crazy_moons] loop cancelled")
                break
            except Exception as e:
                print(f"[crazy_moons] ERROR: {type(e).__name__}: {e}")
                await asyncio.sleep(15)


async def setup(bot: commands.Bot):
    print("[crazy_moons] setup called")
    await bot.add_cog(CrazyLoop(bot))
