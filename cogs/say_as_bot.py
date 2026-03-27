import discord
from discord import app_commands
from discord.ext import commands


ALLOWED_ROLE_IDS = {
    1358898283782602932,
}

ALLOWED_USER_IDS = {
    685958402442133515, 
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

    @app_commands.command(name="say", description="Pošle zprávu jako bot.")
    @app_commands.describe(
        text="Text, který má bot poslat",
        channel="Kanál, kam se má zpráva poslat"
    )
    async def say(
        self,
        interaction: discord.Interaction,
        text: str,
        channel: discord.TextChannel | None = None
    ):
        if not self.is_allowed(interaction):
            await interaction.response.send_message(
                "Na tenhle command nemáš oprávnění.",
                ephemeral=True
            )
            return

        target_channel = channel or interaction.channel

        if target_channel is None:
            await interaction.response.send_message(
                "Nepodařilo se najít cílový kanál.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            await target_channel.send(text)
            await interaction.followup.send(
                f"Zpráva odeslána do {target_channel.mention}.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "Bot nemá oprávnění psát do tohohle kanálu.",
                ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"Nastala Discord chyba: {e}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"Nastala neočekávaná chyba: {e}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(SayAsBot(bot))
