import discord
from discord import app_commands
from discord.ext import commands


# Obory: (nazev_pro_vyber, popis, role_id)
OBORY = [
    ("BAK-EP", "Ekonomika podniku", 1466421834680504508),
    ("BAK-PM", "Procesní management", 1466421944772595765),
    ("BAK-MIn", "Manažerská informatika", 1466422113924681973),
    ("BAK-UAD", "Účetnictví a daně", 1466422421732065464),
    ("BAK-ESBD", "Entrepreneurship and Small Business Development", 1469318987560124602),
]

FP_ROLE_ID = 1466036385017233636 


# check: jen uzivatel s VUT roli
def has_fp_role():
    async def predicate(interaction: discord.Interaction):
        role = interaction.guild.get_role(VUT_ROLE_ID)
        if role and role in interaction.user.roles:
            return True
        raise app_commands.CheckFailure("Tento příkaz může použít pouze uživatel s rolí FP.")
    return app_commands.check(predicate)


async def obor_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=f"{k} – {popis}", value=k)
        for k, popis, _ in OBORY
        if current.lower() in k.lower() or current.lower() in popis.lower()
    ][:25]


class VyberOboruSimple(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    obor = app_commands.Group(
        name="obor",
        description="Výběr studijního oboru"
    )

    @has_fp_role()
    @obor.command(name="pridat", description="Přidá ti roli zvoleného oboru")
    @app_commands.guild_only()
    @app_commands.autocomplete(obor=obor_autocomplete)
    async def pridat(self, interaction: discord.Interaction, obor: str):
        match = next((o for o in OBORY if o[0] == obor), None)
        if not match:
            await interaction.response.send_message("Neplatný obor.", ephemeral=True)
            return

        _, popis, role_id = match
        role = interaction.guild.get_role(role_id)

        if not role:
            await interaction.response.send_message("Role nebyla nalezena.", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(
                f"Už máš roli **{role.name}**.", ephemeral=True
            )
            return

        await interaction.user.add_roles(role, reason="User selected study program")
        await interaction.response.send_message(
            f"Přidána role **{role.name}** ({popis})", ephemeral=True
        )

    @has_fp_role()
    @obor.command(name="odebrat", description="Odebere ti roli zvoleného oboru")
    @app_commands.guild_only()
    @app_commands.autocomplete(obor=obor_autocomplete)
    async def odebrat(self, interaction: discord.Interaction, obor: str):
        match = next((o for o in OBORY if o[0] == obor), None)
        if not match:
            await interaction.response.send_message("Neplatný obor.", ephemeral=True)
            return

        _, popis, role_id = match
        role = interaction.guild.get_role(role_id)

        if not role:
            await interaction.response.send_message("Role nebyla nalezena.", ephemeral=True)
            return

        if role not in interaction.user.roles:
            await interaction.response.send_message(
                f"Roli **{role.name}** nemáš.", ephemeral=True
            )
            return

        await interaction.user.remove_roles(role, reason="User removed study program")
        await interaction.response.send_message(
            f"Odebrána role **{role.name}** ({popis})", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(VyberOboruSimple(bot))

