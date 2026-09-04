import logging

import discord
from discord import app_commands
from discord.ext import commands


logger = logging.getLogger(__name__)


ALLOWED_USER_ID = 685958402442133515

VERIFIED_ROLE_ID = 1358887522079346801
EXSTUDENT_ROLE_ID = 1545393809075077120


class ExStudentRoleCleanup(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="exstudent_roles_clear",
        description="Odebere ExStudentum vsechny role krome Verified a ExStudent.",
    )
    @app_commands.guild_only()
    async def exstudent_roles_clear(
        self,
        interaction: discord.Interaction,
    ):
        # Prikaz muze spustit pouze povoleny uzivatel
        if interaction.user.id != ALLOWED_USER_ID:
            await interaction.response.send_message(
                "Tento prikaz nemuzes pouzit.",
                ephemeral=True,
            )
            return

        guild = interaction.guild

        if guild is None:
            return

        # Odpovime hned, aby interaction nevyprsel
        await interaction.response.send_message(
            "Mazani roli ExStudentu bylo spusteno.\n"
            "Vysledek ti poslu do DM.",
            ephemeral=True,
        )

        try:
            dm_channel = await interaction.user.create_dm()

        except discord.HTTPException as error:
            logger.exception(
                "Could not create DM channel. error=%s",
                error,
            )
            return

        verified_role = guild.get_role(VERIFIED_ROLE_ID)
        exstudent_role = guild.get_role(EXSTUDENT_ROLE_ID)

        if verified_role is None:
            await dm_channel.send(
                "Chyba: role Verified nebyla nalezena."
            )
            return

        if exstudent_role is None:
            await dm_channel.send(
                "Chyba: role ExStudent nebyla nalezena."
            )
            return

        bot_member = guild.me

        if bot_member is None:
            await dm_channel.send(
                "Chyba: nepodarilo se najit bota na serveru."
            )
            return

        if not bot_member.guild_permissions.manage_roles:
            await dm_channel.send(
                "Chyba: bot nema opravneni Manage Roles."
            )
            return

        # Nacteme vsechny cleny serveru
        if not guild.chunked:
            try:
                await guild.chunk(cache=True)

            except Exception as error:
                await dm_channel.send(
                    "Chyba pri nacitani clenu serveru:\n"
                    f"`{type(error).__name__}: {error}`"
                )
                return

        # Seznam ExStudentu vytvorime pred odebiranim roli
        exstudent_members = [
            member
            for member in guild.members
            if exstudent_role in member.roles
        ]

        total_members = len(exstudent_members)

        changed_members = []
        errors = []
        blocked_roles = []

        total_removed_roles = 0

        logger.info(
            "ExStudent role cleanup started. users=%s",
            total_members,
        )

        for index, member in enumerate(
            exstudent_members,
            start=1,
        ):
            # Prubeh vypisujeme do konzole
            if (
                index == 1
                or index % 25 == 0
                or index == total_members
            ):
                progress = (
                    (index / total_members) * 100
                    if total_members
                    else 100
                )

                logger.info(
                    "ExStudent role cleanup progress: "
                    "%s/%s users processed (%.1f%%)",
                    index,
                    total_members,
                    progress,
                )

            roles_to_remove = []
            blocked_for_member = []

            for role in member.roles:
                # @everyone nelze odebrat
                if role == guild.default_role:
                    continue

                # Verified a ExStudent zachovame
                if role.id in {
                    VERIFIED_ROLE_ID,
                    EXSTUDENT_ROLE_ID,
                }:
                    continue

                # Managed role nelze normalne odebrat
                if role.managed:
                    blocked_for_member.append(
                        f"{role.name} (managed)"
                    )
                    continue

                # Bot nemuze odebrat roli nad svou nejvyssi roli
                if role >= bot_member.top_role:
                    blocked_for_member.append(
                        f"{role.name} (hierarchy)"
                    )
                    continue

                roles_to_remove.append(role)

            # Pokud nejake role nejdou odebrat, zapiseme je
            if blocked_for_member:
                blocked_roles.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"{', '.join(blocked_for_member)}"
                )

                logger.warning(
                    "Some ExStudent roles cannot be removed. "
                    "discord_id=%s, roles=%s",
                    member.id,
                    blocked_for_member,
                )

            # Pokud nema zadne dalsi role, neni co delat
            if not roles_to_remove:
                continue

            removed_names = [
                role.name
                for role in roles_to_remove
            ]

            try:
                # Odebereme vsechny ostatni role najednou
                await member.remove_roles(
                    *roles_to_remove,
                    reason="ExStudent role cleanup",
                )

            except (discord.Forbidden, discord.HTTPException) as error:
                logger.exception(
                    "Failed to clear ExStudent roles. "
                    "discord_id=%s",
                    member.id,
                )

                errors.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"{type(error).__name__}: {error}"
                )
                continue

            except Exception as error:
                logger.exception(
                    "Unexpected ExStudent role cleanup error. "
                    "discord_id=%s",
                    member.id,
                )

                errors.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"{type(error).__name__}: {error}"
                )
                continue

            total_removed_roles += len(roles_to_remove)

            changed_members.append(
                f"{member} | Discord ID: {member.id} | "
                f"odebrano: {', '.join(removed_names)}"
            )

            logger.info(
                "ExStudent roles removed. "
                "discord_id=%s, roles=%s",
                member.id,
                removed_names,
            )

        summary = (
            "**EXSTUDENT ROLE CLEANUP - HOTOVO**\n\n"
            f"ExStudent uzivatelu celkem: **{total_members}**\n"
            f"Uzivatelu se zmenou: **{len(changed_members)}**\n"
            f"Odebranych roli celkem: **{total_removed_roles}**\n"
            f"Chyby: **{len(errors)}**\n"
            f"Uzivatelu s neodebratelnou roli: **{len(blocked_roles)}**\n\n"
            "Zachovane role:\n"
            "**Verified**\n"
            "**ExStudent**\n\n"
            "**Ostatni dostupne role byly skutecne odebrany.**"
        )

        await dm_channel.send(summary)

        await self.send_list(
            dm_channel,
            "CHYBY",
            errors,
        )

        await self.send_list(
            dm_channel,
            "MANUAL - neodebratelne role",
            blocked_roles,
        )

        logger.info(
            "ExStudent role cleanup finished. "
            "users=%s, changed=%s, removed_roles=%s, "
            "errors=%s, blocked=%s",
            total_members,
            len(changed_members),
            total_removed_roles,
            len(errors),
            len(blocked_roles),
        )

    async def send_list(
        self,
        destination,
        title: str,
        lines: list[str],
    ):
        # Dlouhe seznamy rozdelime do vice zprav
        if not lines:
            return

        message = f"**{title}**\n"

        for line in lines:
            new_line = line + "\n"

            if len(message) + len(new_line) > 1900:
                await destination.send(message)
                message = f"**{title} - pokracovani**\n"

            message += new_line

        if message.strip():
            await destination.send(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(ExStudentRoleCleanup(bot))