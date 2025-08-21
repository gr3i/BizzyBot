import os
import re
from datetime import datetime, timedelta
import discord
from discord import app_commands
from discord.ext import commands

from db.session import SessionLocal
from db.models import Verification
from utils.codes import generate_verification_code
from utils.mailer import send_verification_mail

# regex: jen 4 povolene VUT formáty (x? + 6 cislic) @ (vut.cz|vutbr.cz)
VUT_PATTERN = re.compile(r"^(x?\d{6})@(vut\.cz|vutbr\.cz)$", re.IGNORECASE)

def extract_vut_code(email: str) -> str | None:
    m = VUT_PATTERN.match(email.strip().lower())
    if not m:
        return None
    return m.group(1)[-6:]  # 6 cifer

class Verify(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="verify", description="Zadej svuj e-mail pro overeni.")
    async def verify(self, inter: discord.Interaction, mail: str):
        user_id = inter.user.id
        code = generate_verification_code()
        mail_norm = mail.strip().lower()

        with SessionLocal() as s:
            # user uz je overen?
            existing_verified = (
                s.query(Verification)
                .filter(Verification.user_id == user_id, Verification.verified == True)
                .order_by(Verification.id.desc())
                .first()
            )
            if existing_verified:
                await inter.response.send_message(
                    "Uz jsi overen. Pokud potrebujes zmenu, kontaktuj moderatory.",
                    ephemeral=True
                )
                return

            # smazat me stare neoverene pokusy
            s.query(Verification).filter(
                Verification.user_id == user_id, Verification.verified == False
            ).delete(synchronize_session=False)

            # smazat globalne pokusy starsi 10 min
            cutoff = datetime.utcnow() - timedelta(minutes=10)
            s.query(Verification).filter(
                Verification.verified == False,
                Verification.created_at <= cutoff
            ).delete(synchronize_session=False)

            # kontrola VUT kodu: zabranit duplicitam napric 4 variantami
            vut6 = extract_vut_code(mail_norm)
            if vut6:
                variants = [f"{vut6}@vut.cz", f"x{vut6}@vut.cz", f"{vut6}@vutbr.cz", f"x{vut6}@vutbr.cz"]
                dup = (
                    s.query(Verification)
                    .filter(
                        Verification.verified == True,
                        Verification.user_id != user_id,
                        Verification.mail.in_(variants),
                    )
                    .first()
                )
                if dup:
                    await inter.response.send_message(
                        "Tento VUT kod (6 cifer) je jiz pouzit jinym uzivatelem.",
                        ephemeral=True
                    )
                    return
            else:
                # ne-VUT: stejny e-mail uz jiny overeny user?
                someone_else = (
                    s.query(Verification)
                    .filter(
                        Verification.mail == mail_norm,
                        Verification.verified == True,
                        Verification.user_id != user_id,
                    )
                    .first()
                )
                if someone_else:
                    await inter.response.send_message(
                        "Tento e-mail je jiz pouzit jinym uzivatelem.",
                        ephemeral=True
                    )
                    return

            # zalozit pokus
            s.add(Verification(user_id=user_id, mail=mail_norm, verification_code=code, verified=False))
            s.commit()

        try:
            send_verification_mail(mail_norm, code)
            await inter.response.send_message(
                f"Zadal jsi mail **{mail}**. Poslal jsem overovaci kod (podivej se i do SPAM).",
                ephemeral=True
            )
        except Exception as e:
            await inter.response.send_message(f"Chyba pri odeslani e-mailu: {e}", ephemeral=True)

    @app_commands.command(name="verify_code", description="Zadej overovaci kod.")
    async def verify_code(self, inter: discord.Interaction, code: str):
        user_id = inter.user.id

        with SessionLocal() as s:
            v = (
                s.query(Verification)
                .filter(Verification.user_id == user_id)
                .order_by(Verification.id.desc())
                .first()
            )
            if v is None:
                await inter.response.send_message("Nemas zadny neovereny kod. Pouzij /verify.", ephemeral=True)
                return
            if v.verified:
                await inter.response.send_message("Jiz jsi overen.", ephemeral=True)
                return
            if code != v.verification_code:
                await inter.response.send_message("Chybny kod. Zkus to znovu.", ephemeral=True)
                return

            mail_value = v.mail
            v.verified = True
            s.commit()

        # pridelit role
        guild = inter.guild
        verified_role = discord.utils.get(guild.roles, name="Verified") or await guild.create_role(name="Verified")
        await inter.user.add_roles(verified_role)

        specific = "VUT" if extract_vut_code(mail_value) else "Host"
        specific_role = discord.utils.get(guild.roles, name=specific) or await guild.create_role(name=specific)
        await inter.user.add_roles(specific_role)

        await inter.response.send_message(
            f"Overeni uspesne! Prideleny role: Verified + {specific}.",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Verify(bot))

