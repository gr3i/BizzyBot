import discord
from discord import app_commands
from discord.ext import commands

# predmety pro obor Ekonomika podniku - 1. rocnik

# "Ekonomika podniku - 1. ročník"
ekonomika_podniku_1_rocnik = [
    ("HA1PZ", 1383522776664637544),
    ("HA2PL", 1383522880347832432),
    ("HA2PZ", 1383522782343598082),
    ("HA3PL", 1383522885339054150),
    ("IG", 1383522832356475024),
    ("KeseP", 1383522822713905366),
    ("KinfP", 1383522839239327874),
    ("epP", 1383522736986656950),
    ("ma1P", 1383522770130047036),
    ("ma2P", 1383522843593015379),
    ("mak1P", 1383522746167857202),
    ("manP", 1383522758658490551),
    ("mik1P", 1383522850505494710),
    ("mkP", 1383522765092425788),
    ("pmlP", 1383522890456240150),
    ("pmrlP", 1383522896760016928),
    ("pmrzP", 1383522816938348655),
    ("pmzP", 1383522811058061373),
    ("pzmP", 1383522787821355200),
    ("uceP", 1383522873120919718),
]

# "Ekonomika podniku - 2. ročník"
ekonomika_podniku_2_rocnik = [
    ("AOP1", 1383522977982972125),
    ("AOP2", 1383523100834009088),
    ("KdasP", 1383523036116025456),
    ("KdetP", 1383522983007748237),
    ("KepP", 1383523129187631164),
    ("KikP", 1383522948928770060),
    ("KjpP", 1383522934236381270),
    ("KmmP", 1383523017832796183),
    ("KobP", 1383523070685352097),
    ("KrnP", 1383522938963365960),
    ("VYF001", 1383522988665868401),
    ("VYF002", 1383523134539436205),
    ("VYI001", 1383522993510023238),
    ("VYN001", 1383523024082309202),
    ("VYN002", 1383523140612657273),
    ("VYS001", 1383523031275802735),
    ("VYS002", 1383523151807385621),
    ("emP", 1383523082366615612),
    ("fapP", 1383523041195331737),
    ("fpP", 1383522903387017348),
    ("ftP", 1383522928200515596),
    ("kvmP", 1383522973046149281),
    ("marP", 1383523064125329470),
    ("msmP", 1383523123667927061),
    ("pojP", 1383523075852599340),
    ("pprP", 1383523088305623040),
    ("statP", 1383522943992074422),
    ("zdP", 1383523093741305916),
]
# "Ekonomika podniku - 3. ročník"
ekonomika_podniku_3_rocnik = [
    ("KdmP", 1383523204030529617),
    ("KdsP", 1383523290894569553),
    ("KimP", 1383523232849858570),
    ("Kme1P", 1383523297546735667),
    ("KopxlP", 1383523302575964270),
    ("KopxzP", 1383523162569834657),
    ("KosP", 1383523187806965771),
    ("KpdsP", 1383523198024421466),
    ("KrlrP", 1383523238738399353),
    ("VYF003", 1383523243293671515),
    ("VYI003", 1383523249752641597),
    ("VYN003", 1383523255461351555),
    ("VYS003", 1383523261652140254),
    ("bpsP", 1383523285324664872),
    ("oprP", 1383523157482279012),
    ("prP", 1383523193213681846),
    ("smarP", 1383523209252438036),
]


# seznam oboru
obory_list = [
    ("Ekonomika podniku - 1. ročník", ekonomika_podniku_1_rocnik),
    ("Ekonomika podniku - 2. ročník", ekonomika_podniku_2_rocnik),
    ("Ekonomika podniku - 3. ročník", ekonomika_podniku_3_rocnik),
    # tady pridam dalsi obory...
]

async def obor_autocomplete(interaction: discord.Interaction, current: str):
    matches = [name for name, _ in obory_list if current.lower() in name.lower()]
    return [app_commands.Choice(name=name, value=name) for name in matches[:25]]

class Obor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="obor", description="Vyber si obor a ročník a automaticky získáš role předmětů.")
    @app_commands.describe(obor="Název oboru a ročníku")
    @app_commands.autocomplete(obor=obor_autocomplete)
    async def obor(self, interaction: discord.Interaction, obor: str):
        predmety = next((predmety for name, predmety in obory_list if name == obor), None)
        if predmety is None:
            await interaction.response.send_message("❌ Obor nebyl nalezen.", ephemeral=True)
            return
        
        pridane_role = []
        for _, role_id in predmety:
            role = interaction.guild.get_role(role_id)
            if role and role not in interaction.user.roles:
                await interaction.user.add_roles(role)
                pridane_role.append(role.name)

        if pridane_role:
            await interaction.response.send_message(
                f"✅ Byly ti přidány role předmětů pro obor **{obor}**: {', '.join(pridane_role)}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"ℹ️ Všechny role pro obor **{obor}** už máš přiřazené.",
                ephemeral=True
            )

    @app_commands.command(name="obor_odebrat", description="Vyber si obor a odeberou se ti role předmětů tohoto oboru.")
    @app_commands.describe(obor="Název oboru a ročníku")
    @app_commands.autocomplete(obor=obor_autocomplete)
    async def obor_odebrat(self, interaction: discord.Interaction, obor: str):
        predmety = next((predmety for name, predmety in obory_list if name == obor), None)
        if predmety is None:
            await interaction.response.send_message("❌ Obor nebyl nalezen.", ephemeral=True)
            return
        
        odebrane_role = []
        for _, role_id in predmety:
            role = interaction.guild.get_role(role_id)
            if role and role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                odebrane_role.append(role.name)

        if odebrane_role:
            await interaction.response.send_message(
                f"✅ Byly ti odebrány role předmětů pro obor **{obor}**: {', '.join(odebrane_role)}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"ℹ️ Žádné role pro obor **{obor}** jsi neměl.",
                ephemeral=True
            )

    @obor.error
    @obor_odebrat.error
    async def obor_error(self, interaction: discord.Interaction, error):
        await interaction.response.send_message(
            f"❌ Došlo k chybě: {str(error)}", ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Obor(bot))

