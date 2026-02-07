import discord
from discord import app_commands
from discord.ext import commands

# kdo si muze roli nastavovat
ALLOWED_ROLE_IDS = {1358911329737642014, 1466036385017233636}

# role, kterou budeme pridavat/odebirat
SPOLKU_ROLE_ID = 1437796762260607067


def has_allowed_role():
    async def predicate(interaction: discord.Interaction):
        member = interaction.user
        if not isinstance(member, discord.Member):
            raise app_commands.CheckFailure
        if any(r.id in ALLOWED_ROLE_IDS for r in member.roles):
            return True
        raise app_commands.CheckFailure
    return app_commands.check(predicate)


class RoleSpolku(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    role_spolku = app_commands.Group(
        name="role_spolku",
        description="Přidání/odebrání role spolku"
    )

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            msg = "Na tento příkaz musíš mít roli **VUT** nebo **FP**."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return
        raise error

    @has_allowed_role()
    @role_spolku.command(name="pridat", description="Přidá ti roli spolku")
    @app_commands.guild_only()
    async def pridat(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(SPOLKU_ROLE_ID)
        if not role:
            await interaction.response.send_message("Roli se nepodařilo najít.", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(f"Už máš roli **{role.name}**.", ephemeral=True)
            return

        await interaction.user.add_roles(role, reason="/role_spolku pridat")
        await interaction.response.send_message(f"Přidána role **{role.name}**.", ephemeral=True)

    @has_allowed_role()
    @role_spolku.command(name="odebrat", description="Odebere ti roli spolku")
    @app_commands.guild_only()
    async def odebrat(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(SPOLKU_ROLE_ID)
        if not role:
            await interaction.response.send_message("Roli se nepodařilo najít.", ephemeral=True)
            return

        if role not in interaction.user.roles:
            await interaction.response.send_message(f"Roli **{role.name}** nemáš.", ephemeral=True)
            return

        await interaction.user.remove_roles(role, reason="/role_spolku odebrat")
        await interaction.response.send_message(f"Odebrána role **{role.name}**.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(RoleSpolku(bot))
