from discord.ext import commands
from discord import app_commands, Interaction
import discord
import sqlite3
import os

class Strip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # pomocna funkce pro pripojeni k databazi
    def create_connection(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, "..", "db", "verify.db")
        return sqlite3.connect(db_path)

    @app_commands.command(name="strip", description="Odebere ti verifikaci, roli 'Verified' a smaže tě z databáze.")
    async def strip(self, interaction: Interaction):
        user_id = interaction.user.id
        guild = interaction.guild

        # seznam roli, ktere chceme odstranit specificky
        roles_to_remove = ["Verified", "VUT", "Host"]

        # odebrani specifickych roli
        for role_name in roles_to_remove:
            role = discord.utils.get(guild.roles, name=role_name)
            if role and role in interaction.user.roles:
                await interaction.user.remove_roles(role)

        # odstraneni vsech ostatnich roli krome @everyone
        for role in interaction.user.roles:
            if role.name != "@everyone":  # neodstranujeme roli @everyone
                await interaction.user.remove_roles(role)

        # smazani z databaze
        conn = self.create_connection()
        cursor = conn.cursor()
        cursor.execute('''
        DELETE FROM verifications WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()

        await interaction.response.send_message(
            "Byl jsi odstraněn z databáze a všechny tvoje role byly odebrány, pokud jsi nějaké měl.",
            ephemeral=True
        )

# setup funkce pro nacteni Cog modulu
async def setup(bot):
    await bot.add_cog(Strip(bot))

