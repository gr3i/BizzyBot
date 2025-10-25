# cogs/verify.py
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

    @app_commands.command(name="verify", description="Zadej své VUT ID (6 číslic) nebo login (např. xlogin00).")
    @app_commands.describe(id_login="VUT ID nebo login (např. 256465 nebo xlogin00)")
    async def verify(self, interaction: discord.Interaction, id_login: str):
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        ident_norm = id_login.strip().lower()
        verification_code = generate_verification_code()

        # 1) zavolej VUT API
        try:
            details = await self.bot.vut_api.get_user_details(ident_norm)
        except Exception as e:
            await interaction.followup.send(f"Chyba při komunikaci s VUT API: {e}", ephemeral=True)
            return

        if not details:
            await interaction.followup.send("Tento identifikátor (ID/login) nebyl ve VUT systému nalezen.", ephemeral=True)
            return

        emails_api = [e.strip().lower() for e in (details.get("emaily") or [])]
        if not emails_api:
            await interaction.followup.send("K tomuto VUT účtu nejsou v API uvedené žádné e-maily.", ephemeral=True)
            return

        # beru prvni e-mail z API
        target_email = emails_api[0]

        with SessionLocal() as session:
            # 2) kdyz uz je tento ident overen jinym uzivatelem, tak stop
            dup = (
                session.query(Verification)
                .filter(
                    and_(
                        Verification.verified == True,
                        Verification.user_id != user_id,
                        (Verification.mail == ident_norm) | (Verification.mail.like(f"%||{ident_norm}")),
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

            # zahod stare neoverene pokusy tehoz uzivatele
            session.query(Verification).filter(
                and_(Verification.user_id == user_id, Verification.verified == False)
            ).delete(synchronize_session=False)

            # vytvor pokus a uloz KOMBINACI "mail||ident"
            stored_value = f"{target_email}||{ident_norm}"
            v = Verification(
                user_id=user_id,
                mail=stored_value,
                verification_code=verification_code,
                verified=False
            )
            session.add(v)
            session.commit()

        # 3) posli kod na target_email
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
            await interaction.followup.send("Odesílání e-mailu trvalo příliš dlouho. Zkus to prosím znovu.", ephemeral=True)
        except OSError as e:
            await interaction.followup.send(f"Nelze se připojit k poštovnímu serveru ({e}). Zkus to později.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Došlo k chybě při odesílání mailu: {e}", ephemeral=True)
    
    @app_commands.command(name="verify_host", description="Ověření e-mailem pro hosty (mimo VUT).")
    @app_commands.describe(mail="E-mail, kam poslat ověřovací kód.")
    async def verify_host(self, interaction: discord.Interaction, mail: str):
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        mail_norm = mail.strip().lower()
        verification_code = generate_verification_code()

        with SessionLocal() as session:
            # blokuj duplicitni e-mail overeny jinym uzivatelem
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

            # zahod stare neoverene pokusy tehoz uzivatele
            session.query(Verification).filter(
                and_(Verification.user_id == user_id, Verification.verified == False)
            ).delete(synchronize_session=False)

            # uloz jen mail (bez ident), pozdeji se z toho pozna, ze je to HOST
            v = Verification(
                user_id=user_id,
                mail=mail_norm,
                verification_code=verification_code,
                verified=False
            )
            session.add(v)
            session.commit()

        # posli kod
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
            await interaction.followup.send("Odesílání e-mailu trvalo příliš dlouho. Zkus to prosím znovu.", ephemeral=True)
        except OSError as e:
            await interaction.followup.send(f"Nelze se připojit k poštovnímu serveru ({e}). Zkus to později.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Došlo k chybě při odesílání mailu: {e}", ephemeral=True)
        

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

            # rozbal MAIL a IDENT (zpetne kompatibilni se starsimi zaznamy)
            parts = stored_value.split("||", 1)
            mail_value = parts[0].strip().lower()
            ident_value = parts[1].strip().lower() if len(parts) == 2 else None
                
            

        # assign roles after session is closed
        guild = interaction.guild

        verified_role = discord.utils.get(guild.roles, name="Verified")
        if not verified_role:
            verified_role = await guild.create_role(name="Verified")
        await interaction.user.add_roles(verified_role)

        # rozhodnuti o roli
        specific_role_name = "Host"  # default

        if ident_value:
            try:
                details = await self.bot.vut_api.get_user_details(ident_value)
                if details:
                    emails_api = [e.strip().lower() for e in (details.get("emaily") or [])]
                    vztahy = details.get("vztahy") or []

                    if mail_value in emails_api:
                        # Podle "pozice" z API urcim, jestli je student nebo zamestnanec
                        pozice = vztahy[0].get("pozice") if vztahy else None
                        if pozice and pozice.lower() == "student":
                            specific_role_name = "VUT"
                        else:
                            specific_role_name = "VUT Staff"
            except Exception as e:
                # Pokud API selze, necham Host, ale vypisu do logu
                print(f"[VUT API] Chyba při ověřování role: {e}")
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



