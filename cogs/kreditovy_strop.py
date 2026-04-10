from discord.ext import commands
from discord import app_commands, Interaction, Embed

ALLOWED_CHANNEL_ID = 1358908501031915621


class CreditLimit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="kreditovy_strop",
        description="Vypíše informace o kreditovém stropu"
    )
    async def kreditovy_strop(self, interaction: Interaction):

        # Povol pouze v jednom kanalu
        # if interaction.channel_id != ALLOWED_CHANNEL_ID:
        #     await interaction.response.send_message(
        #         "Tento prikaz lze pouzit jen v kanalu bot-spam.",
        #         ephemeral=True
        #     )
        #     return

        embed = Embed(
            title="Kreditový strop",
            description=(
                "**Pro zápis do LS:**\n\n"
                "• **80 kreditů** – průměr do **1,5**\n"
                "• **75 kreditů** – vše splněno + průměr do **2,0**\n"
                "• **70 kreditů** – min. **20 kreditů**, žádný nesplněný volitelný, max. **1 nesplněný povinný**\n"
                "• **65 kreditů** – jinak"
            ),
            color=0x2ecc71
        )

        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot):
    await bot.add_cog(CreditLimit(bot))
