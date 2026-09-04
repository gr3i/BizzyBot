import logging

import discord
from discord import app_commands
from discord.ext import commands


logger = logging.getLogger(__name__)


ALLOWED_USER_ID = 685958402442133515

FP_ROLE_ID = 1466036385017233636

YEAR_ROLE_IDS = {
    "1BC": 1469298142959898840,
    "2BC": 1469298381200293963,
    "3+BC": 1469298468399878145,
    "1MGR": 1469298670066204702,
    "2+MGR": 1469298920562757785,
}


class FpYearRoles(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="fp_year_roles_clear",
        description="Odebere vsem FP studentum stare rocnikove role.",
    )
    @app_commands.guild_only()
    async def fp_year_roles_clear(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.user.id != ALLOWED_USER_ID:
            await interaction.response.send_message(
                "Tento prikaz nemuzes pouzit.",
                ephemeral=True,
            )
            return

        guild = interaction.guild

        if guild is None:
            return

        # Odpovime hned, aby prikaz nevyprsel
        await interaction.response.send_message(
            "Odebirani rocnikovych roli bylo spusteno.\n"
            "Vysledek ti poslu do DM.",
            ephemeral=True,
        )

        dm_channel = await interaction.user.create_dm()

        fp_role = guild.get_role(FP_ROLE_ID)

        if fp_role is None:
            await dm_channel.send(
                "Chyba: FP role nebyla nalezena."
            )
            return

        year_roles = {}

        for role_name, role_id in YEAR_ROLE_IDS.items():
            role = guild.get_role(role_id)

            if role is None:
                await dm_channel.send(
                    f"Chyba: role `{role_name}` nebyla nalezena."
                )
                return

            year_roles[role_name] = role

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

        # Overime, ze bot muze se vsemi rocnikovymi rolemi pracovat
        for role_name, role in year_roles.items():
            if role >= bot_member.top_role:
                await dm_channel.send(
                    f"Chyba: bot nemuze spravovat roli `{role_name}`."
                )
                return

        if not guild.chunked:
            try:
                await guild.chunk(cache=True)

            except Exception as error:
                await dm_channel.send(
                    "Chyba pri nacitani clenu serveru:\n"
                    f"`{type(error).__name__}: {error}`"
                )
                return

        fp_members = [
            member
            for member in guild.members
            if fp_role in member.roles
        ]

        changed_members = []
        errors = []

        removed_counts = {
            role_name: 0
            for role_name in YEAR_ROLE_IDS
        }

        total_fp = len(fp_members)

        logger.info(
            "FP year role clear started. fp_members=%s",
            total_fp,
        )

        for index, member in enumerate(fp_members, start=1):

            if (
                index == 1
                or index % 25 == 0
                or index == total_fp
            ):
                progress = (
                    (index / total_fp) * 100
                    if total_fp
                    else 100
                )

                logger.info(
                    "FP year role clear progress: "
                    "%s/%s users processed (%.1f%%)",
                    index,
                    total_fp,
                    progress,
                )

            roles_to_remove = []
            removed_names = []

            for role_name, role in year_roles.items():
                if role in member.roles:
                    roles_to_remove.append(role)
                    removed_names.append(role_name)

            # Uzivatel nema zadnou rocnikovou roli
            if not roles_to_remove:
                continue

            try:
                # Vsechny rocnikove role odebereme jednim requestem
                await member.remove_roles(
                    *roles_to_remove,
                    reason="Reset FP year roles for new academic year",
                )

            except (discord.Forbidden, discord.HTTPException) as error:
                logger.exception(
                    "Failed to remove FP year roles. "
                    "discord_id=%s, roles=%s",
                    member.id,
                    removed_names,
                )

                errors.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"{', '.join(removed_names)} | "
                    f"{type(error).__name__}: {error}"
                )
                continue

            for role_name in removed_names:
                removed_counts[role_name] += 1

            changed_members.append(
                f"{member} | Discord ID: {member.id} | "
                f"odebrano: {', '.join(removed_names)}"
            )

            logger.info(
                "FP year roles removed. "
                "discord_id=%s, roles=%s",
                member.id,
                removed_names,
            )

        total_removed_roles = sum(
            removed_counts.values()
        )

        summary = (
            "**FP YEAR ROLES - HOTOVO**\n\n"
            f"FP uzivatelu celkem: **{total_fp}**\n"
            f"Uzivatelu se zmenou: **{len(changed_members)}**\n"
            f"Odebranych roli celkem: **{total_removed_roles}**\n"
            f"Chyby: **{len(errors)}**\n\n"
            "**Odebrane role:**\n"
            f"1BC: **{removed_counts['1BC']}**\n"
            f"2BC: **{removed_counts['2BC']}**\n"
            f"3+BC: **{removed_counts['3+BC']}**\n"
            f"1MGR: **{removed_counts['1MGR']}**\n"
            f"2+MGR: **{removed_counts['2+MGR']}**\n\n"
            "**Rocnikove role byly skutecne odebrany.**"
        )

        await dm_channel.send(summary)

        if errors:
            error_message = "**CHYBY PRI ODEBIRANI ROLI**\n"

            for error in errors:
                line = error + "\n"

                if len(error_message) + len(line) > 1900:
                    await dm_channel.send(error_message)
                    error_message = (
                        "**CHYBY PRI ODEBIRANI ROLI - pokracovani**\n"
                    )

                error_message += line

            if error_message.strip():
                await dm_channel.send(error_message)

        logger.info(
            "FP year role clear finished. "
            "fp_members=%s, changed_members=%s, "
            "removed_roles=%s, errors=%s",
            total_fp,
            len(changed_members),
            total_removed_roles,
            len(errors),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(FpYearRoles(bot))