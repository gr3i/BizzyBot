import discord
from discord import app_commands
from discord.ext import commands

from db.session import SessionLocal
from db.models import Verification


# Pouze tento Discord uzivatel muze prikazy spustit
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


def get_latest_verified_rows(session):
    """
    Nacte pouze posledni verified zaznam kazdeho Discord uzivatele.
    """

    rows = (
        session.query(Verification)
        .filter(Verification.verified == True)
        .order_by(Verification.id.desc())
        .all()
    )

    latest_rows = []
    seen_users = set()

    for row in rows:
        if row.user_id in seen_users:
            continue

        seen_users.add(row.user_id)
        latest_rows.append(row)

    return rows, latest_rows


def classify_row(row):
    """
    Rozhodne, co se ma se zaznamem udelat.

    Vraci:
    migrate       -> je potreba doplnit ||ident
    already       -> VUT ident uz existuje
    non_vut       -> nejde o VUT e-mail
    invalid       -> zaznam nejde bezpecne zpracovat
    """

    stored_value = (row.mail or "").strip()

    # Pokud uz tam || je, zkontrolujeme jeho obsah
    if "||" in stored_value:
        parts = stored_value.split("||", 1)

        mail = parts[0].strip()
        ident = parts[1].strip()

        if mail and ident:
            return {
                "status": "already",
                "mail": mail,
                "ident": ident,
                "new_value": stored_value,
            }

        # Napr. mail||
        stored_value = mail

    if not is_vut_email(stored_value):
        return {
            "status": "non_vut",
            "mail": stored_value,
            "ident": None,
            "new_value": None,
        }

    ident = get_ident_from_email(stored_value)

    if not ident:
        return {
            "status": "invalid",
            "mail": stored_value,
            "ident": None,
            "new_value": None,
        }

    new_value = f"{stored_value}||{ident}"

    return {
        "status": "migrate",
        "mail": stored_value,
        "ident": ident,
        "new_value": new_value,
    }


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


    # DRY RUN
    @app_commands.command(
        name="migrate_vut_idents_dry_run",
        description="Dry run doplneni VUT ID/loginu do starych verifikaci.",
    )
    @app_commands.guild_only()
    async def migrate_vut_idents_dry_run(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.user.id != ALLOWED_USER_ID:
            await interaction.response.send_message(
                "Tento prikaz nemuzes pouzit.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        with SessionLocal() as session:
            rows, latest_rows = get_latest_verified_rows(session)

            to_migrate = []
            already_migrated = []
            non_vut = []
            invalid = []

            for row in latest_rows:
                result = classify_row(row)

                if result["status"] == "migrate":
                    to_migrate.append(
                        (
                            row.id,
                            row.user_id,
                            result["mail"],
                            result["ident"],
                            result["new_value"],
                        )
                    )

                elif result["status"] == "already":
                    already_migrated.append(
                        f"Discord ID: {row.user_id} | "
                        f"{result['mail']} | "
                        f"VUT: {result['ident']}"
                    )

                elif result["status"] == "non_vut":
                    non_vut.append(
                        f"Discord ID: {row.user_id} | "
                        f"{result['mail']}"
                    )

                elif result["status"] == "invalid":
                    invalid.append(
                        f"Discord ID: {row.user_id} | "
                        f"{result['mail']}"
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
            "Neni VUT e-mail",
            non_vut,
        )

        await send_list(
            interaction,
            "Neplatne zaznamy - manualni kontrola",
            invalid,
        )


    # APPLY
    @app_commands.command(
        name="migrate_vut_idents_apply",
        description="Doplni VUT ID/login do starych verifikaci.",
    )
    @app_commands.guild_only()
    async def migrate_vut_idents_apply(
        self,
        interaction: discord.Interaction,
    ):
        if interaction.user.id != ALLOWED_USER_ID:
            await interaction.response.send_message(
                "Tento prikaz nemuzes pouzit.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        migrated = []
        already_migrated = []
        non_vut = []
        invalid = []

        session = SessionLocal()

        try:
            rows, latest_rows = get_latest_verified_rows(session)

            for row in latest_rows:
                result = classify_row(row)

                if result["status"] == "migrate":
                    old_value = result["mail"]
                    new_value = result["new_value"]

                    # Skutecna zmena v databazi
                    row.mail = new_value

                    migrated.append(
                        f"Discord ID: {row.user_id} | "
                        f"{old_value} -> {new_value}"
                    )

                elif result["status"] == "already":
                    already_migrated.append(
                        f"Discord ID: {row.user_id} | "
                        f"{result['mail']} | "
                        f"VUT: {result['ident']}"
                    )

                elif result["status"] == "non_vut":
                    non_vut.append(
                        f"Discord ID: {row.user_id} | "
                        f"{result['mail']}"
                    )

                elif result["status"] == "invalid":
                    invalid.append(
                        f"Discord ID: {row.user_id} | "
                        f"{result['mail']}"
                    )

            # Vsechny zmeny ulozime najednou
            session.commit()

        except Exception as error:
            # Pri chybe zahodime neulozene zmeny
            session.rollback()

            await interaction.followup.send(
                "**VUT IDENT MIGRATION - CHYBA**\n\n"
                "Doslo k chybe pri migraci.\n"
                "Zmeny nebyly ulozeny.\n\n"
                f"Chyba: `{type(error).__name__}: {error}`",
                ephemeral=True,
            )
            return

        finally:
            session.close()

        summary = (
            "**VUT IDENT MIGRATION - HOTOVO**\n\n"

            f"Verified zaznamu v DB celkem: **{len(rows)}**\n"
            f"Unikatnich Verified uzivatelu: **{len(latest_rows)}**\n\n"

            f"Uspesne migrovano: **{len(migrated)}**\n"
            f"Uz ma VUT ID/login: **{len(already_migrated)}**\n"
            f"Neni VUT e-mail: **{len(non_vut)}**\n"
            f"Neplatny zaznam: **{len(invalid)}**\n\n"

            "**Zmeny byly ulozeny do databaze.**"
        )

        await interaction.followup.send(
            summary,
            ephemeral=True,
        )

        await send_list(
            interaction,
            "Migrovane zaznamy",
            migrated,
        )

        await send_list(
            interaction,
            "Neni VUT e-mail",
            non_vut,
        )

        await send_list(
            interaction,
            "Neplatne zaznamy - manualni kontrola",
            invalid,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(MigrateVutIdents(bot))