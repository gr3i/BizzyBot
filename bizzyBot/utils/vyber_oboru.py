import discord
from discord import app_commands
from discord.ext import commands

# Předměty pro obor Ekonomika podniku - 1. ročník
ekonomika_podniku_1_rocnik = [
    ("HA1PZ", 1383522776664637544),
    ("HA2PL", 1383522880347832432),
    ("HA2PZ", 1383522782343598082),
    ("HA3PL", 1383522885339054150),
    ("IG", 1383522832356475024),
    ("KeseP", 1383522822713905366),
    ("KinfP", 1383522839239327874),
    ("epP", 1383522736986656950),
    ("ma1P", 1383522770130047036),
    ("ma2P", 1383522843593015379),
    ("mak1P", 1383522746167857202),
    ("manP", 1383522758658490551),
    ("mik1P", 1383522850505494710),
    ("mkP", 1383522765092425788),
    ("pmlP", 1383522890456240150),
    ("pmrlP", 1383522896760016928),
    ("pmrzP", 1383522816938348655),
    ("pmzP", 1383522811058061373),
    ("pzmP", 1383522787821355200),
    ("uceP", 1383522873120919718),
]

# 🔹 Zde můžeš přidat další obory
obory_list = [
    ("Ekonomika podniku - 1. ročník", ekonomika_podniku_1_rocnik),
    # ("Informatika - 1. ročník", informatika_1_rocnik), apod.
]

async def obor_autocomplete(interaction: discord.Interaction, current: str):
    matches = [name for name, _ in obory_list if current.lower() in name.lower()]
    return [app_commands.Choice(name=name, value=name) for name in matches[:25]]

class Obor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="obor", description="Vyber si obor a ročník a automaticky získáš role předmětů.")
    @app_commands.describe(obor="Název oboru a ročníku")
    @app_commands.autocomplete(obor=obor_autocomplete)
    async def obor(self, interaction: discord.Interaction, obor: str):
        predmety = next((predmety for name, predmety in obory_list if name == obor), None)
        if predmety is None:
            await interaction.response.send_message("❌ Obor nebyl nalezen.", ephemeral=True)
            return
        
        # Přidání všech rolí k uživateli
        pridane_role = []
        for _, role_id in predmety:
            role = interaction.guild.get_role(role_id)
            if role and role not in interaction.user.roles:
                await interaction.user.add_roles(role)
                pridane_role.append(role.name)

        if pridane_role:
            await interaction.response.send_message(
                f"✅ Byly ti přidány role předmětů pro obor **{obor}**: {', '.join(pridane_role)}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"ℹ️ Všechny role pro obor **{obor}** už máš přiřazené.",
                ephemeral=True
            )

    @obor.error
    async def obor_error(self, interaction: discord.Interaction, error):
        await interaction.response.send_message(
            f"❌ Došlo k chybě: {str(error)}", ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Obor(bot))

