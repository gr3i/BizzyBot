import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from db.session import SessionLocal
from db.models import Verification
from services.vut_api import RateLimited, VutApiError


logger = logging.getLogger(__name__)


# Jediny uzivatel, ktery muze prikaz spustit
ALLOWED_USER_ID = 685958402442133515


# Role IDs
VERIFIED_ROLE_ID = 1358887522079346801
VUT_ROLE_ID = 1358911329737642014
FP_ROLE_ID = 1466036385017233636
EXSTUDENT_ROLE_ID = 1545393809075077120


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
    Nacte posledni overeny VUT identifikator pro uzivatele.

    V databazi je VUT overeni ulozene jako:
    email||vut_ident
    """

    result: dict[int, str] = {}

    with SessionLocal() as session:
        rows = (
            session.query(Verification)
            .filter(Verification.verified == True)
            .order_by(Verification.id.desc())
            .all()
        )

    for row in rows:
        # Pokud uz mame novejsi zaznam, starsi ignorujeme
        if row.user_id in result:
            continue

        stored_value = (row.mail or "").strip()

        parts = stored_value.split("||", 1)

        # Bez || nejde o VUT overeni
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


def classify_student(details: dict) -> str:
    """
    Vraci:
    FP          = platny B/N student na FP
    VUT         = platny B/N student na jine fakulte VUT
    EXSTUDENT   = API osobu zna, ale nema zadne vztahy
    UNSUPPORTED = nestandardni stav pro manualni kontrolu
    """

    vztahy = details.get("vztahy") or []

    # API osobu zna, ale nema zadny aktualni vztah
    # Takoveho cloveka povazujeme za ExStudent
    if not vztahy:
        return "EXSTUDENT"

    valid_fp = []
    valid_other = []

    # Nestandardni FP studentsky vztah
    unsupported_fp_student = False

    for vztah in vztahy:
        pozice = (
            (vztah.get("pozice") or "")
            .strip()
            .lower()
        )

        # Zajimaji nas pouze studentske vztahy
        if pozice != "student":
            continue

        fakulta = (
            ((vztah.get("fakulta") or {}).get("zkratka") or "")
            .strip()
            .upper()
        )

        typ = (
            ((vztah.get("typ_studia") or {}).get("zkratka") or "")
            .strip()
            .upper()
        )

        rok = vztah.get("rok_studia")

        # Platne studium je pouze bakalarske nebo navazujici magisterske
        valid_study = (
            typ in {"B", "N"}
            and isinstance(rok, int)
            and rok >= 1
            and bool(fakulta)
        )

        if valid_study:
            if fakulta == "FP":
                valid_fp.append(vztah)
            else:
                valid_other.append(vztah)

        elif fakulta == "FP":
            unsupported_fp_student = True

    # Platne FP studium ma prioritu
    if valid_fp:
        return "FP"

    # FP student s nestandardnim typem studia
    if unsupported_fp_student:
        return "UNSUPPORTED"

    # Platny B/N student na jine fakulte
    if valid_other:
        return "VUT"

    # API vratilo nejaky vztah, ale neni to bezpecny B/N student
    return "UNSUPPORTED"


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
                "VUT API rate limit during role sync. "
                "vut_ident=%s, retry=%s/%s, wait_seconds=%s",
                vut_ident,
                attempt + 1,
                RATE_LIMIT_MAX_RETRIES,
                wait_seconds,
            )

            await asyncio.sleep(wait_seconds)

async def send_list(
    interaction: discord.Interaction,
    title: str,
    lines: list[str],
):
    """
    Rozdeli dlouhy vypis do vice Discord zprav.
    """

    if not lines:
        return

    header = f"**{title}**\n"
    message = header

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


class VutRoleSync(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="vut_role_dry_run",
        description="Dry run kontroly VUT, FP a ExStudent roli.",
    )
    @app_commands.guild_only()
    async def vut_role_dry_run(
        self,
        interaction: discord.Interaction,
    ):
        # Prikaz muze spustit pouze vlastnik
        if interaction.user.id != ALLOWED_USER_ID:
            await interaction.response.send_message(
                "Tento prikaz nemuzes pouzit.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        await interaction.followup.send(
            "VUT role dry run byl spusten.\n"
            "Vysledek ti poslu do DM.",
            ephemeral=True,
        )

        dm_channel = await interaction.user.create_dm()

        guild = interaction.guild

        if guild is None:
            return

        # Ujistime se, ze mame nactene vsechny cleny serveru
        if not guild.chunked:
            try:
                await guild.chunk(cache=True)

            except Exception as error:
                await interaction.followup.send(
                    f"Nepodarilo se nacist vsechny cleny serveru: {error}",
                    ephemeral=True,
                )
                return

        verified_role = guild.get_role(VERIFIED_ROLE_ID)
        vut_role = guild.get_role(VUT_ROLE_ID)
        fp_role = guild.get_role(FP_ROLE_ID)
        exstudent_role = guild.get_role(EXSTUDENT_ROLE_ID)

        missing_roles = []

        if verified_role is None:
            missing_roles.append("Verified")

        if vut_role is None:
            missing_roles.append("VUT")

        if fp_role is None:
            missing_roles.append("FP")

        if exstudent_role is None:
            missing_roles.append("ExStudent")

        if missing_roles:
            await interaction.followup.send(
                "Na serveru chybi role: "
                + ", ".join(missing_roles),
                ephemeral=True,
            )
            return

        all_members = list(guild.members)

        verified_members = [
            member
            for member in all_members
            if verified_role in member.roles
        ]

        # Kontrolujeme pouze Verified uzivatele,
        # kteri maji VUT nebo FP roli
        target_members = [
            member
            for member in verified_members
            if vut_role in member.roles or fp_role in member.roles
        ]

        vut_only_count = 0
        fp_only_count = 0
        both_count = 0

        for member in target_members:
            has_vut = vut_role in member.roles
            has_fp = fp_role in member.roles

            if has_vut and has_fp:
                both_count += 1

            elif has_vut:
                vut_only_count += 1

            elif has_fp:
                fp_only_count += 1

        vut_idents = load_verified_vut_idents()

        # Vysledky
        vut_to_fp = []
        fp_to_vut = []

        both_to_fp = []
        both_to_vut = []

        keep_fp = []
        keep_vut = []

        to_exstudent = []

        unsupported = []
        missing_ident = []
        api_errors = []

        expected_fp = 0
        expected_vut = 0
        expected_exstudent = 0

        api_request_count = 0

        for index, member in enumerate(target_members, start=1):
            if index == 1 or index % 25 == 0 or index == len(target_members):
                progress = (index / len(target_members)) * 100

                logger.info(
                    "VUT role sync progress: %s/%s users processed (%.1f%%)",
                    index,
                    len(target_members),
                    progress,
                )

            has_vut = vut_role in member.roles
            has_fp = fp_role in member.roles

            vut_ident = vut_idents.get(member.id)

            # Nemame VUT ID/login v nasi databazi
            if not vut_ident:
                missing_ident.append(
                    f"{member} | Discord ID: {member.id}"
                )
                continue

            api_request_count += 1

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
                continue

            except Exception as error:
                logger.exception(
                    "Unexpected VUT API error during dry run. user_id=%s",
                    member.id,
                )

                api_errors.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"VUT: {vut_ident} | {type(error).__name__}: {error}"
                )
                continue

            finally:
                # Kratka pauza po kazdem uzivateli
                await asyncio.sleep(API_REQUEST_DELAY)

                # Delsi pauza po kazde davce requestu   
                if api_request_count % API_BATCH_SIZE == 0:
                    logger.info(
                        "VUT role sync batch cooldown. "
                        "api_requests=%s, wait_seconds=%s",
                        api_request_count,
                        API_BATCH_DELAY,
                    )

                    await asyncio.sleep(API_BATCH_DELAY)

            # None znamena po uprave vut_api.py skutecne HTTP 404
            if details is None:
                expected_exstudent += 1

                current_roles = []

                if has_vut:
                    current_roles.append("VUT")

                if has_fp:
                    current_roles.append("FP")

                to_exstudent.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"VUT: {vut_ident} | "
                    f"{'+'.join(current_roles)} -> ExStudent"
                )

                continue

            if not isinstance(details, dict):
                api_errors.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"VUT: {vut_ident} | API vratilo neocekavany format"
                )
                continue

            target = classify_student(details)

            if target == "EXSTUDENT":
                expected_exstudent += 1

                current_roles = []

                if has_vut:
                    current_roles.append("VUT")

                if has_fp:
                    current_roles.append("FP")

                to_exstudent.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"VUT: {vut_ident} | "
                    f"{'+'.join(current_roles)} -> ExStudent"
                )

                continue

            # API osobu zna, ale studium neni bezpecne B/N
            if target == "UNSUPPORTED":
                unsupported.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"VUT: {vut_ident} | "
                    f"{relation_summary(details)}"
                )
                continue

            if target == "FP":
                expected_fp += 1

                if has_vut and has_fp:
                    both_to_fp.append(
                        f"{member} | Discord ID: {member.id} | "
                        f"VUT: {vut_ident} | VUT+FP -> FP"
                    )

                elif has_vut:
                    vut_to_fp.append(
                        f"{member} | Discord ID: {member.id} | "
                        f"VUT: {vut_ident} | VUT -> FP"
                    )

                else:
                    keep_fp.append(
                        f"{member} | Discord ID: {member.id} | "
                        f"VUT: {vut_ident}"
                    )

                continue

            if target == "VUT":
                expected_vut += 1

                if has_vut and has_fp:
                    both_to_vut.append(
                        f"{member} | Discord ID: {member.id} | "
                        f"VUT: {vut_ident} | VUT+FP -> VUT"
                    )

                elif has_fp:
                    fp_to_vut.append(
                        f"{member} | Discord ID: {member.id} | "
                        f"VUT: {vut_ident} | FP -> VUT"
                    )

                else:
                    keep_vut.append(
                        f"{member} | Discord ID: {member.id} | "
                        f"VUT: {vut_ident}"
                    )

        ignored_verified = len(verified_members) - len(target_members)

        summary = (
            "**VUT ROLE SYNC - DRY RUN**\n\n"

            f"Clenu serveru celkem: **{len(all_members)}**\n"
            f"Verified celkem: **{len(verified_members)}**\n"
            f"Verified bez FP/VUT role: **{ignored_verified}**\n\n"

            f"Kontrolovano FP/VUT uzivatelu: **{len(target_members)}**\n"
            f"Jen VUT: **{vut_only_count}**\n"
            f"Jen FP: **{fp_only_count}**\n"
            f"VUT + FP soucasne: **{both_count}**\n\n"

            "**Vysledek podle VUT API:**\n"
            f"Mel by mit FP: **{expected_fp}**\n"
            f"Mel by mit VUT: **{expected_vut}**\n"
            f"Mel by byt ExStudent: **{expected_exstudent}**\n\n"

            "**Zmeny, ktere by se provedly:**\n"
            f"VUT -> FP: **{len(vut_to_fp)}**\n"
            f"FP -> VUT: **{len(fp_to_vut)}**\n"
            f"VUT+FP -> FP: **{len(both_to_fp)}**\n"
            f"VUT+FP -> VUT: **{len(both_to_vut)}**\n"
            f"FP/VUT -> ExStudent: **{len(to_exstudent)}**\n\n"

            "**Beze zmeny:**\n"
            f"Spravne FP: **{len(keep_fp)}**\n"
            f"Spravne VUT: **{len(keep_vut)}**\n\n"

            "**Manualni kontrola:**\n"
            f"Nepodporovany typ studia: **{len(unsupported)}**\n"
            f"Chybi VUT ID v DB: **{len(missing_ident)}**\n"
            f"API chyby: **{len(api_errors)}**\n\n"

            "**DRY RUN - zadne role nebyly zmeneny.**"
        )

        await dm_channel.send(summary)

        # Konkretni lide, u kterych by se neco menilo
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

        await send_list(
            dm_channel,
            "FP -> VUT",
            fp_to_vut,
        )

        await send_list(
            dm_channel,
            "VUT+FP -> FP",
            both_to_fp,
        )

        await send_list(
            dm_channel,
            "VUT+FP -> VUT",
            both_to_vut,
        )

        await send_list(
            dm_channel,
            "FP/VUT -> ExStudent",
            to_exstudent,
        )

        # Tyto lidi nechceme automaticky menit
        await send_list(
            dm_channel,
            "MANUAL - nepodporovany typ studia",
            unsupported,
        )

        await send_list(
            dm_channel,
            "MANUAL - chybi VUT ID v databazi",
            missing_ident,
        )

        await send_list(
            dm_channel,
            "MANUAL - chyba VUT API",
            api_errors,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(VutRoleSync(bot))