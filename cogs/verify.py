import discord
from discord import app_commands
from discord.ext import commands
from db.session import SessionLocal
from db.models import Verification
from utils.mailer import send_verification_mail
from utils.codes import generate_verification_code

class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="verify", description="Zadej svuj mail pro overeni.")
    async def verify(self, interaction: discord.Interaction, mail: str):
    user_id = interaction.user.id
    verification_code = generate_verification_code()

    with SessionLocal() as session:
        # 0) user is already verified -> stop early
        existing_verified = (
            session.query(Verification)
            .filter(Verification.user_id == user_id, Verification.verified == True)
            .order_by(Verification.id.desc())
            .first()
        )
        if existing_verified:
            await interaction.response.send_message(
                f"Uz jsi overen jako {existing_verified.mail}. Pokud potrebujes zmenu, kontaktuj moderatory.",
                ephemeral=True
            )
            return

        # 1) delete old unverified attempts of this user
        session.query(Verification).filter(
            Verification.user_id == user_id, Verification.verified == False
        ).delete(synchronize_session=False)

        # 2) delete global unverified attempts older than 10 minutes
        # sqlite server_default handles created_at; easiest is to compare via SQL func
        from sqlalchemy import text
        session.execute(
            text("DELETE FROM verifications WHERE verified = 0 AND created_at <= datetime('now', '-10 minutes')")
        )

        # 3) block if this mail is already verified by someone else
        someone_else = (
            session.query(Verification)
            .filter(
                Verification.mail == mail,
                Verification.verified == True,
                Verification.user_id != user_id,
            )
            .first()
        )
        if someone_else:
            await interaction.response.send_message(
                f"Tento e-mail ({mail}) je jiz pouzit jinym uzivatelem a nelze ho znovu overit.",
                ephemeral=True
            )
            return

        # 4) create new verification attempt
        v = Verification(user_id=user_id, mail=mail, verification_code=verification_code, verified=False)
        session.add(v)
        session.commit()

    # 5) send code by email (outside session)
    try:
        send_verification_mail(mail, verification_code)
        await interaction.response.send_message(
            f"Zadal jsi mail {mail}. Overovaci kod byl odeslan na tvuj mail. (zkontroluj SPAM)",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"Doslo k chybe pri odesilani mailu: {e}",
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

