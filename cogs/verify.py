# cogs/verify.py
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





class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 


    # If I will want instant per-guild availability, uncomment and set your guild ID:
    # @app_commands.guilds(discord.Object(id=123456789012345678))


    verify = app_commands.Group(
        name="verify",
        description="Ověření uživatele"
    )

    @verify.command(name="vut", description="Zadej své VUT ID (6 číslic) nebo login (např. xlogin00).")
    #@app_commands.guild_only()
    @app_commands.describe(id_login="VUT ID nebo login (např. 123456 nebo xlogin00)")
    async def verify_vut(self, interaction: discord.Interaction, id_login: str):
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
    
    @verify.command(name="host", description="Ověření e-mailem pro hosty (mimo VUT).")
    #@app_commands.guild_only()
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
    @verify.command(name="code", description="Zadej ověřovací kód.")
    #@app_commands.guild_only()
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

        # rozhodnuti o roli podle typ_studia 
        specific_role_name = "Host"  # default

        if ident_value:
            try:
                details = await self.bot.vut_api.get_user_details(ident_value)
                if details:
                    emails_api = [e.strip().lower() for e in (details.get("emaily") or [])]
                    vztahy = details.get("vztahy") or []

                    if mail_value in emails_api and vztahy:
                        typy_studia = set()

                        for vztah in vztahy:
                            typ_studia_info = vztah.get("typ_studia") or {}
                            zkratka_typu = (typ_studia_info.get("zkratka") or "").strip().upper()
                            if zkratka_typu:
                                typy_studia.add(zkratka_typu)

                        # rozhodnuti o roli podle typu studia
                        if len(typy_studia) == 0:
                            # fallback, kdyby nemel zadne typy_studia, tak necham puvodni default Host
                            pass
                        elif "B" in typy_studia:
                            specific_role_name = "Doktorand"
                        elif typy_studia.issubset({"D", "N", "C4"}):
                            specific_role_name = "VUT"  # B - bakalar, N - navazujici magistersky,
                                                        # C4 - celozivotni vzdelavani kratkodoby kurz
                        else:
                            specific_role_name = "VUT Staff"  # zamestnanec atd. 
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

    # lokalni/guild-only registrace (pokud to tak chces mit stejne jako u reviews)
    GUILD_ID = int(os.getenv("GUILD_ID", "0"))  # pouzij stejny pattern jako v reviews.py
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.add_command(Verify.verify, guild=guild)
        print(f"[verify] group 'verify' registered for guild {GUILD_ID}")
    else:
        bot.tree.add_command(Verify.verify)
        print("[verify] group 'verify' registered (global)")

