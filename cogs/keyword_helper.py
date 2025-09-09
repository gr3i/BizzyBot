# cogs/keyword_helper.py
import time
import discord
from discord.ext import commands

TARGET_CHANNEL_ID = 1358876461825523863
KEYWORDS = {"problém", "problem", "pomoc", "nejde", "nefunguje"}
COOLDOWN_SECONDS = 5
DEBUG = True

class KeywordHelper(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_trigger_ts: float = 0.0

    async def cog_load(self):
        # jednorázová zpráva po načtení, ať víš, že cog běží
        channel = self.bot.get_channel(TARGET_CHANNEL_ID)
        if channel:
            try:
                await channel.send("KeywordHelper je aktivní (test).")
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            # ignoruj bota a DMs
            if message.author.bot or not message.guild:
                return

            # jen cílový kanál nebo jeho parent (threads/forum)
            parent_id = getattr(message.channel, "parent_id", None)
            if message.channel.id != TARGET_CHANNEL_ID and parent_id != TARGET_CHANNEL_ID:
                if DEBUG: print("[KW] skip: jiný kanál", message.channel.id, "parent:", parent_id, flush=True)
                return

            # cooldown
            now = time.time()
            if now - self._last_trigger_ts < COOLDOWN_SECONDS:
                if DEBUG: print("[KW] skip: cooldown", flush=True)
                return

            # klíčová slova (case-insensitive)
            text = (message.content or "").lower()
            if any(k.lower() in text for k in KEYWORDS):
                await message.channel.send("Napiš lomítko `/` a vyjede ti příkaz.")
                self._last_trigger_ts = now
                if DEBUG: print("[KW] trigger OK:", text, flush=True)
            else:
                if DEBUG: print("[KW] no match:", text[:80], flush=True)

        except discord.Forbidden:
            if DEBUG: print("[KW] nemám práva posílat zprávy v kanálu.", flush=True)
        except Exception as e:
            if DEBUG: print("[KW] error:", e, flush=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(KeywordHelper(bot))

