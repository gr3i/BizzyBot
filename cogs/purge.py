import discord
from discord import app_commands
from discord.ext import commands


ALLOWED_USER_IDS = {
    685958402442133515,
}


class Purge(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def is_allowed(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id in ALLOWED_USER_IDS

    @app_commands.command(
        name="purge",
        description="Smaže označenou zprávu a všechny zprávy pod ní v aktuálním kanálu."
    )
    @app_commands.describe(
        message="Zpráva, od které se má mazat"
    )
    async def purge(
        self,
        interaction: discord.Interaction,
        message: discord.Message
    ):
        if not self.is_allowed(interaction):
            await interaction.response.send_message(
                "Na tento příkaz nemáš oprávnění.",
                ephemeral=True
            )
            return

        if interaction.channel is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "Tento příkaz lze použít jen v textovém kanálu.",
                ephemeral=True
            )
            return

        if message.channel.id != interaction.channel.id:
            await interaction.response.send_message(
                "Musíš vybrat zprávu ze stejného kanálu, kde příkaz používáš.",
                ephemeral=True
            )
            return

        me = interaction.guild.me if interaction.guild else None
        if me is None:
            await interaction.response.send_message(
                "Nepodařilo se zjistit bota na serveru.",
                ephemeral=True
            )
            return

        perms = interaction.channel.permissions_for(me)
        if not perms.manage_messages:
            await interaction.response.send_message(
                "Bot nemá oprávnění Spravovat zprávy.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        to_delete = [message]

        try:
            async for msg in interaction.channel.history(limit=None, after=message):
                to_delete.append(msg)

            if not to_delete:
                await interaction.followup.send(
                    "Nenašly se žádné zprávy ke smazání.",
                    ephemeral=True
                )
                return

            deleted_count = 0
            recent_messages = []
            old_messages = []

            for msg in to_delete:
                age = discord.utils.utcnow() - msg.created_at
                if age.days < 14:
                    recent_messages.append(msg)
                else:
                    old_messages.append(msg)

            if recent_messages:
                deleted = await interaction.channel.delete_messages(recent_messages)
                deleted_count += len(deleted)

            for msg in old_messages:
                try:
                    await msg.delete()
                    deleted_count += 1
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass

            await interaction.followup.send(
                f"Smazáno {deleted_count} zpráv od označené zprávy dolů.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "Bot nemá dostatečná oprávnění pro mazání zpráv.",
                ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"Nastala chyba Discordu: {e}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"Nastala neočekávaná chyba: {e}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Purge(bot))
