from datetime import datetime, timedelta
from sqlalchemy import and_
from db.session import SessionLocal
from db.models import Verification
from utils.mailer import send_verification_mail
from utils.codes import generate_verification_code
import discord
from discord import app_commands
from discord.ext import commands

class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="verify", description="Zadej svůj mail pro ověření.")
    async def verify(self, interaction: discord.Interaction, mail: str):
        user_id = interaction.user.id
        verification_code = generate_verification_code()

        with SessionLocal() as session:
            # 0) already verified -> stop early
            existing_verified = (
                session.query(Verification)
                .filter(and_(Verification.user_id == user_id, Verification.verified == True))
                .order_by(Verification.id.desc())
                .first()
            )
            if existing_verified:
                await interaction.response.send_message(
                    f"Už jsi ověřen. Pokud potřebujes změnu, kontaktuj moderátory.",
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

            # 3) block if the same mail is already verified by someone else
            someone_else = (
                session.query(Verification)
                .filter(
                    and_(
                        Verification.mail == mail,
                        Verification.verified == True,
                        Verification.user_id != user_id,
                    )
                )
                .first()
            )
            if someone_else:
                await interaction.response.send_message(
                    f"Tento e-mail ({mail}) je již použit jiným uživatelem a nelze ho znovu ověřit.",
                    ephemeral=True
                )
                return

            # 4) create new verification attempt
            v = Verification(user_id=user_id, mail=mail, verification_code=verification_code, verified=False)
            session.add(v)
            session.commit()

        # 5) send mail outside of session
        try:
            send_verification_mail(mail, verification_code)
            await interaction.response.send_message(
                f"Zadal jsi mail {mail}. Ověřovací kód byl odeslán na tvůj mail. (Zkontroluj si SPAM.)",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Došlo k chybě při odesílání mailu: {e}",
                ephemeral=True
            )

   
    @app_commands.command(name="verify_code", description="Zadej ověřovací kód.")
    async def verify_code(self, interaction: discord.Interaction, code: str):
        user_id = interaction.user.id

        with SessionLocal() as session:
            v = session.query(Verification).filter(
                Verification.user_id == user_id
            ).order_by(Verification.id.desc()).first()

            if v is None:
                await interaction.response.send_message(
                    "Nemáš žádný neověřený kód. Použij příkaz /verify pro získání kódu.",
                    ephemeral=True
                )
                return

            if v.verified:
                await interaction.response.send_message("Již jsi ověřen.", ephemeral=True)
                return

            if code != v.verification_code:
                await interaction.response.send_message("Chybný kód. Zkus to znovu.", ephemeral=True)
                return

            # save mail value before session close
            mail_value = v.mail
            v.verified = True
            session.commit()

        # work with roles after session is closed
        guild = interaction.guild

        verified_role = discord.utils.get(guild.roles, name="Verified")
        if not verified_role:
            verified_role = await guild.create_role(name="Verified")
        await interaction.user.add_roles(verified_role)

        if "@vut" in mail_value or "@vutbr" in mail_value:
            specific_role_name = "VUT"
        else:
            specific_role_name = "Host"

        specific_role = discord.utils.get(guild.roles, name=specific_role_name)
        if not specific_role:
            specific_role = await guild.create_role(name=specific_role_name)
        await interaction.user.add_roles(specific_role)

        await interaction.response.send_message(
            f"Ověření bylo úspěšné! Byly ti přidělené role 'Verified' a '{specific_role_name}'.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Verify(bot))

