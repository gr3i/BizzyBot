import discord
from discord import app_commands
from discord.ext import commands


ALLOWED_USER_ID = 685958402442133515


class VutApiTest(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="vut_api_test",
        description="Otestuje jeden VUT API request.",
    )
    @app_commands.describe(
        ident="VUT ID nebo login, napr. 268500 nebo xlogin00",
    )
    async def vut_api_test(
        self,
        interaction: discord.Interaction,
        ident: str,
    ):
        if interaction.user.id != ALLOWED_USER_ID:
            await interaction.response.send_message(
                "Tento prikaz nemuzes pouzit.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        ident = ident.strip().lower()

        try:
            details = await self.bot.vut_api.get_user_details(ident)

        except Exception as error:
            await interaction.followup.send(
                "**VUT API TEST - CHYBA**\n\n"
                f"VUT ident: `{ident}`\n"
                f"Typ chyby: `{type(error).__name__}`\n"
                f"Chyba: `{error}`\n\n"
                "Podivej se ted do logu bota na radky tesne pred touto chybou.",
                ephemeral=True,
            )
            return

        if details is None:
            await interaction.followup.send(
                "**VUT API TEST**\n\n"
                f"VUT ident: `{ident}`\n"
                "API vratilo, ze uzivatel nebyl nalezen.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            "**VUT API TEST - OK**\n\n"
            f"VUT ident: `{ident}`\n"
            "VUT API uspesne vratilo data.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(VutApiTest(bot))