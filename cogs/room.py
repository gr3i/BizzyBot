from discord.ext import commands
from discord import app_commands, Interaction

BASE_URL = "https://gr3i.github.io/room"

# seznam mistnosti, ktere mam na mape (STEJNE nazvy jako v ROOMS v room.html)
VALID_ROOMS = {
    "p381",
    "p384",
    "e337",
    "e339",
    "e341",
    "e342",

    "p283",
    "p284",
    "p285",
    "p286",
    "p287",
    "p288",
    "p292",
    "p289",
    "p254",
    "p257",
    "p259",
    "p262",
    "p256",
    "p255",

    "e110",
    "e109",
    "e131",
    "e135",
    "p165",
    "p164",
    "p163",
    "p160",
    "p159",
    "p158",
    "p157",
}


class Room(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="room",
        description="Ukáže místnost na mapě."
    )
    @app_commands.describe(
        code="Zadej zkratku místnosti, např. P384 nebo P287"
    )
    async def room(self, interaction: Interaction, code: str):

        # prevedu vstup na mala pismena
        room_code = code.strip().lower()

        # kontrola, jestli mistnost existuje v seznamu
        if room_code not in VALID_ROOMS:
            await interaction.response.send_message(
                f"Místnost **{room_code.upper()}** nemám v seznamu. "
                f"Zkontroluj prosím, jestli jsi ji napsal správně.",
                ephemeral=True
            )
            return

        # slozim URL ve tvaru: https://.../?room=e112
        url = f"{BASE_URL}?room={room_code}"

        # poslat odkaz uzivateli
        await interaction.response.send_message(
            f"Otevírám mapu pro místnost **{room_code.upper()}**:\n{url}",
            ephemeral=False
        )


async def setup(bot):
    await bot.add_cog(Room(bot))

