from discord.ext import commands
from discord import app_commands, Interaction, Embed
ALLOWED_CHANNEL_ID = 1358908501031915621

class RoleInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="role", description="Vypíše hlavní role na serveru a jejich popisky")
    async def role(self, interaction: Interaction):

        # povol pouze v jednom kanalu
        if interaction.channel_id != ALLOWED_CHANNEL_ID:
            await interaction.response.send_message(
                "Tento prikaz lze pouzit jen v urcenem kanalu.",
                ephemeral=True
            )
            return

        # priklad roli a jejich popisku
        example_roles = [
            ("**Mod**", "Má nejvyšší oprávnění po ownerovi a odpovídá za správu serveru."),
            ("**Shadow Mod**", "Všechny role, které mají před rolí 'Shadow', jsou na stejné úrovni oprávnění jako role bez 'Shadow'. Tato role se týká 'Shadow' verzí rolí, tedy 'Shadow Mod', 'Shadow Submod', 'Shadow Helper' atd., které spravují ostatní VUT servery. Mají skoro stejné pravomoce jako běžní Modi, Submodi nebo Helperi. Pokud jste student, který zastává roli Mod, Submod nebo Helper na jiném oficiálním VUT serveru a máte zájem pomáhat i tady, napište mi (Ent3i) a rád vám tuto roli přidám."),
            ("**Submod**", "Druhá nejvyšší role na serveru, podřízená pouze Modům. Pomáhá při správě serveru a má značná oprávnění."),
            ("**Helper**", "Pomáhá uživatelům serveru s dotazy, problémy nebo informacemi. Je to role pro pomocníky, kteří usnadňují chod komunity."),
            ("**Bot**", "Speciální role pro bota, který zajišťuje správu a chod serveru."),
            ("**Teacher**", "Role pro učitele/vyučující. Pro přidání role 'Učitel' napište někomu z Modů."),  
        ]
        
        #vytvoreni embedu
        embed = Embed(
            title="Přehled hlavních rolí na serveru",
            description="Níže najdete popis všech hlavních rolí:",
            color=0x2ecc71
        ) 
 
        # pridani poli pro kazdou roli
        for role_name, role_description in example_roles:
            embed.add_field(name=role_name, value=role_description, inline=False)

        embed.add_field(
            name="Kdo kam vidí",
            value="[Klikni sem pro zobrazení přehledu](https://discord.com/channels/1357455204391321712/1422505714332602459/1435567370969288704)",
            inline=False
        ) 

        # odeslani embedu
        await interaction.response.send_message(embed=embed, ephemeral=False) 

# funkce pro nacteni cogu
async def setup(bot):
    await bot.add_cog(RoleInfo(bot))

