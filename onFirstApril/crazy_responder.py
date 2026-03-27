import os

import discord
from discord.ext import commands


TRIGGER_WORD = "crazy"
RESPONSE_TEXT = "I was crazy once..."


class CrazyResponder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def is_enabled(self) -> bool:
        return os.getenv("ENABLE_CRAZY_RESPONDER", "true").lower() == "true"

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.is_enabled():
            return

        if message.author.bot:
            return

        content = message.content.lower()

        if TRIGGER_WORD in content:
            await message.reply(RESPONSE_TEXT, mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(CrazyResponder(bot))
