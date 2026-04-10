import discord
from discord.ext import commands


TRIGGER_PHRASES = {
    "příručce prváka",
    "prirucce prvaka",
    "příručce pro prváka",
    "prirucce pro prvaka",
    "příručka prváka",
    "prirucka prvaka",
    "příručka pro prváka",
    "prirucka pro prvaka",
}

RESPONSE_TEXT = "https://prirucka.vut.cz/category/fp/ <:KannaSip:1359694460807811344>"


class PriruckaResponder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        content = message.content.lower()

        if any(phrase in content for phrase in TRIGGER_PHRASES):
            await message.reply(RESPONSE_TEXT, mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(PriruckaResponder(bot))
