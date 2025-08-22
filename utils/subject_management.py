# cogs/subjects.py
import os
import discord
from discord import app_commands
from discord.ext import commands

# role, která smí příkaz použít (stejná jako u reviews)
ALLOWED_ROLE_ID = 1358911329737642014

# (překopírováno z tvého kódu)
SUBJECT_ROLES: list[tuple[str, int]] = [
     ("epP",1383522736986656950 ),
    ("mak1P", 1383522746167857202),
    ("manP", 1383522758658490551),
    ("mkP", 1383522765092425788),
    ("ma1P", 1383522770130047036),
    ("HA1PZ", 1383522776664637544),
    ("HA2PZ", 1383522782343598082),
    ("pzmP", 1383522787821355200),
    ("pmzP", 1383522811058061373),
    ("pmrzP", 1383522816938348655),
    ("KeseP", 1383522822713905366),
    ("IG", 1383522832356475024),
    ("KinfP", 1383522839239327874),
    ("ma2P", 1383522843593015379),
    ("mik1P", 1383522850505494710),
    ("uceP", 1383522873120919718),
    ("HA2PL", 1383522880347832432),
    ("HA3PL", 1383522885339054150),
    ("pmlP", 1383522890456240150),
    ("pmrlP", 1383522896760016928),
    ("fpP", 1383522903387017348),
    ("ftP", 1383522928200515596),
    ("KjpP", 1383522934236381270),
    ("KrnP", 1383522938963365960),
    ("statP", 1383522943992074422),
    ("KikP", 1383522948928770060),
    ("kvmP", 1383522973046149281),
    ("AOP1", 1383522977982972125),
    ("KdetP", 1383522983007748237),
    ("VYF001", 1383522988665868401),
    ("VYI001", 1383522993510023238),
    ("KmmP", 1383523017832796183),
    ("VYN001", 1383523024082309202),
    ("VYS001", 1383523031275802735),
    ("KdasP", 1383523036116025456),
    ("fapP", 1383523041195331737),
    ("marP", 1383523064125329470),
    ("KobP", 1383523070685352097),
    ("pojP", 1383523075852599340),
    ("emP", 1383523082366615612),
    ("pprP", 1383523088305623040),
    ("zdP", 1383523093741305916),
    ("AOP2", 1383523100834009088),
    ("msmP", 1383523123667927061),
    ("KepP", 1383523129187631164),
    ("VYF002", 1383523134539436205),
    ("VYN002", 1383523140612657273),
    ("VYS002", 1383523151807385621),
    ("oprP", 1383523157482279012),
    ("KopxzP", 1383523162569834657),
    ("KosP", 1383523187806965771),
    ("prP", 1383523193213681846),
    ("KpdsP", 1383523198024421466),
    ("KdmP", 1383523204030529617),
    ("smarP", 1383523209252438036),
    ("KimP", 1383523232849858570),
    ("KrlrP", 1383523238738399353),
    ("VYF003", 1383523243293671515),
    ("VYI003", 1383523249752641597),
    ("VYN003", 1383523255461351555),
    ("VYS003", 1383523261652140254),
    ("bpsP", 1383523285324664872),
    ("KdsP", 1383523290894569553),
    ("Kme1P", 1383523297546735667),
    ("KopxlP", 1383523302575964270),
    ("BBIDE", 1383523307407544320),
    ("BECOE", 1383523335836667904),
    ("BMAE", 1383523341624934400),
    ("BMEE", 1383523346985259088),
    ("BMARE", 1383523352857284709),
    ("BMATE", 1383523363644903566),
    ("BDMSE", 1383523370150395994),
    ("BFMSE", 1383523376533999798),
    ("BLENE", 1383523383354069114),
    ("BPENE", 1383523406133067928),
    ("BBCDE", 1383523412047040552),
    ("BATE", 1383523417436852425),
    ("BEPR1E", 1383523425188053053),
    ("BMRE", 1383523430476812289),
    ("BPMAE", 1383523437661913109),
    ("BAASE", 1383523443705643182),
    ("BCCSME", 1383523466522791956),
    ("BEPR2E", 1383523471321202719),
    ("BHRME", 1383523476710883398),
    ("BSMAE", 1383523482142380124),
    ("BEPR3E", 1383523489071501375),
    ("BFT1E", 1383523511775264952),
    ("BISSCE", 1383523516954968064),
    ("BTSPE", 1383523527046467777),
    ("BBDAE", 1383523535057846332),
    ("BEPR4E", 1383523540178964683),
    ("BFT2E", 1383523548106199120),
    ("DFM", 1383523555203088394),
    ("MA1_M", 1383523560433385594),
    ("IUS", 1383523583682154576),
    ("ZE", 1383523588631429293),
    ("OA1Z", 1383523595233529957),
    ("OA2Z", 1383523603206635701),
    ("APV", 1383523609657606265),
    ("bdmP", 1383523614548295884),
    ("MA2_M", 1383523620239970535),
    ("NUM", 1383523643782332496),
    ("PLAB", 1383523648480084039),
    ("VT", 1383523660282859605),
    ("OA2L", 1383523666880626819),
    ("OA3", 1383523673499107358),
    ("DMSM", 1383523678607773716),
    ("EC", 1383523684073083002),
    ("EPO", 1383523707049349192),
    ("RD", 1383523711700963430),
    ("STA1", 1383523717388308480),
    ("DIT", 1383523724438933734),
    ("PPP", 1383523732462637188),
    ("BuceP", 1383523738137530481),
    ("IZP", 1383523742960849079),
    ("MRMU", 1383523767312973887),
    ("PRA", 1383523774015606886),
    ("RPICT", 1383523779376058498),
    ("STA2", 1383523784681853069),
    ("UPS", 1383523789500973201),
    ("ZFI", 1383523811718332428),
    ("ISJ", 1383523816948498566),
    ("ITW", 1383523822094782594),
    ("IZG", 1383523828252147833),
    ("DS_2", 1383523839031640066),
    ("MICT", 1383523844228386917),
    ("PIS", 1383523850318249985),
    ("PPR1", 1383523872988729375),
    ("PDS", 1383523879871578133),
    ("APSP", 1383523885223514195),
    ("rkP", 1383523890051153940),
    ("ITU", 1383523896912773202),
    ("DIS", 1383523919276933192),
    ("PRIS", 1383523931826163814),
    ("PPR2", 1383523938696691712),
    ("PICT", 1383523944484573375),
    ("infP", 1383523951845703731),
    ("BbpP", 1383523958267183165),
    ("kitP", 1383523963266662441),
    ("BelmP", 1383523985966235699),
    ("BmsP", 1383523992068948011),
    ("BopvP", 1383523999245533195),
    ("Bp1P", 1383524004664709242),
    ("BpmP", 1383524015527952515),
    ("ssrP", 1383524020527566878),
    ("rrpnP", 1383524026944716981),
    ("BomvP", 1383524033957466204),
    ("Bp2P", 1383524056506306601),
    ("BrprP", 1383524062730649610),
    ("BevpP", 1383524068300685463),
    ("BstP", 1383524074332098700),
    ("BbezP", 1383524086474604598),
    ("BlogaP", 1383524100181594246),
    ("BoppP", 1383524106296754218),
    ("BpisP", 1383524112374173898),
    ("BpdsP", 1383524117936083045),
    ("BsvP", 1383524124521005136),
    ("BdisP", 1383524129927463086),
    ("BmzP", 1383524153377816586),
    ("Bp3P", 1383524160180977705),
    ("BrkvP", 1383524167034343616),
    ("BtrtP", 1383524173510606872),
    ("PVA3", 1383524181072941186),
    ("PVA4", 1383524185770557564),
    ("PVB1", 1383524191525142550),
    ("PVB2", 1383524215872815215),
    ("PVB5", 1383524222881632389),
    ("PVB6", 1383524234558701642),
    ("UzpP", 1383524240363491478),
    ("UvfP", 1383524245534937229),
    ("UvpP", 1383524251298168872),
    ("UfuP", 1383524257115537540),
    ("UopP", 1383524279978557510),
    ("UzfoP", 1383524286077210624),
    ("UfudP", 1383524292691497061),
    ("UmpaP", 1383524302573539398),
    ("Uopx1P", 1383524307740790937),
    ("UzpoP", 1383524313344376832),
    ("UdphP", 1383524320525160489),
    ("UnuP", 1383524326426280017),
    ("Uopx2P", 1383524350879072466),
    ("UpdsP", 1383524356394586316),
    ("UupcP", 1383524361805369367),
    ("UvhoP", 1383524367446708375),
    ("UispP", 1383524372941115483),
    ("UdsP", 1383524396743790653),
    ("UmzpP", 1383524402242523248),
    ("UudpP", 1383524407938387978),
    ("UfifP", 1383524413596631070),
    ("PVB3", 1383524421934911589),
    ("PVB4", 1383524427681239190),  
]

def _find_role_id(name: str) -> int | None:
    return next((rid for n, rid in SUBJECT_ROLES if n == name), None)

async def _predmet_autocomplete(inter: discord.Interaction, current: str):
    matches = [n for n, _ in SUBJECT_ROLES if current.lower() in n.lower()]
    return [app_commands.Choice(name=n, value=n) for n in matches[:25]]

class SubjectCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Slash group /predmet
    predmet = app_commands.Group(
        name="predmet",
        description="Přidání a odebrání role k předmětu"
    )

    @predmet.command(name="pridat", description="Přidá roli vybraného předmětu.")
    @app_commands.guild_only()
    @app_commands.describe(predmet="Název předmětu")
    @app_commands.autocomplete(predmet=_predmet_autocomplete)
    @app_commands.checks.has_role(ALLOWED_ROLE_ID)
    async def predmet_pridat(self, interaction: discord.Interaction, predmet: str):
        rid = _find_role_id(predmet)
        if rid is None:
            await interaction.response.send_message("Předmět nebyl nalezen.", ephemeral=True)
            return

        role = interaction.guild.get_role(rid)
        if role is None:
            await interaction.response.send_message("Role nebyla nalezena.", ephemeral=True)
            return

        member: discord.Member = interaction.user  # type: ignore
        if role in member.roles:
            await interaction.response.send_message("Tuto roli už máš.", ephemeral=True)
            return

        await member.add_roles(role, reason="/predmet pridat")
        await interaction.response.send_message(f"✅ Přidána role **{role.name}**.", ephemeral=True)

    @predmet.command(name="odebrat", description="Odebere roli vybraného předmětu.")
    @app_commands.guild_only()
    @app_commands.describe(predmet="Název předmětu")
    @app_commands.autocomplete(predmet=_predmet_autocomplete)
    @app_commands.checks.has_role(ALLOWED_ROLE_ID)
    async def predmet_odebrat(self, interaction: discord.Interaction, predmet: str):
        rid = _find_role_id(predmet)
        if rid is None:
            await interaction.response.send_message("Předmět nebyl nalezen.", ephemeral=True)
            return

        role = interaction.guild.get_role(rid)
        if role is None:
            await interaction.response.send_message("Role nebyla nalezena.", ephemeral=True)
            return

        member: discord.Member = interaction.user  # type: ignore
        if role not in member.roles:
            await interaction.response.send_message("Tuto roli nemáš.", ephemeral=True)
            return

        await member.remove_roles(role, reason="/predmet odebrat")
        await interaction.response.send_message(f"❌ Odebrána role **{role.name}**.", ephemeral=True)

    # Jeden společný error handler pro obě sub-commands
    @predmet_pridat.error
    @predmet_odebrat.error
    async def predmet_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.errors.MissingRole):
            await interaction.response.send_message("❌ Nemáš oprávnění použít tento příkaz.", ephemeral=True)
        else:
            # pro ladění
            await interaction.response.send_message(f"❌ Chyba: {error}", ephemeral=True)

# Registrace skupiny do správné guildy (ihned viditelné)
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

async def setup(bot: commands.Bot):
    cog = SubjectCog(bot)
    await bot.add_cog(cog)

    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.add_command(SubjectCog.predmet, guild=guild)
        print(f"[subjects] group 'predmet' registered for guild {GUILD_ID}")
    else:
        bot.tree.add_command(SubjectCog.predmet)
        print("[subjects] group 'predmet' registered (global)")

