from discord.ext import commands
from discord import app_commands, Interaction

class Hello(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="Zprava", description="Řeknu ti něco!")
    async def hello(self, interaction: Interaction):
        await interaction.response.send_message("Toaster tvrdi, ze lzu. :(", ephemeral=False)

async def setup(bot):
    await bot.add_cog(Hello(bot))

