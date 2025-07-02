import discord
from discord import app_commands
from discord.ext import commands
from db.database import create_connection
from utils.mailer import send_verification_mail
from utils.codes import generate_verification_code

class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="verify", description="Zadej svůj mail pro ověření.")
    async def verify(self, interaction: discord.Interaction, mail: str):
        user_id = interaction.user.id
        verification_code = generate_verification_code()

        conn = create_connection()
        cursor = conn.cursor()

        # smazat stare neoverene pokusy uzivatele
        cursor.execute('''
        DELETE FROM verifications
        WHERE user_id = ? AND verified = 0
        ''', (user_id,))

        # smazat neoverene pokusy starsi nez 10 minut
        cursor.execute('''
        DELETE FROM verifications
        WHERE verified = 0 AND created_at <= datetime('now', '-10 minutes')
        ''')

        # zkontrolovat, jestli mail uz je overen nekym jinym
        cursor.execute('''
        SELECT user_id FROM verifications WHERE mail = ? AND verified = 1 AND user_id != ?
        ''', (mail, user_id))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            await interaction.response.send_message(
                f"Tento e-mail ({mail}) je již použit jiným uživatelem a nelze ho znovu ověřit.",
                ephemeral=True
            )
            return

        # ulozit novy overovaci pokus
        cursor.execute('''
        INSERT INTO verifications (user_id, mail, verification_code)
        VALUES (?, ?, ?)
        ''', (user_id, mail, verification_code))
      
        conn.commit()
        conn.close()

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

        conn = create_connection()
        cursor = conn.cursor()

        cursor.execute('''
        SELECT mail, verification_code, verified FROM verifications WHERE user_id = ?
        ''', (user_id,))
        row = cursor.fetchone()

        if row is None:
            await interaction.response.send_message(
                "Nemáš žádný neověřený kód. Použij příkaz /verify pro získání kódu.",
                ephemeral=True
            )
            conn.close()
            return

        mail, stored_code, verified = row

        if verified:
            await interaction.response.send_message("Již jsi ověřen.", ephemeral=True)
            conn.close()
            return

        if code == stored_code:
            cursor.execute('''
            UPDATE verifications SET verified = 1 WHERE user_id = ?
            ''', (user_id,))
            conn.commit()

            guild = interaction.guild

            # pridani role 'Verified'
            verified_role = discord.utils.get(guild.roles, name="Verified")
            if not verified_role:
                verified_role = await guild.create_role(name="Verified")
            await interaction.user.add_roles(verified_role)

            # pridani specificke role dle mailu
            if "@vut" in mail or "@vutbr" in mail:
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
        else:
            await interaction.response.send_message("Chybný kód. Zkus to znovu.", ephemeral=True)

        conn.close()

async def setup(bot):
    await bot.add_cog(Verify(bot))

