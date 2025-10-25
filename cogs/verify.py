# cogs/verify.py
import re
from datetime import datetime, timedelta
import asyncio

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import and_

from db.session import SessionLocal
from db.models import Verification
from utils.mailer import send_verification_mail
from utils.codes import generate_verification_code
from services.vut_api import InvalidApiKey, RateLimited


# allowed VUT formats only:
# 123456@vut.cz, x123456@vut.cz, 123456@vutbr.cz, x123456@vutbr.cz
VUT_PATTERN = re.compile(r"^(x?\d{6})@(vut\.cz|vutbr\.cz)$", re.IGNORECASE)

# allowed VUT FIT formats only:
VUT_FIT_PATTERN = re.compile(r"^x[a-z0-9]*\d{2}@vutbr\.cz", re.IGNORECASE)

def is_vut_student_email(email: str) -> bool:
    """Vrati True, pokud jde o VUT mail (klasicky 6-ciselny nebo x…00@vutbr.cz)."""
    e = email.strip().lower()
    return bool(VUT_PATTERN.match(e) or VUT_FIT_PATTERN.match(e))


def extract_vut_code(email: str) -> str | None:
    """Return 6-digit code if email matches allowed formats, else None."""
    m = VUT_PATTERN.match(email.strip().lower())
    if not m:
        return None
    return m.group(1)[-6:]  # last 6 digits


class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def _login_or_number_from_email(self, email: str) -> str | None:
        """Vrati login nebo 6mistne cislo z VUT mailu."""
        e = email.strip().lower()
        # 123456@vut.cz nebo 123456@vutbr.cz
        m = re.match(r"^(?P<num>\d{6})@(?:vut\.cz|vutbr\.cz)$", e)
        if m:
            return m.group("num")
        # xlogin00@vutbr.cz (FIT)
        m = re.match(r"^(?P<login>x[a-z0-9]*\d{2})@vutbr\.cz$", e)
        if m:
            return m.group("login")
        return None
    

    # If I will want instant per-guild availability, uncomment and set your guild ID:
    # @app_commands.guilds(discord.Object(id=123456789012345678))
    @app_commands.command(name="verify", description="Zadej svůj mail pro ověření.")
    async def verify(self, interaction: discord.Interaction, mail: str):

        await interaction.response.defer(ephemeral=True) # ack do 3s, at neexpiruje interaction token

        user_id = interaction.user.id

        # Overeni e-mailu ve VUT API
        user_id_for_api = self._login_or_number_from_email(mail)
        if not user_id_for_api:
            await interaction.followup.send(
                "Tento e-mail nevypadá jako platná VUT adresa (např. 123456@vut.cz nebo xlogin00@vutbr.cz).",
                ephemeral=True
            )
            return

        try:
            details = await self.bot.vut_api.get_user_details(user_id_for_api)
            # 👇 DEBUG výpis odpovědi z VUT API
            import json
            print(f"[VUT API] dotaz: {user_id_for_api}")
            print(f"[VUT API] status: OK, odpověď:")
            print(json.dumps(details, indent=2, ensure_ascii=False))
            
        except InvalidApiKey:
            await interaction.followup.send(
                "Interní chyba: neplatný VUT API klíč. Kontaktuj administrátora.",
                ephemeral=True
            )
            return
        except RateLimited:
            await interaction.followup.send(
                "VUT API je momentálně přetížené. Zkus to prosím za pár minut.",
                ephemeral=True
            )
            return
        except Exception as e:
            await interaction.followup.send(
                f"Chyba při komunikaci s VUT API: {e}",
                ephemeral=True
            )
            return

        if details is None:
            await interaction.followup.send(
                "Tento uživatel nebyl ve VUT systému nalezen. Zkontroluj e-mail nebo login.",
                ephemeral=True
            )
            return
        
        verification_code = generate_verification_code()
        mail_norm = mail.strip().lower()

        with SessionLocal() as session:
            # 0) already verified -> stop early
            existing_verified = (
                session.query(Verification)
                .filter(and_(Verification.user_id == user_id, Verification.verified == True))
                .order_by(Verification.id.desc())
                .first()
            )
            if existing_verified:
                await interaction.followup.send(
                    "Už jsi ověřen. Pokud potřebuješ změnu, kontaktuj moderátory.",
                    ephemeral=True
                )
                return

            # 1) delete this user's old unverified attempts
            session.query(Verification).filter(
                and_(Verification.user_id == user_id, Verification.verified == False)
            ).delete(synchronize_session=False)

            # 2) delete global unverified attempts older than 10 minutes
            cutoff = datetime.utcnow() - timedelta(minutes=10)
            session.query(Verification).filter(
                and_(Verification.verified == False, Verification.created_at <= cutoff)
            ).delete(synchronize_session=False)

            # 3a) allowed VUT formats -> block duplicates by 6-digit code across 4 variants
            code6 = extract_vut_code(mail_norm)
            if code6:
                group_emails = [
                    f"{code6}@vut.cz",
                    f"x{code6}@vut.cz",
                    f"{code6}@vutbr.cz",
                    f"x{code6}@vutbr.cz",
                ]
                dup = (
                    session.query(Verification)
                    .filter(
                        and_(
                            Verification.verified == True,
                            Verification.user_id != user_id,
                            Verification.mail.in_(group_emails),
                        )
                    )
                    .first()
                )
                if dup:
                    await interaction.followup.send(
                        "Tento VUT kód (6 číslic) už je použit jiným uživatelem. Kontaktuj moderátory, pokud jde o omyl.",
                        ephemeral=True
                    )
                    return
            else:
                # 3b) non-VUT formats -> exact email must not be verified by someone else
                existing = (
                    session.query(Verification)
                    .filter(
                        and_(
                            Verification.mail == mail_norm,
                            Verification.verified == True,
                            Verification.user_id != user_id,
                        )
                    )
                    .first()
                )
                if existing:
                    await interaction.followup.send(
                        "Tento e-mail je již použit jiným uživatelem a nelze ho znovu ověřit.",
                        ephemeral=True
                    )
                    return

            # 4) create new verification attempt
            v = Verification(
                user_id=user_id,
                mail=mail_norm,
                verification_code=verification_code,
                verified=False
            )
            session.add(v)
            session.commit()

        # 5) send mail (outside session), sync SMTP spustime mimo event loop + timeout
        try:
            await asyncio.wait_for(
                asyncio.to_thread(send_verification_mail, mail_norm, verification_code),
                timeout=15
            )
            await interaction.followup.send(
                f"Zadal jsi mail {mail}. Ověřovací kód byl odeslán na tvůj mail. (zkontroluj si SPAM)",
                ephemeral=True
            )
        except asyncio.TimeoutError:
            await interaction.followup.send(
                "Odesílání e-mailu trvalo příliš dlouho. Zkus to prosím znovu.",
                ephemeral=True
            )
        except OSError as e:
            # typicky: [Errno 101] Network unreachable / blokovany SMTP port
            await interaction.followup.send(
                f"Nelze se připojit k poštovnímu serveru ({e}). Zkus to později.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"Došlo k chybě při odesílání mailu: {e}",
                ephemeral=True
            ) 

    # If I want instant per-guild availability, uncomment and set your guild ID:
    # @app_commands.guilds(discord.Object(id=123456789012345678))
    @app_commands.command(name="verify_code", description="Zadej ověřovací kód.")
    async def verify_code(self, interaction: discord.Interaction, code: str):

        await interaction.response.defer(ephemeral=True) 

        user_id = interaction.user.id

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

            # cache mail before closing session
            mail_value = v.mail
            v.verified = True
            session.commit()

        # assign roles after session is closed
        guild = interaction.guild

        verified_role = discord.utils.get(guild.roles, name="Verified")
        if not verified_role:
            verified_role = await guild.create_role(name="Verified")
        await interaction.user.add_roles(verified_role)

        # VUT only for allowed formats; otherwise Host
        if is_vut_student_email(mail_value):
            specific_role_name = "VUT"
        else:
            specific_role_name = "Host"

        specific_role = discord.utils.get(guild.roles, name=specific_role_name)
        if not specific_role:
            specific_role = await guild.create_role(name=specific_role_name)
        await interaction.user.add_roles(specific_role)

        await interaction.followup.send(
            f"Ověření bylo úspěšné! Byly ti přidělené role 'Verified' a '{specific_role_name}'.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Verify(bot))


