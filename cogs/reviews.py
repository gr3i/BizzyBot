import discord
from discord import app_commands
from discord.ext import commands
import os

class Reviews(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    hodnoceni = app_commands.Group(
        name="hodnoceni",
        description="Test group – musi byt videt"
    )

    @hodnoceni.command(name="test", description="Vrati OK – jen test")
    async def test_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_message("OK (hodnoceni/test)", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Reviews(bot))
    # registrace groupy přímo do guildy, obcházíme .env
    GUILD_ID = 1357455204391321712  # stejná hodnota jako v bot.py
    guild = discord.Object(id=GUILD_ID)
    bot.tree.add_command(Reviews.hodnoceni, guild=guild)
    print(f"[reviews] group 'hodnoceni' registered for guild {GUILD_ID}")

