import discord
from discord import app_commands
from discord.ext import commands


# kdo si muze role nastavovat
ALLOWED_ROLE_IDS = {1358911329737642014, 1466036385017233636}

# role: (hodnota_pro_vyber, nazev_pro_uzivatele, role_id)
ROLE_OPTIONS = [
    ("spolku", "Spolku", 1437796762260607067),
    ("cesa_sport", "ČESA / Sport", 1514716246610940116),
]


def has_allowed_role():
    async def predicate(interaction: discord.Interaction):
        member = interaction.user

        if not isinstance(member, discord.Member):
            raise app_commands.CheckFailure

        if any(role.id in ALLOWED_ROLE_IDS for role in member.roles):
            return True

        raise app_commands.CheckFailure

    return app_commands.check(predicate)


async def role_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=display_name, value=role_key)
        for role_key, display_name, _ in ROLE_OPTIONS
        if current.lower() in role_key.lower() or current.lower() in display_name.lower()
    ][:25]


class VyberRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    role = app_commands.Group(
        name="role",
        description="Přidání/odebrání volitelných rolí"
    )

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.CheckFailure):
            message = "Na tento příkaz musíš mít roli **VUT** nebo **FP**."

            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)

            return

        raise error

    def get_role_option(self, role_key: str):
        return next((role_option for role_option in ROLE_OPTIONS if role_option[0] == role_key), None)

    @has_allowed_role()
    @role.command(name="pridat", description="Přidá ti zvolenou roli")
    @app_commands.guild_only()
    @app_commands.autocomplete(role=role_autocomplete)
    async def pridat(self, interaction: discord.Interaction, role: str):
        role_option = self.get_role_option(role)

        if not role_option:
            await interaction.response.send_message("Neplatná role.", ephemeral=True)
            return

        _, display_name, role_id = role_option

        if interaction.guild is None:
            await interaction.response.send_message("Tento příkaz lze použít jen na serveru.", ephemeral=True)
            return

        member = interaction.user

        if not isinstance(member, discord.Member):
            await interaction.response.send_message("Nepodařilo se načíst člena serveru.", ephemeral=True)
            return

        discord_role = interaction.guild.get_role(role_id)

        if not discord_role:
            await interaction.response.send_message("Role nebyla nalezena.", ephemeral=True)
            return

        if discord_role in member.roles:
            await interaction.response.send_message(
                f"Už máš roli **{discord_role.name}**.",
                ephemeral=True
            )
            return

        try:
            await member.add_roles(discord_role, reason=f"/role pridat {display_name}")
        except discord.Forbidden:
            await interaction.response.send_message(
                "Nemám oprávnění tuto roli přidat. Zkontroluj pořadí rolí bota.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Přidána role **{discord_role.name}**.",
            ephemeral=True
        )

    @has_allowed_role()
    @role.command(name="odebrat", description="Odebere ti zvolenou roli")
    @app_commands.guild_only()
    @app_commands.autocomplete(role=role_autocomplete)
    async def odebrat(self, interaction: discord.Interaction, role: str):
        role_option = self.get_role_option(role)

        if not role_option:
            await interaction.response.send_message("Neplatná role.", ephemeral=True)
            return

        _, display_name, role_id = role_option

        if interaction.guild is None:
            await interaction.response.send_message("Tento příkaz lze použít jen na serveru.", ephemeral=True)
            return

        member = interaction.user

        if not isinstance(member, discord.Member):
            await interaction.response.send_message("Nepodařilo se načíst člena serveru.", ephemeral=True)
            return

        discord_role = interaction.guild.get_role(role_id)

        if not discord_role:
            await interaction.response.send_message("Role nebyla nalezena.", ephemeral=True)
            return

        if discord_role not in member.roles:
            await interaction.response.send_message(
                f"Roli **{discord_role.name}** nemáš.",
                ephemeral=True
            )
            return

        try:
            await member.remove_roles(discord_role, reason=f"/role odebrat {display_name}")
        except discord.Forbidden:
            await interaction.response.send_message(
                "Nemám oprávnění tuto roli odebrat. Zkontroluj pořadí rolí bota.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Odebrána role **{discord_role.name}**.",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(VyberRole(bot))
