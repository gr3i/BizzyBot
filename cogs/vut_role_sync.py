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


async def apply_member_target_role(
    member: discord.Member,
    target: str,
    vut_role: discord.Role,
    fp_role: discord.Role,
    exstudent_role: discord.Role,
):
    """
    Nastavi cilovou VUT/FP/ExStudent roli.
    Cilovou roli pridame jako prvni a stare role odebereme az potom.
    """

    reason = "VUT role sync"

    if target == "FP":
        if fp_role not in member.roles:
            await member.add_roles(
                fp_role,
                reason=reason,
            )

        roles_to_remove = []

        if vut_role in member.roles:
            roles_to_remove.append(vut_role)

        if exstudent_role in member.roles:
            roles_to_remove.append(exstudent_role)

        if roles_to_remove:
            await member.remove_roles(
                *roles_to_remove,
                reason=reason,
            )

        return

    if target == "VUT":
        if vut_role not in member.roles:
            await member.add_roles(
                vut_role,
                reason=reason,
            )

        roles_to_remove = []

        if fp_role in member.roles:
            roles_to_remove.append(fp_role)

        if exstudent_role in member.roles:
            roles_to_remove.append(exstudent_role)

        if roles_to_remove:
            await member.remove_roles(
                *roles_to_remove,
                reason=reason,
            )

        return

    if target == "EXSTUDENT":
        if exstudent_role not in member.roles:
            await member.add_roles(
                exstudent_role,
                reason=reason,
            )

        roles_to_remove = []

        if vut_role in member.roles:
            roles_to_remove.append(vut_role)

        if fp_role in member.roles:
            roles_to_remove.append(fp_role)

        if roles_to_remove:
            await member.remove_roles(
                *roles_to_remove,
                reason=reason,
            )

        return

    raise ValueError(f"Neznamy target: {target}")

class VutRoleSync(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="vut_role_dry_run",
        description="Dry run kontroly VUT, FP a ExStudent roli.",
    )

    @app_commands.command(
        name="vut_role_apply",
        description="OSTRY sync VUT, FP a ExStudent roli.",
    )
    @app_commands.guild_only()
    async def vut_role_apply(
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

        # Interaction vyuzijeme pouze na okamzite potvrzeni.
        # Vysledek pujde do DM, protoze cely sync muze trvat dlouho.
        await interaction.response.send_message(
            "VUT role sync byl spusten naostro.\n"
            "Prubeh uvidis v konzoli a vysledek ti poslu do DM.",
            ephemeral=True,
        )

        guild = interaction.guild

        if guild is None:
            return

        # Nez zacneme menit role, musime mit funkcni DM.
        try:
            dm_channel = await interaction.user.create_dm()

            await dm_channel.send(
                "**VUT ROLE SYNC - REAL RUN STARTED**\n\n"
                "Sync byl spusten. Role se nyni opravdu meni."
            )

        except discord.HTTPException as error:
            logger.exception(
                "Could not create DM for VUT role sync. error=%s",
                error,
            )
            return

        # Ujistime se, ze mame nactene vsechny cleny
        if not guild.chunked:
            try:
                await guild.chunk(cache=True)

            except Exception as error:
                await dm_channel.send(
                    "Sync byl ukoncen.\n"
                    f"Nepodarilo se nacist vsechny cleny serveru: `{error}`"
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
            await dm_channel.send(
                "Sync byl ukoncen.\n"
                "Na serveru chybi role: "
                + ", ".join(missing_roles)
            )
            return

        # Pred ostrym runem overime prava bota
        bot_member = guild.me

        if bot_member is None:
            await dm_channel.send(
                "Sync byl ukoncen. Nepodarilo se najit bota na serveru."
            )
            return

        if not bot_member.guild_permissions.manage_roles:
            await dm_channel.send(
                "Sync byl ukoncen. Bot nema Manage Roles permission."
            )
            return

        unmanageable_roles = [
            role.name
            for role in (vut_role, fp_role, exstudent_role)
            if role >= bot_member.top_role
        ]

        if unmanageable_roles:
            await dm_channel.send(
                "Sync byl ukoncen. Bot nema dostatecne vysokou roli pro: "
                + ", ".join(unmanageable_roles)
            )
            return

        all_members = list(guild.members)

        verified_members = [
            member
            for member in all_members
            if verified_role in member.roles
        ]

        # Stejne jako dry run kontrolujeme jen lidi s VUT nebo FP
        target_members = [
            member
            for member in verified_members
            if vut_role in member.roles or fp_role in member.roles
        ]

        vut_idents = load_verified_vut_idents()

        # Najdeme duplicitni VUT ID.
        # Pouze je zalogujeme, sync je dale normalne zpracuje.
        ident_members: dict[str, list[discord.Member]] = {}

        for member in target_members:
            vut_ident = vut_idents.get(member.id)

            if not vut_ident:
                continue

            ident_members.setdefault(
                vut_ident,
                [],
            ).append(member)

        duplicate_idents = {
            vut_ident: members
            for vut_ident, members in ident_members.items()
            if len(members) > 1
        }

        for vut_ident, members in duplicate_idents.items():
            members_text = ", ".join(
                f"{member} ({member.id})"
                for member in members
            )

            logger.warning(
                "DUPLICATE VUT IDENT during REAL role sync. "
                "vut_ident=%s, users=%s",
                vut_ident,
                members_text,
            )

        # Vysledky skutecnych zmen
        vut_to_fp = []
        fp_to_vut = []

        both_to_fp = []
        both_to_vut = []

        to_exstudent = []

        keep_fp = []
        keep_vut = []

        unsupported = []
        missing_ident = []
        api_errors = []
        role_errors = []

        processed_with_api = 0

        total_members = len(target_members)

        logger.info(
            "VUT REAL role sync started. total_users=%s",
            total_members,
        )

        for index, member in enumerate(target_members, start=1):
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
                    "VUT REAL role sync progress: "
                    "%s/%s users processed (%.1f%%)",
                    index,
                    total_members,
                    progress,
                )

            has_vut = vut_role in member.roles
            has_fp = fp_role in member.roles

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
                    "VUT REAL role sync API error. "
                    "discord_id=%s, vut_ident=%s, error=%s",
                    member.id,
                    vut_ident,
                    error,
                )

                continue

            except Exception as error:
                logger.exception(
                    "Unexpected VUT API error during REAL role sync. "
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

                # Stejna davkova pauza jako v dry runu
                if (
                    processed_with_api > 0
                    and processed_with_api % API_BATCH_SIZE == 0
                ):
                    logger.info(
                        "VUT REAL role sync batch cooldown. "
                        "api_requests=%s, wait_seconds=%s",
                        processed_with_api,
                        API_BATCH_DELAY,
                    )

                    await asyncio.sleep(API_BATCH_DELAY)

            # 404 znamena ExStudent
            if details is None:
                target = "EXSTUDENT"

            elif not isinstance(details, dict):
                api_errors.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"VUT: {vut_ident} | "
                    "API vratilo neocekavany format"
                )
                continue

            else:
                target = classify_student(details)

            # Nestandardni vztah nechame bez zmeny
            if target == "UNSUPPORTED":
                unsupported.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"VUT: {vut_ident} | "
                    f"{relation_summary(details)}"
                )
                continue

            # Zapamatujeme si puvodni stav pred zmenou
            original_has_vut = has_vut
            original_has_fp = has_fp

            try:
                await apply_member_target_role(
                    member,
                    target,
                    vut_role,
                    fp_role,
                    exstudent_role,
                )

            except (discord.Forbidden, discord.HTTPException) as error:
                logger.exception(
                    "Discord role change failed during REAL sync. "
                    "discord_id=%s, vut_ident=%s, target=%s",
                    member.id,
                    vut_ident,
                    target,
                )

                role_errors.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"VUT: {vut_ident} | target: {target} | "
                    f"{type(error).__name__}: {error}"
                )

                continue

            except Exception as error:
                logger.exception(
                    "Unexpected role change error during REAL sync. "
                    "discord_id=%s, vut_ident=%s, target=%s",
                    member.id,
                    vut_ident,
                    target,
                )

                role_errors.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"VUT: {vut_ident} | target: {target} | "
                    f"{type(error).__name__}: {error}"
                )

                continue

            # Zapiseme, co jsme realne udelali
            if target == "EXSTUDENT":
                to_exstudent.append(
                    f"{member} | Discord ID: {member.id} | "
                    f"VUT: {vut_ident} | "
                    f"{'VUT' if original_has_vut else ''}"
                    f"{'+' if original_has_vut and original_has_fp else ''}"
                    f"{'FP' if original_has_fp else ''}"
                    " -> ExStudent"
                )

                logger.info(
                    "VUT REAL role change: discord_id=%s, "
                    "vut_ident=%s, target=ExStudent",
                    member.id,
                    vut_ident,
                )

                continue

            if target == "FP":
                if original_has_vut and original_has_fp:
                    both_to_fp.append(
                        f"{member} | Discord ID: {member.id} | "
                        f"VUT: {vut_ident} | VUT+FP -> FP"
                    )

                elif original_has_vut:
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
                if original_has_vut and original_has_fp:
                    both_to_vut.append(
                        f"{member} | Discord ID: {member.id} | "
                        f"VUT: {vut_ident} | VUT+FP -> VUT"
                    )

                elif original_has_fp:
                    fp_to_vut.append(
                        f"{member} | Discord ID: {member.id} | "
                        f"VUT: {vut_ident} | FP -> VUT"
                    )

                else:
                    keep_vut.append(
                        f"{member} | Discord ID: {member.id} | "
                        f"VUT: {vut_ident}"
                    )

        duplicate_lines = []

        for vut_ident, members in duplicate_idents.items():
            users = ", ".join(
                f"{member} ({member.id})"
                for member in members
            )

            duplicate_lines.append(
                f"VUT: {vut_ident} | {users}"
            )

        summary = (
            "**VUT ROLE SYNC - REAL RUN HOTOVO**\n\n"

            f"Kontrolovano uzivatelu: **{total_members}**\n\n"

            "**Provedene zmeny:**\n"
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
            f"API chyby: **{len(api_errors)}**\n"
            f"Discord role chyby: **{len(role_errors)}**\n"
            f"Duplicitni VUT ID: **{len(duplicate_idents)}**\n\n"

            "**REAL RUN - role byly skutecne zmeneny.**"
        )

        await dm_channel.send(summary)

        await send_list(
            dm_channel,
            "VUT -> FP",
            vut_to_fp,
        )

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

        await send_list(
            dm_channel,
            "MANUAL - Discord role chyba",
            role_errors,
        )

        await send_list(
            dm_channel,
            "MANUAL - duplicitni VUT ID",
            duplicate_lines,
        )

        logger.info(
            "VUT REAL role sync finished. "
            "users=%s, vut_to_fp=%s, fp_to_vut=%s, "
            "to_exstudent=%s, unsupported=%s, missing_ident=%s, "
            "api_errors=%s, role_errors=%s, duplicate_idents=%s",
            total_members,
            len(vut_to_fp),
            len(fp_to_vut),
            len(to_exstudent),
            len(unsupported),
            len(missing_ident),
            len(api_errors),
            len(role_errors),
            len(duplicate_idents),
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