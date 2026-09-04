import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from db.models import Verification
from db.session import SessionLocal
from services.vut_api import RateLimited, VutApiError


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


# Pauza mezi jednotlivymi pozadavky na VUT API
API_REQUEST_DELAY = 0.5

# Po kazde davce dame API delsi pauzu
API_BATCH_SIZE = 100
API_BATCH_DELAY = 10

# Pokud API vrati 429, pockame a stejny request zopakujeme
RATE_LIMIT_MAX_RETRIES = 3
RATE_LIMIT_DEFAULT_WAIT = 60


def load_verified_vut_idents() -> dict[int, str]:
    """
    Nacte VUT ident z posledniho verified zaznamu uzivatele.
    """

    result: dict[int, str] = {}
    seen_users: set[int] = set()

    with SessionLocal() as session:
        rows = (
            session.query(Verification)
            .filter(Verification.verified == True)
            .order_by(Verification.id.desc())
            .all()
        )

    for row in rows:
        if row.user_id in seen_users:
            continue

        seen_users.add(row.user_id)

        stored_value = (row.mail or "").strip()
        parts = stored_value.split("||", 1)

        if len(parts) != 2:
            continue

        vut_ident = parts[1].strip().lower()

        if not vut_ident:
            continue

        result[row.user_id] = vut_ident

    return result


def relation_summary(details: dict) -> str:
    """
    Vytvori kratky vypis vztahu pro manualni kontrolu.
    """

    output = []

    for vztah in details.get("vztahy") or []:
        fakulta = (
            ((vztah.get("fakulta") or {}).get("zkratka") or "")
            .strip()
            .upper()
        )

        pozice = (
            (vztah.get("pozice") or "")
            .strip()
            .lower()
        )

        typ = (
            ((vztah.get("typ_studia") or {}).get("zkratka") or "")
            .strip()
            .upper()
        )

        rok = vztah.get("rok_studia")

        output.append(
            f"{fakulta or '-'} / {pozice or '-'} / "
            f"{typ or '-'} / rok {rok if rok is not None else '-'}"
        )

    if not output:
        return "zadne vztahy"

    return "; ".join(output[:5])


def get_fp_year_target(details: dict) -> tuple[str | None, str]:
    """
    Vraci cilovou rocnikovou roli podle aktualniho FP studia.

    B rok 1     -> 1BC
    B rok 2     -> 2BC
    B rok 3+    -> 3+BC
    N rok 1     -> 1MGR
    N rok 2+    -> 2+MGR
    """

    targets: set[str] = set()

    for vztah in details.get("vztahy") or []:
        pozice = (
            (vztah.get("pozice") or "")
            .strip()
            .lower()
        )

        fakulta = (
            ((vztah.get("fakulta") or {}).get("zkratka") or "")
            .strip()
            .upper()
        )

        # Zajima nas pouze studium na FP
        if pozice != "student" or fakulta != "FP":
            continue

        typ = (
            ((vztah.get("typ_studia") or {}).get("zkratka") or "")
            .strip()
            .upper()
        )

        rok = vztah.get("rok_studia")

        if not isinstance(rok, int) or rok < 1:
            continue

        # Bakalarske studium
        if typ == "B":
            if rok == 1:
                targets.add("1BC")
            elif rok == 2:
                targets.add("2BC")
            else:
                targets.add("3+BC")

        # Navazujici magisterske studium
        elif typ == "N":
            if rok == 1:
                targets.add("1MGR")
            else:
                targets.add("2+MGR")

    if len(targets) == 1:
        return next(iter(targets)), "OK"

    # Kdyby API vratilo dva rozdilne platne FP rocniky
    if len(targets) > 1:
        return None, "AMBIGUOUS"

    return None, "UNSUPPORTED"


async def get_user_details_with_retry(
    vut_api,
    vut_ident: str,
):
    """
    Zavola VUT API a pri 429 stejny request zopakuje.
    """

    for attempt in range(RATE_LIMIT_MAX_RETRIES + 1):
        try:
            return await vut_api.get_user_details(vut_ident)

        except RateLimited as error:
            if attempt >= RATE_LIMIT_MAX_RETRIES:
                raise

            wait_seconds = error.retry_after or RATE_LIMIT_DEFAULT_WAIT

            logger.warning(
                "VUT API rate limit during FP year role sync. "
                "vut_ident=%s, retry=%s/%s, wait_seconds=%s",
                vut_ident,
                attempt + 1,
                RATE_LIMIT_MAX_RETRIES,
                wait_seconds,
            )

            await asyncio.sleep(wait_seconds)


async def send_list(
    destination,
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
            await destination.send(message)
            message = f"**{title} - pokracovani**\n"

        message += new_line

    if message.strip():
        await destination.send(message)


class FpYearRoleSync(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="fp_year_roles_dry_run",
        description="Dry run prideleni rocnikovych roli FP studentum.",
    )
    @app_commands.guild_only()
    async def fp_year_roles_dry_run(
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

        # Odpovime hned, protoze kontrola muze kvuli VUT API trvat dlouho
        await interaction.response.send_message(
            "FP year role dry run byl spusten.\n"
            "Prubeh uvidis v konzoli a vysledek ti poslu do DM.",
            ephemeral=True,
        )

        try:
            dm_channel = await interaction.user.create_dm()

            await dm_channel.send(
                "**FP YEAR ROLE SYNC - DRY RUN STARTED**\n\n"
                "Kontrola byla spustena. Zadne role se nebudou menit."
            )

        except discord.HTTPException as error:
            logger.exception(
                "Could not create DM for FP year role dry run. error=%s",
                error,
            )
            return

        # Ujistime se, ze mame vsechny cleny serveru
        if not guild.chunked:
            try:
                await guild.chunk(cache=True)

            except Exception as error:
                await dm_channel.send(
                    "Dry run byl ukoncen.\n"
                    f"Nepodarilo se nacist vsechny cleny serveru: `{error}`"
                )
                return

        fp_role = guild.get_role(FP_ROLE_ID)

        if fp_role is None:
            await dm_channel.send(
                "Dry run byl ukoncen. FP role nebyla nalezena."
            )
            return

        year_roles: dict[str, discord.Role] = {}
        missing_roles = []

        for role_name, role_id in YEAR_ROLE_IDS.items():
            role = guild.get_role(role_id)

            if role is None:
                missing_roles.append(role_name)
                continue

            year_roles[role_name] = role

        if missing_roles:
            await dm_channel.send(
                "Dry run byl ukoncen. Chybi rocnikove role: "
                + ", ".join(missing_roles)
            )
            return

        # Kontrolujeme vsechny uzivatele s FP roli
        fp_members = [
            member
            for member in guild.members
            if fp_role in member.roles
        ]

        vut_idents = load_verified_vut_idents()

        target_counts = {
            role_name: 0
            for role_name in YEAR_ROLE_IDS
        }

        would_assign = {
            role_name: []
            for role_name in YEAR_ROLE_IDS
        }

        already_correct = []
        missing_ident = []
        unsupported = []
        ambiguous = []
        api_errors = []

        processed_with_api = 0
        total_members = len(fp_members)

        logger.info(
            "FP year role DRY RUN started. fp_members=%s",
            total_members,
        )

        for index, member in enumerate(fp_members, start=1):
            # Prubeh v konzoli
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
                    "FP year role DRY RUN progress: "
                    "%s/%s users processed (%.1f%%)",
                    index,
                    total_members,
                    progress,
                )

            vut_ident = vut_idents.get(member.id)

            if not vut_ident:
                missing_ident.append(
                    f"{member} | Discord ID: {member.id}"
                )
                continue

            processed_with_api += 1

            try:
                details = await get_user_details_with_retry(
                    self.bot.vut_api,
                    vut_ident,
                )

            except VutApiError as error:
                api_errors.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"VUT: {vut_ident} | {error}"
                )

                logger.warning(
                    "FP year role DRY RUN API error. "
                    "discord_id=%s, vut_ident=%s, error=%s",
                    member.id,
                    vut_ident,
                    error,
                )

                continue

            except Exception as error:
                logger.exception(
                    "Unexpected API error during FP year role DRY RUN. "
                    "discord_id=%s, vut_ident=%s",
                    member.id,
                    vut_ident,
                )

                api_errors.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"VUT: {vut_ident} | "
                    f"{type(error).__name__}: {error}"
                )

                continue

            finally:
                # Kratka pauza po kazdem API uzivateli
                await asyncio.sleep(API_REQUEST_DELAY)

                # Delsi pauza po kazde davce
                if (
                    processed_with_api > 0
                    and processed_with_api % API_BATCH_SIZE == 0
                ):
                    logger.info(
                        "FP year role DRY RUN batch cooldown. "
                        "api_requests=%s, wait_seconds=%s",
                        processed_with_api,
                        API_BATCH_DELAY,
                    )

                    await asyncio.sleep(API_BATCH_DELAY)

            # 404 tady automaticky nic neznamena
            # Jen ho dame na manualni kontrolu
            if details is None:
                unsupported.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"VUT: {vut_ident} | API vratilo 404"
                )
                continue

            if not isinstance(details, dict):
                api_errors.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"VUT: {vut_ident} | "
                    "API vratilo neocekavany format"
                )
                continue

            target_role_name, status = get_fp_year_target(details)

            if status == "AMBIGUOUS":
                ambiguous.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"VUT: {vut_ident} | "
                    f"{relation_summary(details)}"
                )
                continue

            if status != "OK" or target_role_name is None:
                unsupported.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"VUT: {vut_ident} | "
                    f"{relation_summary(details)}"
                )
                continue

            target_counts[target_role_name] += 1

            # Podivame se na soucasne rocnikove role
            current_year_roles = [
                role_name
                for role_name, role in year_roles.items()
                if role in member.roles
            ]

            # Ma presne tu roli, kterou ma mit
            if current_year_roles == [target_role_name]:
                already_correct.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"VUT: {vut_ident} | {target_role_name}"
                )
                continue

            current_text = (
                "+".join(current_year_roles)
                if current_year_roles
                else "bez rocnikove role"
            )

            would_assign[target_role_name].append(
                f"{member} | Discord ID: {member.id} | "
                f"VUT: {vut_ident} | "
                f"{current_text} -> {target_role_name}"
            )

        total_would_assign = sum(
            len(lines)
            for lines in would_assign.values()
        )

        valid_targets = sum(target_counts.values())

        summary = (
            "**FP YEAR ROLE SYNC - DRY RUN**\n\n"

            f"FP uzivatelu celkem: **{total_members}**\n"
            f"Platne FP studium podle VUT API: **{valid_targets}**\n\n"

            "**Cilove rocnikove role:**\n"
            f"1BC: **{target_counts['1BC']}**\n"
            f"2BC: **{target_counts['2BC']}**\n"
            f"3+BC: **{target_counts['3+BC']}**\n"
            f"1MGR: **{target_counts['1MGR']}**\n"
            f"2+MGR: **{target_counts['2+MGR']}**\n\n"

            "**Zmeny, ktere by se provedly:**\n"
            f"Pridat nebo opravit rocnikovou roli: "
            f"**{total_would_assign}**\n"
            f"Jiz spravna rocnikova role: "
            f"**{len(already_correct)}**\n\n"

            "**Manualni kontrola:**\n"
            f"Chybi VUT ID v DB: **{len(missing_ident)}**\n"
            f"Nenalezeno platne FP B/N studium: "
            f"**{len(unsupported)}**\n"
            f"Vice moznych FP rocniku: **{len(ambiguous)}**\n"
            f"API chyby: **{len(api_errors)}**\n\n"

            "**DRY RUN - zadne role nebyly zmeneny.**"
        )

        await dm_channel.send(summary)

        # Vypiseme lidi podle cilove role
        for role_name in YEAR_ROLE_IDS:
            await send_list(
                dm_channel,
                f"PRIDELIT {role_name}",
                would_assign[role_name],
            )

        await send_list(
            dm_channel,
            "MANUAL - chybi VUT ID v databazi",
            missing_ident,
        )

        await send_list(
            dm_channel,
            "MANUAL - bez platneho FP B/N studia",
            unsupported,
        )

        await send_list(
            dm_channel,
            "MANUAL - vice moznych FP rocniku",
            ambiguous,
        )

        await send_list(
            dm_channel,
            "MANUAL - chyba VUT API",
            api_errors,
        )

        logger.info(
            "FP year role DRY RUN finished. "
            "fp_members=%s, valid_targets=%s, would_assign=%s, "
            "already_correct=%s, missing_ident=%s, unsupported=%s, "
            "ambiguous=%s, api_errors=%s",
            total_members,
            valid_targets,
            total_would_assign,
            len(already_correct),
            len(missing_ident),
            len(unsupported),
            len(ambiguous),
            len(api_errors),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(FpYearRoleSync(bot))