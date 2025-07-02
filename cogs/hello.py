from discord.ext import commands
from discord import app_commands, Interaction

class Hello(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="hello", description="Řeknu ti Ahoj!")
    async def hello(self, interaction: Interaction):
        await interaction.response.send_message("Ahoj!", ephemeral=False)

async def setup(bot):
    await bot.add_cog(Hello(bot))


