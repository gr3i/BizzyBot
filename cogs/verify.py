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





class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
    

    # If I will want instant per-guild availability, uncomment and set your guild ID:
    # @app_commands.guilds(discord.Object(id=123456789012345678))
    # změna signatury (mail povinný, ident volitelný)
    @app_commands.command(name="verify", description="Zadej svůj e-mail a (pokud jsi z VUT) i VUT ID/login.")
    async def verify(self, interaction: discord.Interaction, mail: str, vut_id_login: str | None = None):
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        mail_norm = mail.strip().lower()
        ident_norm = vut_id_login.strip().lower() if vut_id_login else None
        verification_code = generate_verification_code() 
        

        with SessionLocal() as session:
            # 0) already verified, stop early
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

            # 3) blokace duplicit, kdyz je ident, nesmi byt overeny jinym uzivatelem
            if ident_norm:
                dup = (
                    session.query(Verification)
                    .filter(
                        and_(
                            Verification.verified == True,
                            Verification.user_id != user_id,
                            # bud nekdo drive ulozil mail||ident, nebo jen ident (pro pripad starsich zaznamu)
                            (Verification.mail == ident_norm) | (Verification.mail.like(f"%||{ident_norm}"))
                        )
                    )
                    .first()
                )
                if dup:
                    await interaction.followup.send(
                        "Tento identifikátor ( VUT ID/login) už je ověřen jiným uživatelem. Pokud jde o omyl, kontaktuj moderátory.",
                        ephemeral=True
                    )
                    return
           


            stored_value = f"{mail_norm}||{ident_norm}" if ident_norm else mail_norm

            # 4) create new verification attempt
            v = Verification(
                user_id=user_id,
                mail=stored_value,
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
                f"Ověřovací kód byl odeslán na adresu **{mail_norm}**. (Zkontroluj i složku SPAM)",
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

            stored_value = v.mail  # v DB je "mail||ident" nebo jen "mail"

            # rozbal MAIL a IDENT (zpětně kompatibilní se staršími záznamy)
            parts = stored_value.split("||", 1)
            mail_value = parts[0].strip().lower()
            ident_value = parts[1].strip().lower() if len(parts) == 2 else None
                
            

        # assign roles after session is closed
        guild = interaction.guild

        verified_role = discord.utils.get(guild.roles, name="Verified")
        if not verified_role:
            verified_role = await guild.create_role(name="Verified")
        await interaction.user.add_roles(verified_role)

        # VUT only for allowed formats; otherwise Host
        # Rozhodnuti o roli: pokud je to VUT-format, zkusim potvrdit pres VUT API,
        # jinak rovnou Host.
        specific_role_name = "Host"  # default

        # pokud mame identifikator, over pres VUT API a porovnej, zda mail patri mezi "emaily"
        if ident_value:
            try:
                details = await self.bot.vut_api.get_user_details(ident_value)
                if details:
                    emails_api = [e.strip().lower() for e in (details.get("emaily") or [])]
                    if mail_value in emails_api:
                        specific_role_name = "VUT"
            except Exception:
                # kdyz API spadne nebo limit, nepokazime verifikaci – nechame Host
                pass 
       
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


