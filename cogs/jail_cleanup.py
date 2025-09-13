# cogs/jail_cleanup.py
import contextlib
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands
from discord import app_commands

# konstanty
VERIFIED_ROLE_ID = 1358887522079346801       # verified role
JAIL_CHANNEL_ID = 1358876461825523863        # jail room
MAX_BULK_DELETE_DAYS_LIMIT = 14              # discord limit pro hromadne mazani (14 dni)

# povoleni pro /cleanup_jail
ALLOWED_ROLE_IDS = [
    1358898283782602932,  
]
ALLOWED_USER_IDS = [
    685958402442133515, 
]


class JailCleanup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # jadro uklidu
    async def _cleanup_for_member(self, member: discord.Member):
        channel = member.guild.get_channel(JAIL_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return

        cutoff_datetime = datetime.now(timezone.utc) - timedelta(days=MAX_BULK_DELETE_DAYS_LIMIT)
        messages_to_bulk_delete: list[discord.Message] = []
        messages_to_delete_individually: list[discord.Message] = []

        async for message in channel.history(limit=None, oldest_first=False):
            # zpravy uzivatele
            if message.author.id == member.id:
                (messages_to_delete_individually if message.created_at < cutoff_datetime else messages_to_bulk_delete).append(message)
                continue

            # botovy odpovedi (reply) na nej
            if message.author.bot and message.reference and message.reference.message_id:
                referenced_message = None
                with contextlib.suppress(discord.NotFound, discord.Forbidden, discord.HTTPException):
                    referenced_message = await channel.fetch_message(message.reference.message_id)
                if referenced_message and referenced_message.author.id == member.id:
                    (messages_to_delete_individually if message.created_at < cutoff_datetime else messages_to_bulk_delete).append(message)

        # bulk mazani po 100
        for i in range(0, len(messages_to_bulk_delete), 100):
            chunk = messages_to_bulk_delete[i:i+100]
            try:
                await channel.delete_messages(chunk)
            except Exception:
                # fallback smazat kusove
                for msg in chunk:
                    with contextlib.suppress(Exception):
                        await msg.delete()

        # stare kusove
        for msg in messages_to_delete_individually:
            with contextlib.suppress(Exception):
                await msg.delete()

    # event pridani verified role
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        before_role_ids = {role.id for role in before.roles}
        after_role_ids = {role.id for role in after.roles}
        if VERIFIED_ROLE_ID not in before_role_ids and VERIFIED_ROLE_ID in after_role_ids:
            await self._cleanup_for_member(after)

    # slash prikaz pro manualni uklid
    @app_commands.command(
        name="cleanup_jail",
        description="Smaže v jailu zprávy uživatele a botovy reply na něj.",
    )
    @app_commands.describe(user="Uživatel, kterému vyčistit jail zprávy")
    async def cleanup_jail(self, interaction: discord.Interaction, user: discord.User):
        member = interaction.user

        # kontrola jestli je uzivatel povolen
        has_allowed_role = any(role.id in ALLOWED_ROLE_IDS for role in member.roles)
        is_allowed_user = member.id in ALLOWED_USER_IDS

        if not (has_allowed_role or is_allowed_user):
            await interaction.response.send_message(
                "Nemáš oprávnění použít tento příkaz.", ephemeral=True
            )
            return

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Příkaz musí být spuštěn na serveru.", ephemeral=True)
            return

        target_member = guild.get_member(user.id)
        if target_member is None:
            await interaction.response.send_message("Uživatel není na serveru.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        await self._cleanup_for_member(target_member)
        await interaction.followup.send("Hotovo. Jail pro uživatele byl vyčištěn.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(JailCleanup(bot))

