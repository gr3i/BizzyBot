import discord
from discord import app_commands
from discord.ext import commands


ALLOWED_USER_IDS = {
    685958402442133515,  
}

ALLOWED_ROLE_IDS = {
   
}


class Purge(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.purge_context_menu = app_commands.ContextMenu(
            name="Purge od této zprávy",
            callback=self.purge_from_message,
        )

    async def cog_load(self):
        self.bot.tree.add_command(self.purge_context_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(
            self.purge_context_menu.name,
            type=self.purge_context_menu.type
        )

    def is_allowed(self, member: discord.Member) -> bool:
        if member.id in ALLOWED_USER_IDS:
            return True

        return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)

    async def purge_from_message(
        self,
        interaction: discord.Interaction,
        message: discord.Message
    ):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Tento příkaz lze použít jen na serveru.",
                ephemeral=True
            )
            return

        if not self.is_allowed(interaction.user):
            await interaction.response.send_message(
                "Na tento příkaz nemáš oprávnění.",
                ephemeral=True
            )
            return

        channel = interaction.channel
        if channel is None or not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "Tento příkaz lze použít jen v textovém kanálu.",
                ephemeral=True
            )
            return

        if message.channel.id != channel.id:
            await interaction.response.send_message(
                "Musíš vybrat zprávu ze stejného kanálu.",
                ephemeral=True
            )
            return

        me = interaction.guild.me
        if me is None:
            await interaction.response.send_message(
                "Nepodařilo se zjistit bota na serveru.",
                ephemeral=True
            )
            return

        perms = channel.permissions_for(me)
        if not perms.manage_messages:
            await interaction.response.send_message(
                "Bot nemá oprávnění Spravovat zprávy.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        to_delete = [message]

        try:
            async for msg in channel.history(limit=None, after=message):
                to_delete.append(msg)

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
                deleted = await channel.delete_messages(recent_messages)
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
