import discord
from discord.ext import commands


TRIGGER_PHRASES = {
    "mapa fektu",
    "mapa fekt",
    "mapu fektu",
    "mapu fekt",
}

RESPONSE_TEXT = "Mapu FEKTu najdeš tady --> https://vitapavlik.cz/fekt_mapa/ <:koteseni:1361038813719302175>"


class MapaFektuResponder(commands.Cog):
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
    await bot.add_cog(MapaFektuResponder(bot))
