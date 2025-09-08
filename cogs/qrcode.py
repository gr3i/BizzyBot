# posle do chatu qrcode 

import os
import discord
from discord import app_commands
from discord.ext import commands

QR_CODE_IMAGE = os.getenv("QR_CODE_IMAGE")

class QRCode(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if not QR_CODE_IMAGE:
            print("[WARN] QR_CODE_IMAGE neni nastavene. Pridat do .env")

    @app_commands.command(
        name="qrcode",
        description="Pošle QR kód VUT FP Discord serveru."
    )
    async def qrcode(self, interaction: discord.Interaction):
        if not QR_CODE_IMAGE:
            return await interaction.response.send_message(
                "Chybi konfigurace `QR_CODE_IMAGE`.", ephemeral=True
            )

        embed = discord.Embed(title="QR kód")
        embed.set_image(url=QR_CODE_IMAGE)
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(QRCode(bot))

