from discord.ext import commands
from discord import app_commands, Interaction

class BotInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Slash příkaz
    @app_commands.command(name="botinfo", description="Odkaz na repozitář bota.")
    async def bot_info(self, interaction: Interaction):
        await interaction.response.send_message("https://github.com/gr3i/BizzyBot", ephemeral=False)

    # Automatická registrace slash příkazu po načtení cogu
    async def cog_load(self):
        self.bot.tree.add_command(self.bot_info)

# Setup funkce pro dynamické načítání cogu
async def setup(bot):
    await bot.add_cog(BotInfo(bot))
