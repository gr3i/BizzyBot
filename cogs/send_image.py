# poslani obrazku jaky potrebuji pres slash command 
import discord
from discord import app_commands
from discord.ext import commands


ALLOWED_USER_IDS = {
    685958402442133515, 
}
ALLOWED_ROLE_IDS = {
    1358898283782602932,
}

def user_is_allowed(interaction: discord.Interaction) -> bool:

    # povoleny uzivatel pouzivat command
    if interaction.user.id in ALLOWED_USER_IDS:
        return True
    
    # povoleni na roli  
    member = interaction.user if isinstance(interaction.user, discord.Member) else None
    if member:
        return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)
    return False


class VerificationImageModal(discord.ui.Modal, title="Poslat obrázek jako bot"):
    image_url = discord.ui.TextInput(
        label="URL obrázku",
        placeholder="vlož obrázek (raw link)",
        required=True,
        max_length=500,
    )
    description = discord.ui.TextInput(
        label="Popisek",
        placeholder="vlož popisek (nepovinné)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1024,
    )

    def __init__(self, reply_ephemeral: bool = False, embed_title: str | None = None):
        super().__init__()
        self.reply_ephemeral = reply_ephemeral
        self.embed_title = embed_title or "obrázek k poslání"

    async def on_submit(self, interaction: discord.Interaction) -> None:
        url = str(self.image_url.value).strip()
        
        if not (url.startswith("http://") or url.startswith("https://")):
            await interaction.response.send_message(
                "URL musí začínat na http(s)://", ephemeral=True
            )
            return

        embed = discord.Embed(title=self.embed_title)
       

        # ephemeralne „defer“, abych si mohl odpovedet pozdeji a nic neni videt v kanalu
        await interaction.response.defer(ephemeral=True)

        # posle cistou zpravu jako bot do kanalu (bez viditelne vazby na slash command)
        await interaction.channel.send(embed=embed)

        # kratke ephemeralni potvrzeni jen volajicimu
        await interaction.followup.send("Obrázek byl odeslán jako bot.", ephemeral=True) 


class VerificationImage(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # check na oprávnění pro slash command
    async def _permissions_check(self, interaction: discord.Interaction):
        if not user_is_allowed(interaction):
            raise app_commands.CheckFailure("Na tento příkaz nemáš oprávnění.")

    @app_commands.command(
        name="obrazek",
        description="Odešle obrázek z vloženého URL a volitelný popisek. (Only MODs)"
    )
    @app_commands.checks.check(user_is_allowed)
    @app_commands.guild_only()
    async def verificationimage(self, interaction: discord.Interaction):
        """Otevře modal s poli: URL obrázku + popisek."""
        await interaction.response.send_modal(VerificationImageModal())

    # pokud nemas opravneni
    @verificationimage.error
    async def verificationimage_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                "Na tento příkaz nemáš oprávnění.", ephemeral=True
            )
        else:
            # jiná chyba
            await interaction.response.send_message(
                f"Něco se pokazilo: {error}", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(VerificationImage(bot))

