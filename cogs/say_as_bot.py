import discord
from discord import app_commands
from discord.ext import commands


ALLOWED_ROLE_IDS = {
    1358898283782602932,
    # sem muzes pridat dalsi role ID
}

ALLOWED_USER_IDS = {
    685958402442133515,
    # sem muzes pridat dalsi user ID
}


class SayAsBot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def is_allowed(self, interaction: discord.Interaction) -> bool:
        user = interaction.user

        if user.id in ALLOWED_USER_IDS:
            return True

        if isinstance(user, discord.Member):
            user_role_ids = {role.id for role in user.roles}
            if user_role_ids & ALLOWED_ROLE_IDS:
                return True

        return False

    @app_commands.command(name="say", description="Posle zpravu jako bot.")
    @app_commands.describe(
        text="Text, ktery ma bot poslat",
        channel="Kanal, kam se ma zprava poslat"
    )
    async def say(
        self,
        interaction: discord.Interaction,
        text: str,
        channel: discord.TextChannel | None = None
    ):
        if not self.is_allowed(interaction):
            await interaction.response.send_message(
                "Na tenhle command nemas opravneni.",
                ephemeral=True
            )
            return

        target_channel = channel or interaction.channel

        if target_channel is None:
            await interaction.response.send_message(
                "Nepodarilo se najit cilovy kanal.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            await target_channel.send(text)
            await interaction.followup.send(
                f"Zprava odeslana do {target_channel.mention}.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "Bot nema opravneni psat do tohohle kanalu.",
                ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"Nastala Discord chyba: {e}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"Nastala neocekavana chyba: {e}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(SayAsBot(bot))
