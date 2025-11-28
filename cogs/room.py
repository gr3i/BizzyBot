from discord.ext import commands
from discord import app_commands, Interaction

BASE_URL = "https://gr3i.github.io/room"

class Room(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="room",
        description="Ukáže místnost na mapě."
    )

    @app_commands.describe(
        code="Zadej zkratku místnosti, např. P384 nebo E337"
    )

    async def room(self, interaction: Interaction, code: str):

        # vsechno na mala pismena
        room_code = code.strip().lower()

        # slozim URL ve tvaru: https://.../?room=e112
        url = f"{BASE_URL}?room={room_code}"

        # odpoved (ephemeral=True = vidi jen ten, kdo zadal prikaz)
        await interaction.response.send_message(
            f"Otevírám mapu pro místnost **{room_code.upper()}**:\n{url}",
            ephemeral=False
        )

async def setup(bot):
    await bot.add_cog(Room(bot))

