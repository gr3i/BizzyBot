import os
import asyncio

import discord
from discord.ext import commands


ALLOWED_WORDS = ("mňau", "mnau", "meow")

# prazdny set == hlida vsude
# dam ID kanalu, bude hlidat jen tam
TARGET_CHANNEL_IDS = {1487121536686096564}

WARNING_DELETE_AFTER = 8


class MeowGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def is_enabled(self) -> bool:
        return os.getenv("ENABLE_MEOW_GUARD", "true").lower() == "true"

    def is_target_channel(self, channel_id: int) -> bool:
        return not TARGET_CHANNEL_IDS or channel_id in TARGET_CHANNEL_IDS

    def contains_allowed_word(self, content: str) -> bool:
        lowered = content.casefold()
        return any(word in lowered for word in ALLOWED_WORDS)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            await self.bot.process_commands(message)
            return

        if not self.is_enabled():
            await self.bot.process_commands(message)
            return

        if not self.is_target_channel(message.channel.id):
            await self.bot.process_commands(message)
            return

        if not message.content or not message.content.strip():
            await self.bot.process_commands(message)
            return

        if self.contains_allowed_word(message.content):
            await self.bot.process_commands(message)
            return

        try:
            await message.delete()

            warning = await message.channel.send(
                f"{message.author.mention}, musis do zpravy dopsat `mňau`, `mnau` nebo `meow`."
            )

            await asyncio.sleep(WARNING_DELETE_AFTER)
            try:
                await warning.delete()
            except discord.HTTPException:
                pass

        except discord.Forbidden:
            print("[meow_guard] Chybi prava na mazani nebo posilani zprav.")
        except discord.HTTPException as e:
            print(f"[meow_guard] Discord chyba: {e}")
        except Exception as e:
            print(f"[meow_guard] Neocekavana chyba: {e}")

        await self.bot.process_commands(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(MeowGuard(bot))
