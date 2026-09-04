import discord
from discord import app_commands
from discord.ext import commands

from db.session import SessionLocal
from db.models import Verification


# Pouze tento Discord uzivatel muze prikaz spustit
ALLOWED_USER_ID = 685958402442133515


def is_vut_email(mail: str) -> bool:
    """
    Overi, ze jde o VUT e-mail.
    """

    mail = (mail or "").strip().lower()

    if "@" not in mail:
        return False

    domain = mail.rsplit("@", 1)[1]

    return (
        domain == "vut.cz"
        or domain.endswith(".vut.cz")
        or domain == "vutbr.cz"
        or domain.endswith(".vutbr.cz")
    )


def get_ident_from_email(mail: str) -> str | None:
    """
    Vezme cast e-mailu pred @.

    Napr.:
    268500@vutbr.cz -> 268500
    xkinst01@vutbr.cz -> xkinst01
    """

    mail = (mail or "").strip().lower()

    if "@" not in mail:
        return None

    ident = mail.split("@", 1)[0].strip()

    if not ident:
        return None

    return ident


async def send_list(
    interaction: discord.Interaction,
    title: str,
    lines: list[str],
):
    """
    Rozdeli dlouhy seznam do vice Discord zprav.
    """

    if not lines:
        return

    message = f"**{title}**\n"

    for line in lines:
        new_line = line + "\n"

        if len(message) + len(new_line) > 1900:
            await interaction.followup.send(
                message,
                ephemeral=True,
            )

            message = f"**{title} - pokracovani**\n"

        message += new_line

    if message.strip():
        await interaction.followup.send(
            message,
            ephemeral=True,
        )


class MigrateVutIdents(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="migrate_vut_idents_dry_run",
        description="Dry run doplneni VUT ID/loginu do starych verifikaci.",
    )
    @app_commands.guild_only()
    async def migrate_vut_idents_dry_run(
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

        await interaction.response.defer(ephemeral=True)

        with SessionLocal() as session:
            rows = (
                session.query(Verification)
                .filter(Verification.verified == True)
                .order_by(Verification.id.desc())
                .all()
            )

        # Zajima nas pouze posledni verified zaznam kazdeho uzivatele
        latest_rows = []

        seen_users = set()

        for row in rows:
            if row.user_id in seen_users:
                continue

            seen_users.add(row.user_id)
            latest_rows.append(row)

        to_migrate = []
        already_migrated = []
        non_vut = []
        invalid = []

        for row in latest_rows:
            stored_value = (row.mail or "").strip().lower()

            # Pokud uz je ulozen mail||ident
            if "||" in stored_value:
                parts = stored_value.split("||", 1)

                mail = parts[0].strip()
                ident = parts[1].strip()

                if mail and ident:
                    already_migrated.append(
                        f"Discord ID: {row.user_id} | "
                        f"{mail} | VUT: {ident}"
                    )
                    continue

                # Napr. mail||
                stored_value = mail

            if not is_vut_email(stored_value):
                non_vut.append(
                    f"Discord ID: {row.user_id} | {stored_value}"
                )
                continue

            ident = get_ident_from_email(stored_value)

            if not ident:
                invalid.append(
                    f"Discord ID: {row.user_id} | {stored_value}"
                )
                continue

            new_value = f"{stored_value}||{ident}"

            to_migrate.append(
                (
                    row.id,
                    row.user_id,
                    stored_value,
                    ident,
                    new_value,
                )
            )

        summary = (
            "**VUT IDENT MIGRATION - DRY RUN**\n\n"

            f"Verified zaznamu v DB celkem: **{len(rows)}**\n"
            f"Unikatnich Verified uzivatelu: **{len(latest_rows)}**\n\n"

            f"K migraci: **{len(to_migrate)}**\n"
            f"Uz ma VUT ID/login: **{len(already_migrated)}**\n"
            f"Neni VUT e-mail: **{len(non_vut)}**\n"
            f"Neplatny zaznam: **{len(invalid)}**\n\n"

            "**DRY RUN - databaze nebyla zmenena.**"
        )

        await interaction.followup.send(
            summary,
            ephemeral=True,
        )

        migration_lines = []

        for (
            row_id,
            user_id,
            old_value,
            ident,
            new_value,
        ) in to_migrate:

            migration_lines.append(
                f"Discord ID: {user_id} | "
                f"{old_value} -> {new_value}"
            )

        await send_list(
            interaction,
            "Zaznamy, ktere by se migrovaly",
            migration_lines,
        )

        await send_list(
            interaction,
            "Neplatne zaznamy - manualni kontrola",
            invalid,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(MigrateVutIdents(bot))