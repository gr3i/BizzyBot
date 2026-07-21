import random

import discord
from discord import app_commands
from discord.ext import commands


MAX_NAME_LENGTH = 100
_random = random.SystemRandom()


class Ruleta(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="ruleta",
        description="Náhodně vybere jednu ze 2 až 10 zadaných možností.",
    )
    @app_commands.describe(
        nazev_1="První možnost",
        nazev_2="Druhá možnost",
        nazev_3="Třetí možnost (nepovinné)",
        nazev_4="Čtvrtá možnost (nepovinné)",
        nazev_5="Pátá možnost (nepovinné)",
        nazev_6="Šestá možnost (nepovinné)",
        nazev_7="Sedmá možnost (nepovinné)",
        nazev_8="Osmá možnost (nepovinné)",
        nazev_9="Devátá možnost (nepovinné)",
        nazev_10="Desátá možnost (nepovinné)",
    )
    async def ruleta(
        self,
        interaction: discord.Interaction,
        nazev_1: str,
        nazev_2: str | None = None,
        nazev_3: str | None = None,
        nazev_4: str | None = None,
        nazev_5: str | None = None,
        nazev_6: str | None = None,
        nazev_7: str | None = None,
        nazev_8: str | None = None,
        nazev_9: str | None = None,
        nazev_10: str | None = None,
    ):
        zadane_nazvy = [
            nazev_1,
            nazev_2,
            nazev_3,
            nazev_4,
            nazev_5,
            nazev_6,
            nazev_7,
            nazev_8,
            nazev_9,
            nazev_10,
        ]

        # Odstraní nevyplnene moznosti a mezery na zacatku ci konci.
        nazvy = [
            nazev.strip()
            for nazev in zadane_nazvy
            if nazev and nazev.strip()
        ]

        if len(nazvy) < 2:
            await interaction.response.send_message(
                "Pro ruletu musíš zadat alespoň dvě neprázdné možnosti.",
                ephemeral=True,
            )
            return

        prilis_dlouhe_nazvy = [
            nazev
            for nazev in nazvy
            if len(nazev) > MAX_NAME_LENGTH
        ]

        if prilis_dlouhe_nazvy:
            await interaction.response.send_message(
                f"Každý název může mít maximálně {MAX_NAME_LENGTH} znaků.",
                ephemeral=True,
            )
            return

        index_viteze = _random.randrange(len(nazvy))

        zobrazene_moznosti = []

        for index, nazev in enumerate(nazvy):
            bezpecny_nazev = discord.utils.escape_markdown(nazev)

            if index == index_viteze:
                zobrazene_moznosti.append(
                    f"**➡️ {index + 1}. {bezpecny_nazev}**"
                )
            else:
                zobrazene_moznosti.append(
                    f"{index + 1}. {bezpecny_nazev}"
                )

        vitez = discord.utils.escape_markdown(nazvy[index_viteze])
        seznam_moznosti = "\n".join(zobrazene_moznosti)

        embed = discord.Embed(
            title="Ruleta",
            description=(
                f"Vybráno: **{vitez}**\n\n"
                f"**Zadané možnosti**\n"
                f"{seznam_moznosti}"
            ),
            color=discord.Color.gold(),
        )

        embed.set_footer(
            text=f"Roztočil/a: {interaction.user.display_name}"
        )

        await interaction.response.send_message(
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Ruleta(bot))
