import discord
from discord import app_commands
from discord.ext import commands


# Obory + hlavní role + seznam předmětů
obory_list = [
    (
        "Ekonomika podniku - 1. ročník",
        1384961946046042284,  # BAK-EP1
        [
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
            # ... dalsi predmety
        ]
    ),
    (
        "Ekonomika podniku - 2. ročník",
        1384962230298349649,  # BAK-EP2
        [
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
            # ... další předměty
        ]
    ),
    (
        "Ekonomika podniku - 3. ročník",
        1384962548733972600,  # BAK-EP3
        [
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
            # ... dalsi predmety
        ]
    ),
    (
    "Procesní management - 1. ročník",
    1390033798418399254,[
        # 1. ročník, zimní semestr
        ("infP", 1383523951845703731),
        ("manP", 1383522758658490551),
        ("ma1P", 1383522770130047036),
        ("EPO", 1383523707049349192),
        ("ZE", 1383523588631429293),
        ("HA1PZ", 1383522776664637544),
        ("HA2PZ", 1383522782343598082),
        ("pzmP", 1383522787821355200),
        ("pmzP", 1383522811058061373),
        ("pmrzP", 1383522816938348655),
    
        # 1. ročník, letní semestr
        ("bdmP", 1383523614548295884),
        ("BbpP", 1383523958267183165),
        ("kitP", 1383523963266662441),
        ("ma2P", 1383522843593015379),
        ("zdP", 1383523093741305916),
        ("HA3PL", 1383522885339054150),
        ("HA2PL", 1383522880347832432),
        ("BelmP", 1383523985966235699),
        ("BmsP", 1383523992068948011),
        ("IG", 1383522832356475024),
        ("pmlP", 1383522890456240150),
        ("pmrlP", 1383522896760016928),
    ]
            ),
    (
   "Procesní management - 2.ročník",
    1390033955776106546,[
    # 2. ročník, zimní semestr
    ("oprP", 1383523157482279012),
    ("BopvP", 1383523999245533195),
    ("Bp1P", 1383524004664709242),
    ("BpmP", 1383524015527952515),
    ("statP", 1383522943992074422),
    ("kvmP", 1383522973046149281),
    ("ssrP", 1383524020527566878),
    ("BuceP", 1383523738137530481),
    ("AOP1", 1383522977982972125),
    ("VYF001", 1383522988665868401),
    ("VYI001", 1383522993510023238),
    ("VYN001", 1383523024082309202),
    ("VYS001", 1383523031275802735),
    ("rrpnP", 1383524026944716981),

    # 2. ročník, letní semestr
    ("marP", 1383523064125329470),
    ("BomvP", 1383524033957466204),
    ("Bp2P", 1383524056506306601),
    ("BrprP", 1383524062730649610),
    ("BevpP", 1383524068300685463),
    ("BstP", 1383524074332098700),
    ("BbezP", 1383524086474604598),
    ("emP", 1383523082366615612),
    ("ZFI", 1383523811718332428),
    ("AOP2", 1383523100834009088),
    ("VYF002", 1383523134539436205),
    ("VYN002", 1383523140612657273),
    ("VYS002", 1383523151807385621),
    ("IG", 1383522832356475024),
    ("VYI002",1390037910996123818 ),
    ("rrpnP", 1383524026944716981),
] 
    
            ),

    (
   "Procesní management - 3. ročník",
    1390034014282187015, [
    # 3. ročník, zimní semestr
    ("rkP", 1383523890051153940),
    ("BlogaP", 1383524100181594246),
    ("BoppP", 1383524106296754218),
    ("BpisP", 1383524112374173898),
    ("BpdsP", 1383524117936083045),
    ("BsvP", 1383524124521005136),
    ("VYF003", 1383523243293671515),
    ("VYI003", 1383523249752641597),
    ("VYN003", 1383523255461351555),
    ("VYS003", 1383523261652140254),

    # 3. ročník, letní semestr
    ("BdisP", 1383524129927463086),
    ("BmzP", 1383524153377816586),
    ("Bp3P", 1383524160180977705),
    ("BrkvP", 1383524167034343616),
    ("BtrtP", 1383524173510606872),
] 
            ),
    (
    "Manažerská informatika - 1. ročník",
     1390043190702112939,[
        # 1. ročník, zimní semestr
        ("DFM", 1383523555203088394),
        ("manP", 1383522758658490551),
        ("MA1_M", 1383523560433385594),
        ("IUS", 1383523583682154576),
        ("ZE", 1383523588631429293),
        ("OA1Z", 1383523595233529957),
        ("OA2Z", 1383523603206635701),
        ("pzmP", 1383522787821355200),
        ("pmzP", 1383522811058061373),
        ("pmrzP", 1383522816938348655),
    
        # 1. ročník, letní semestr
        ("APV", 1383523609657606265),
        ("bdmP", 1383523614548295884),
        ("MA2_M", 1383523620239970535),
        ("NUM", 1383523643782332496),
        ("PLAB", 1383523648480084039),
        ("VT", 1383523660282859605),
        ("OA2L", 1383523666880626819),
        ("OA3", 1383523673499107358),
        ("IG", 1383522832356475024),
        ("pmlP", 1383522890456240150),
        ("pmrlP", 1383522896760016928),
    ]

            ),
    (
    "Manažerská informatika - 2.ročník",
    1390043447599042782,
    [
        # 2. ročník, zimní semestr
        ("DMSM", 1383523678607773716),
        ("EC", 1383523684073083002),
        ("kvmP", 1383522973046149281),
        ("EPO", 1383523707049349192),
        ("RD", 1383523711700963430),
        ("STA1", 1383523717388308480),
        ("AOP1", 1383522977982972125),
        ("DIT", 1383523724438933734),
        ("VYF001", 1383522988665868401),
        ("VYI001", 1383522993510023238),
        ("VYN001", 1383523024082309202),
        ("PPP", 1383523732462637188),
        ("VYS001", 1383523031275802735),
        ("BuceP", 1383523738137530481),
        ("IZP", 1383523742960849079),
    
        # 2. ročník, letní semestr
        ("MRMU", 1383523767312973887),
        ("PRA", 1383523774015606886),
        ("RPICT", 1383523779376058498),
        ("STA2", 1383523784681853069),
        ("UPS", 1383523789500973201),
        ("ZFI", 1383523811718332428),    
        ("AOP2", 1383523100834009088),
        ("VYF002", 1383523134539436205),
        ("IG", 1383522832356475024),
        ("VYI002", 1383523140612657273),
        ("VYN002", 1383523140612657273),
        ("ISJ", 1383523816948498566),
        ("VYS002", 1383523151807385621),
        ("ITW", 1383523822094782594),
        ("IZG", 1383523828252147833),
    ]
    ),
    (
    "Manažerská informatika - 3. ročník",
     1390043309208113162, [
        # 3. ročník, zimní semestr
        ("DS_2", 1383523839031640066),
        ("MICT", 1383523844228386917),
        ("PIS", 1383523850318249985),
        ("PPR1", 1383523872988729375),
        ("PDS", 1383523879871578133),
        ("APSP", 1383523885223514195),
        ("VYF003", 1383523243293671515),
        ("VYI003", 1383523249752641597),
        ("rkP", 1383523890051153940),
        ("VYN003", 1383523255461351555),
        ("VYS003", 1383523261652140254),
        ("ITU", 1383523896912773202),
    
        # 3. ročník, letní semestr
        ("DIS", 1383523919276933192),
        ("PRIS", 1383523931826163814),
        ("PPR2", 1383523938696691712),
        ("PICT", 1383523944484573375),
    ]

            ),
]

# omezeni, aby si nemohl pridat uzivatel s roli Host obor s predmety; muze pouze clen s roli VUT 
def has_vut_role(): 
    async def predicate(interaction: discord.Interaction):
        vut_role = interaction.guild.get_role(1358911329737642014)
        if vut_role in interaction.user.roles:
            return True
        raise app_commands.CheckFailure("Tento příkaz může použít jen uživatel s rolí VUT.")
    return app_commands.check(predicate)

async def obor_autocomplete(interaction: discord.Interaction, current: str):
    matches = [name for name, _, _ in obory_list if current.lower() in name.lower()]
    return [app_commands.Choice(name=name, value=name) for name in matches[:25]]

class Obor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @has_vut_role()
    @app_commands.command(name="obor", description="Vyber si obor a získáš příslušnou roli.")
    @app_commands.describe(obor="Název oboru a ročníku")
    @app_commands.autocomplete(obor=obor_autocomplete)
    async def obor(self, interaction: discord.Interaction, obor: str):
        match = next((item for item in obory_list if item[0] == obor), None)
        if match is None:
            await interaction.response.send_message("❌ Obor nebyl nalezen.", ephemeral=True)
            return

        role_id = match[1]
        predmety = match[2]

        role = interaction.guild.get_role(role_id)
        if role is None:
            await interaction.response.send_message("❌ Hlavní role nebyla nalezena.", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(f"ℹ️ Už máš roli **{role.name}**.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                f"✅ Byla ti přidána role **{role.name}**.", ephemeral=True
            )

        # Tento seznam předmětů teď máme k dispozici a můžeme s ním pracovat, pokud bys chtěl např. logovat:
        print(f"Uživatel {interaction.user} zvolil obor {obor} s předměty: {[(p[0], p[1]) for p in predmety]}")

    @has_vut_role()
    @app_commands.command(name="obor_odebrat", description="Odeber si roli příslušného oboru.")
    @app_commands.describe(obor="Název oboru a ročníku")
    @app_commands.autocomplete(obor=obor_autocomplete)
    async def obor_odebrat(self, interaction: discord.Interaction, obor: str):
        match = next((item for item in obory_list if item[0] == obor), None)
        if match is None:
            await interaction.response.send_message("❌ Obor nebyl nalezen.", ephemeral=True)
            return

        role_id = match[1]
        predmety = match[2]

        role = interaction.guild.get_role(role_id)
        if role is None:
            await interaction.response.send_message("❌ Hlavní role nebyla nalezena.", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(
                f"✅ Byla ti odebrána role **{role.name}**.", ephemeral=True
            )
        else:
            await interaction.response.send_message(f"ℹ️ Nemáš roli **{role.name}**.", ephemeral=True)

        # I tady máš seznam předmětů k dispozici pro případné další akce
        print(f"Uživatel {interaction.user} odebral obor {obor} s předměty: {[(p[0], p[1]) for p in predmety]}")

    @obor.error
    @obor_odebrat.error
    async def obor_error(self, interaction: discord.Interaction, error):
        await interaction.response.send_message(
            f"❌ Došlo k chybě: {str(error)}", ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Obor(bot))

