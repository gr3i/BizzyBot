from datetime import datetime, timedelta
import asyncio
import os

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import and_

from db.session import SessionLocal
from db.models import Verification
from utils.mailer import send_verification_mail
from utils.codes import generate_verification_code


# ROLE IDs
ROLE_HOST_ID = 1358905374500982995
ROLE_VUT_ID = 1358911329737642014
ROLE_VUT_STAFF_ID = 1431724268160549096
ROLE_DOKTORAND_ID = 1433984072266285097
ROLE_FP_ID = 1466036385017233636

# FP year roles (based on rok_studia + typ_studia.zkratka)
FP_B_1 = 1469298142959898840
FP_B_2 = 1469298381200293963
FP_B_3P = 1469298468399878145

FP_N_1 = 1469298670066204702
FP_N_2P = 1469298920562757785

FP_YEAR_ROLE_IDS = {FP_B_1, FP_B_2, FP_B_3P, FP_N_1, FP_N_2P}


# HELPERS 
def extract_fp_study_info(details: dict):
    """
    Returns (rok_studia, typ_studia_zkratka) from vztahy for FP Student.
    If multiple matches, picks highest rok_studia.
    """
    vztahy = details.get("vztahy") or []
    candidates = []

    for vztah in vztahy:
        fak = ((vztah.get("fakulta") or {}).get("zkratka") or "").strip().upper()
        pozice = (vztah.get("pozice") or "").strip().lower()
        if fak != "FP" or pozice != "student":
            continue

        rok = vztah.get("rok_studia")
        typ = ((vztah.get("typ_studia") or {}).get("zkratka") or "").strip().upper()

        if isinstance(rok, int) and typ:
            candidates.append((rok, typ))

    if not candidates:
        return None, None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0]


def pick_fp_year_role_id(rok: int, typ: str):
    """
    Mapping requested:
      - 1 + B -> FP_B_1
      - 2 + B -> FP_B_2
      - >=3 + B -> FP_B_3P
      - 1 + N -> FP_N_1
      - >=2 + N -> FP_N_2P
    """
    typ = (typ or "").strip().upper()

    if typ == "B":
        if rok <= 1:
            return FP_B_1
        if rok == 2:
            return FP_B_2
        return FP_B_3P

    if typ == "N":
        if rok <= 1:
            return FP_N_1
        return FP_N_2P

    return None


class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    verify = app_commands.Group(
        name="verify",
        description="Ověření uživatele"
    )

    @verify.command(name="vut", description="Zadej své VUT ID (6 číslic) nebo login (např. xlogin00).")
    @app_commands.describe(id_login="VUT ID nebo login (např. 123456 nebo xlogin00)")
    async def verify_vut(self, interaction: discord.Interaction, id_login: str):
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        ident_norm = id_login.strip().lower()
        verification_code = generate_verification_code()

        # 1) call VUT API
        try:
            details = await self.bot.vut_api.get_user_details(ident_norm)
        except Exception as e:
            await interaction.followup.send(f"Chyba při komunikaci s VUT API: {e}", ephemeral=True)
            return

        if not details:
            await interaction.followup.send(
                "Tento identifikátor (ID/login) nebyl ve VUT systému nalezen.",
                ephemeral=True
            )
            return

        emails_api = [e.strip().lower() for e in (details.get("emaily") or [])]
        if not emails_api:
            await interaction.followup.send(
                "K tomuto VUT účtu nejsou v API uvedené žádné e-maily.",
                ephemeral=True
            )
            return

        # preferuj studentsky email (@stud.*), jinak fallback na prvni
        target_email = None
        for e in emails_api:
            if "@stud." in e:
                target_email = e
                break
        if target_email is None:
            target_email = emails_api[0]

        print(f"[VERIFY] Sending verification mail to: {target_email}")

        with SessionLocal() as session:
            # 2) if ident already verified by someone else -> stop
            dup = (
                session.query(Verification)
                .filter(
                    and_(
                        Verification.verified == True,
                        Verification.user_id != user_id,
                        Verification.mail.endswith(f"||{ident_norm}"),
                    )
                )
                .first()
            )
            if dup:
                await interaction.followup.send(
                    "Tento identifikátor (ID/login) už je ověřen jiným uživatelem.",
                    ephemeral=True
                )
                return

            # delete old unverified attempts of this user
            session.query(Verification).filter(
                and_(Verification.user_id == user_id, Verification.verified == False)
            ).delete(synchronize_session=False)

            # store "mail||ident" (no extra data)
            stored_value = f"{target_email}||{ident_norm}"
            v = Verification(
                user_id=user_id,
                mail=stored_value,
                verification_code=verification_code,
                verified=False
            )
            session.add(v)
            session.commit()

        # 3) send code
        try:
            await asyncio.wait_for(
                asyncio.to_thread(send_verification_mail, target_email, verification_code),
                timeout=15
            )
            masked = target_email[:3] + "…" + target_email.split("@")[-1]
            await interaction.followup.send(
                f"Ověřovací kód byl odeslán na **{masked}**. (Zkontroluj i složku SPAM.)",
                ephemeral=True
            )
        except asyncio.TimeoutError:
            await interaction.followup.send(
                "Odesílání e-mailu trvalo příliš dlouho. Zkus to prosím znovu.",
                ephemeral=True
            )
        except OSError as e:
            await interaction.followup.send(
                f"Nelze se připojit k poštovnímu serveru ({e}). Zkus to později.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"Došlo k chybě při odesílání mailu: {e}",
                ephemeral=True
            )

    @verify.command(name="host", description="Ověření e-mailem pro hosty (mimo VUT).")
    @app_commands.describe(mail="E-mail, kam poslat ověřovací kód.")
    async def verify_host(self, interaction: discord.Interaction, mail: str):
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        mail_norm = mail.strip().lower()
        verification_code = generate_verification_code()

        with SessionLocal() as session:
            dup = (
                session.query(Verification)
                .filter(
                    and_(
                        Verification.verified == True,
                        Verification.user_id != user_id,
                        (Verification.mail == mail_norm) | (Verification.mail.like(f"{mail_norm}||%")),
                    )
                )
                .first()
            )
            if dup:
                await interaction.followup.send(
                    "Tento e-mail je již použit jiným ověřeným uživatelem.",
                    ephemeral=True
                )
                return

            session.query(Verification).filter(
                and_(Verification.user_id == user_id, Verification.verified == False)
            ).delete(synchronize_session=False)

            v = Verification(
                user_id=user_id,
                mail=mail_norm,
                verification_code=verification_code,
                verified=False
            )
            session.add(v)
            session.commit()

        try:
            await asyncio.wait_for(
                asyncio.to_thread(send_verification_mail, mail_norm, verification_code),
                timeout=15
            )
            masked = mail_norm[:3] + "…" + mail_norm.split("@")[-1]
            await interaction.followup.send(
                f"Ověřovací kód byl odeslán na **{masked}**. (Zkontroluj i složku SPAM.)",
                ephemeral=True
            )
        except asyncio.TimeoutError:
            await interaction.followup.send(
                "Odesílání e-mailu trvalo příliš dlouho. Zkus to prosím znovu.",
                ephemeral=True
            )
        except OSError as e:
            await interaction.followup.send(
                f"Nelze se připojit k poštovnímu serveru ({e}). Zkus to později.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"Došlo k chybě při odesílání mailu: {e}",
                ephemeral=True
            )

    @verify.command(name="code", description="Zadej ověřovací kód.")
    async def verify_code(self, interaction: discord.Interaction, code: str):
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        specific_role_id = None

        with SessionLocal() as session:
            v = (
                session.query(Verification)
                .filter(Verification.user_id == user_id)
                .order_by(Verification.id.desc())
                .first()
            )

            if v is None:
                await interaction.followup.send(
                    "Nemáš žádný neověřený kód. Použij příkaz /verify pro získání kódu.",
                    ephemeral=True
                )
                return

            if v.verified:
                await interaction.followup.send("Již jsi ověřen.", ephemeral=True)
                return

            if code != v.verification_code:
                await interaction.followup.send("Chybný kód. Zkus to znovu.", ephemeral=True)
                return

            ver_id = v.id
            stored_value = v.mail  # "mail||ident" OR just "mail"

        parts = stored_value.split("||", 1)
        mail_value = parts[0].strip().lower()
        ident_value = parts[1].strip().lower() if len(parts) == 2 else None

        # runtime only
        fp_year_role_id = None

        if ident_value:
            try:
                details = await self.bot.vut_api.get_user_details(ident_value)
                if details:
                    emails_api = [e.strip().lower() for e in (details.get("emaily") or [])]
                    vztahy = details.get("vztahy") or []

                    if mail_value in emails_api and vztahy:
                        typy_studia = set()
                        fakulty = set()

                        for vztah in vztahy:
                            typ_studia_info = vztah.get("typ_studia") or {}
                            zkratka_typu = (typ_studia_info.get("zkratka") or "").strip().upper()
                            if zkratka_typu:
                                typy_studia.add(zkratka_typu)

                            fakulta_info = vztah.get("fakulta") or {}
                            fak_zkr = (fakulta_info.get("zkratka") or "").strip().upper()
                            if fak_zkr:
                                fakulty.add(fak_zkr)

                        # Decide identity role
                        if "D" in typy_studia:
                            specific_role_id = ROLE_DOKTORAND_ID

                        elif typy_studia.issubset({"B", "N", "C4"}):
                            if "FP" in fakulty:
                                specific_role_id = ROLE_FP_ID

                                rok, typ = extract_fp_study_info(details)
                                if rok is not None and typ is not None:
                                    fp_year_role_id = pick_fp_year_role_id(rok, typ)

                            else:
                                specific_role_id = ROLE_VUT_ID

                        else:
                            specific_role_id = ROLE_VUT_STAFF_ID

            except Exception as e:
                print(f"[VUT API] Chyba při ověřování role: {e}")

        if specific_role_id is None:
            specific_role_id = ROLE_HOST_ID

        trust_roles_priority = {
            ROLE_HOST_ID: 0,
            ROLE_VUT_ID: 1,
            ROLE_FP_ID: 1,
            ROLE_VUT_STAFF_ID: 2,
            ROLE_DOKTORAND_ID: 3,
        }

        guild = interaction.guild

        verified_role = discord.utils.get(guild.roles, name="Verified")
        if not verified_role:
            verified_role = await guild.create_role(name="Verified")

        if verified_role not in interaction.user.roles:
            await interaction.user.add_roles(verified_role)

        current_trust_roles = [r for r in interaction.user.roles if r.id in trust_roles_priority]

        current_best_role = None
        current_best_priority = -1
        for r in current_trust_roles:
            prio = trust_roles_priority[r.id]
            if prio > current_best_priority:
                current_best_priority = prio
                current_best_role = r

        new_role_priority = trust_roles_priority[specific_role_id]

        if current_best_role is not None:
            if current_best_priority >= new_role_priority:
                with SessionLocal() as session:
                    rec = session.get(Verification, ver_id)
                    if rec and not rec.verified:
                        session.delete(rec)
                        session.commit()

                await interaction.followup.send(
                    f"Ověření bylo úspěšné. Tvá role zůstává '{current_best_role.name}' (vyšší nebo stejná úroveň důvěry).",
                    ephemeral=True
                )
                return
            else:
                await interaction.user.remove_roles(*current_trust_roles)

        specific_role = guild.get_role(specific_role_id)
        if specific_role is None:
            await interaction.followup.send(
                "Chyba: cílová role na serveru neexistuje (špatné ROLE_ID nebo role byla smazána).",
                ephemeral=True
            )
            return

        if specific_role not in interaction.user.roles:
            await interaction.user.add_roles(specific_role)

        # Add FP year role (runtime decision only)
        if specific_role_id == ROLE_FP_ID and fp_year_role_id:
            year_role = guild.get_role(fp_year_role_id)
            if year_role:
                # remove other FP year roles so user has only one
                to_remove = [r for r in interaction.user.roles if r.id in FP_YEAR_ROLE_IDS and r.id != fp_year_role_id]
                if to_remove:
                    await interaction.user.remove_roles(*to_remove)

                if year_role not in interaction.user.roles:
                    await interaction.user.add_roles(year_role)

        with SessionLocal() as session:
            rec = session.get(Verification, ver_id)
            if rec:
                rec.verified = True
                (
                    session.query(Verification)
                    .filter(
                        Verification.user_id == user_id,
                        Verification.id != ver_id
                    )
                    .delete(synchronize_session=False)
                )
                session.commit()

        role_name = specific_role.name if specific_role else "neznamou roli"
        extra = ""
        if specific_role_id == ROLE_FP_ID and fp_year_role_id:
            yr = guild.get_role(fp_year_role_id)
            if yr:
                extra = f" a také '{yr.name}'"

        await interaction.followup.send(
            f"Ověření bylo úspěšné! Byly ti přidělené role 'Verified' a '{role_name}'{extra}.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Verify(bot))

    GUILD_ID = int(os.getenv("GUILD_ID", "0"))
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.add_command(Verify.verify, guild=guild)
        print(f"[verify] group 'verify' registered for guild {GUILD_ID}")
    else:
        bot.tree.add_command(Verify.verify)
        print("[verify] group 'verify' registered (global)")
