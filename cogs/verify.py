# cogs/verify.py
import discord
from discord import app_commands
from discord.ext import commands

from datetime import datetime, timedelta

from db.session import SessionLocal
from db.models import Verification

from utils.mailer import send_verification_mail
from utils.codes import generate_verification_code


class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="verify", description="Zadej svůj mail pro ověření.")
    async def verify(self, interaction: discord.Interaction, mail: str):
        user_id = interaction.user.id
        verification_code = generate_verification_code()

        # ORM session
        with SessionLocal() as session:
            # Smazat stare neoverene pokusy daneho uzivatele
            session.query(Verification).filter(
                Verification.user_id == user_id,
                Verification.verified.is_(False),
            ).delete(synchronize_session=False)

            # Smazat neoverene pokusy starsi nez 10 minut (globalne)
            cutoff = datetime.utcnow() - timedelta(minutes=10)
            session.query(Verification).filter(
                Verification.verified.is_(False),
                Verification.created_at <= cutoff
            ).delete(synchronize_session=False)

            # Zkontrolovat, zda tento mail už neni overen jinym uzivatelem
            existing = session.query(Verification).filter(
                Verification.mail == mail,
                Verification.verified.is_(True),
                Verification.user_id != user_id
            ).first()

            if existing:
                await interaction.response.send_message(
                    f"Tento e-mail ({mail}) je již použit jiným uživatelem a nelze ho znovu ověřit.",
                    ephemeral=True
                )
                return

            # Ulozit novy overovaci pokus
            v = Verification(
                user_id=user_id,
                mail=mail,
                verification_code=verification_code,
                verified=False,
                # created_at nechame na defaultu DB; pripadne dat created_at=datetime.utcnow()
            )
            session.add(v)
            session.commit()

        # 5) Odeslat e-mail s kodem
        try:
            send_verification_mail(mail, verification_code)
            await interaction.response.send_message(
                f"Zadal jsi mail {mail}. Ověřovací kód byl odeslán na tvůj mail. (Zkontroluj si spam)",
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
            # Vezmeme posledni pokus daneho uzivatele (nebo prvni neovereny)
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

            # Overeni OK - oznacit jako verified
            v.verified = True
            session.commit()

        # Role prirazujeme az po uspesnem potvrzeni
        guild = interaction.guild

        # role 'Verified'
        verified_role = discord.utils.get(guild.roles, name="Verified")
        if not verified_role:
            verified_role = await guild.create_role(name="Verified")
        await interaction.user.add_roles(verified_role)

        # role podle domeny mailu
        if "@vut" in v.mail or "@vutbr" in v.mail:
            specific_role_name = "VUT"
        else:
            specific_role_name = "Host"

        specific_role = discord.utils.get(guild.roles, name=specific_role_name)
        if not specific_role:
            specific_role = await guild.create_role(name=specific_role_name)
        await interaction.user.add_roles(specific_role)

        await interaction.response.send_message(
            f"Ověření bylo úspěšné! Byly ti přiděleny role 'Verified' a '{specific_role_name}'.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Verify(bot))

