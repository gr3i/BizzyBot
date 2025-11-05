from discord.ext import commands
from discord import app_commands, Interaction

class RoleInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="role", description="Vypíše hlavní role na serveru a jejich popisky")
    async def role(self, interaction: Interaction):
        # priklad roli a jejich popisku
        example_roles = [
            ("**Mod**", "Má nejvyšší oprávnění po ownerovi a odpovídá za správu serveru."),
            ("**Shadow Mod**", "Všechny role, které mají před rolí 'Shadow', jsou na stejné úrovni oprávnění jako role bez 'Shadow'. Tato role se týká 'Shadow' verzí rolí, tedy 'Shadow Mod', 'Shadow Submod', 'Shadow Helper' atd., které spravují ostatní VUT servery. Mají skoro stejné pravomoce jako běžní Modi, Submodi nebo Helperi. Pokud jste student, který zastává roli Mod, Submod nebo Helper na jiném oficiálním VUT serveru a máte zájem pomáhat i tady, napište mi (Ent3i) a rád vám tuto roli přidám."),
            ("**Submod**", "Druhá nejvyšší role na serveru, podřízená pouze Modům. Pomáhá při správě serveru a má značná oprávnění."),
            ("**Helper**", "Pomáhá uživatelům serveru s dotazy, problémy nebo informacemi. Je to role pro pomocníky, kteří usnadňují chod komunity."),
            ("**Bot**", "Speciální role pro bota, který zajišťuje správu a chod serveru."),
            ("**Teacher**", "Role pro učitele/vyučující. Pro přidání role 'Učitel' napište někomu z Modů."),  
        ]
        
        # seznam pro ulozeni roli s popisky
        role_info = []

        for role_name, role_description in example_roles:
            role_info.append(f"{role_name}: {role_description}")

        # pokud nejsou zadne role k zobrazeni
        if not role_info:
            await interaction.response.send_message("Tento server nemá žádné role s popisky.")
        else:
            # posilame seznam roli a jejich popisku
            role_text = "\n".join(role_info)
            role_text += "\n\nKdo kam vidí, se dozvíte zde: <#1422505714332602459>" 
            await interaction.response.send_message(role_text, ephemeral=False)

# funkce pro nacteni cogu
async def setup(bot):
    await bot.add_cog(RoleInfo(bot))

