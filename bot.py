import os
import json
import discord
from db.session import engine
from db.models import Base
Base.metadata.create_all(engine)
from discord.ext import commands
from dotenv import load_dotenv
from db.session import SessionLocal
from db.models import Verification
from utils.subject_management import predmet

# nacteni tokenu a databaze
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

# cesta k souboru pro ukladani ID zprav
REACTION_IDS_FILE = "utils/reaction_ids.json"


# nastaveni discord intents
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.reactions = True
intents.members = True
intents.message_content = True


bot = commands.Bot(command_prefix="!", intents=intents)


# check pro overeni, ze prikaz zadava pouze vlastnik
def is_owner(ctx):
    # seznam ID uzivatele, kteri maji pristup k prikazu
    allowed_ids = [685958402442133515]  # mohu pridavat vice ID, pokud chci; kazdy uzivatel zvlast 685958402442133515

    allowed_role_ids = [1358898283782602932] # pridat povoleni pro konkretni roli napr. MOD 1358898283782602932

    if ctx.author.id in allowed_ids:
        return True

    if any(role.id in allowed_role_ids for role in ctx.author.roles):
        return True
    
    return False

def funkce_vrati_false(ctx): 
    return False

# seznam ID zprav, ktere sleduju
reaction_message_ids = []

# role 
vut_roles_list = [
    ("FP - 1BC", 1359529613428134081),
    ("FP - 2BC", 1359529670109827304),
    ("FP - 3+BC", 1359529713453891627),
    ("FP - 1MGR", 1359529781582102618),
    ("FP - 2+MGR", 1359529858325287012),
    ("FP", 1358915656782844094),
    ("FEKT", 1359530289444946081),
    ("FIT", 1359530329463062678),
    ("FSI", 1359530359045230725),
    ("FA", 1359530388183191582),
    ("FAST", 1359530415970586629),
    ("FCH", 1359597408434126989),
    ("FAVU", 1389930978079801395),
    ("ÚSI", 1389931262525050930),
]

# nacti ID zprav
if os.path.exists(REACTION_IDS_FILE):
    with open(REACTION_IDS_FILE, "r") as f:
        reaction_message_ids = json.load(f)
        print(f"📌 Načteno {len(reaction_message_ids)} zpráv s reakcemi.")
else:
    print("📌 Soubor s ID zpráv nenalezen.")


@bot.command()
@commands.check(funkce_vrati_false)
async def vut_roles(ctx):
    emojis = [
    "🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯",
    "🇰", "🇱", "🇲", "🇳", "🇴", "🇵", "🇶", "🇷", "🇸", "🇹",
    "🇺", "🇻", "🇼", "🇽", "🇾", "🇿"
    ]
    message_lines = [f"{emojis[i]} {text}" for i, (text, _) in enumerate(vut_roles_list)]
    msg = await ctx.send("\n".join(message_lines))
    reaction_message_ids.append(msg.id)
    for emoji in emojis[:len(vut_roles_list)]:
        await msg.add_reaction(emoji)

    # ulozeni ID zprav
    try:
        with open(REACTION_IDS_FILE, "w") as f:
            json.dump(reaction_message_ids, f)
        print("💾 VUT role zpráva uložena.")
    except Exception as e:
        print(f"❌ Chyba při ukládání ID zpráv: {e}")

# osetreni chyby pro pripad, ze prikaz pouzije uzivatel bez prav
@vut_roles.error
async def vut_roles_error(ctx, error):
    if isinstance(error, commands.CheckFailure):                         # pokud se objevi chyba kontroly (napr. neni vlastnik)
        await ctx.send("Tento příkaz může použít pouze vlastník bota.")  # posle bot zpravu...


@bot.command()
@commands.check(is_owner)  # tato kontrola zajisti, že prikaz muze spustit pouze vlastnik
async def writeasbot(ctx, *, text: str):
    """Příkaz pro bota, aby napsal zprávu za uživatele."""
    await ctx.send(text)

@writeasbot.error
async def writeasbot_error(ctx, error):
    if isinstance(error, commands.CheckFailure):                         # pokud se objevi chyba kontroly (napr. neni vlastnik)
        await ctx.send("Na tento příkaz nemáš oprávnění.")               # pošle zpravu, ze nema opravneni

@bot.command()
@commands.check(is_owner)  # kontrola zajisti, ze prikaz muze spustit pouze vlastnik
async def writeasbot_longmessage(ctx):
    """Prikaz pro bota, aby napsal zpravu z textoveho souboru longmessage_for_bot.txt."""
    try:
        # otevreni souboru a nacteni jeho obsahu
        with open("longmessage_for_bot.txt", "r", encoding="utf-8") as file:
            content = file.read()
        
        # pokud je obsah prazdni, informujeme uzivatele
        if not content:
            await ctx.send("Soubor 'bot_write.txt' je prázdný.")
        else:
            await ctx.send(content)
    
    except FileNotFoundError:
        await ctx.send("Soubor 'bot_write.txt' nebyl nalezen.")
    except Exception as e:
        await ctx.send(f"Došlo k chybě při čtení souboru: {e}")

# osetreni chyby pro pripad, ze prikaz pouzije uzivatel bez prav
@writeasbot_longmessage.error
async def writeasbot_longmessage_error(ctx, error):
    if isinstance(error, commands.CheckFailure):                            # pokud se objevi chyba kontroly (napr. neni vlastnik)
        await ctx.send("Tento příkaz může použít pouze vlastník bota.")     # posle zpravu, ze nema opravneni


# reagovani na pridani reakce pro roli 
@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id not in reaction_message_ids:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    member = guild.get_member(payload.user_id)
    if member is None or member.bot:
        return

    emoji = str(payload.emoji)

    message = None
    for channel in guild.text_channels:
        try:
            msg = await channel.fetch_message(payload.message_id)
            if msg:
                message = msg
                break
        except (discord.NotFound, discord.Forbidden):
            continue

    if message is None:
        return

   
    if emoji in ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯",
    "🇰", "🇱", "🇲", "🇳"]:
        index = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯",
    "🇰", "🇱", "🇲", "🇳"].index(emoji)
        list_source = vut_roles_list
    else:
        return

    if index < len(list_source):
        role_id = list_source[index][1]
        role = guild.get_role(role_id)
        if role:
            await member.add_roles(role)
            print(f"✅ Přidána role {role.name} uživateli {member.name}")

            # posli DM zpravu uzivateli
            try:
                await member.send(f"✅ Byla ti přidělena role: {role.name}")
            except discord.Forbidden:
                print(f"❗ Nelze poslat DM uživateli {member.name}")

# reagovani na odebrani reakce
@bot.event
async def on_raw_reaction_remove(payload):
    if payload.message_id not in reaction_message_ids:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    member = guild.get_member(payload.user_id)
    if member is None:
        return

    emoji = str(payload.emoji)

    message = None
    for channel in guild.text_channels:
        try:
            msg = await channel.fetch_message(payload.message_id)
            if msg:
                message = msg
                break
        except (discord.NotFound, discord.Forbidden):
            continue

    if message is None:
        return


    if emoji in ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯",
    "🇰", "🇱", "🇲", "🇳"]:
        index = ["🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯",
    "🇰", "🇱", "🇲", "🇳"].index(emoji)
        list_source = vut_roles_list
    else:
        return

    if index < len(list_source):
        role_id = list_source[index][1]
        role = guild.get_role(role_id)
        if role:
            await member.remove_roles(role)
            print(f"❌ Odebrána role {role.name} uživateli {member.name}")

            # posli DM zpravu uzivateli
            try:
                await member.send(f"❌ Byla ti odebrána role: {role.name}")
            except discord.Forbidden:
                print(f"❗ Nelze poslat DM uživateli {member.name}")

@bot.command()
@commands.check(is_owner)  # only owner or allowed role
async def whois(ctx, user_id: int):
    """Vrati info o uzivateli a jeho e-mail overeni."""
    member = ctx.guild.get_member(user_id)
    if member is None:
        await ctx.send(f"Uzivatel s ID {user_id} není na tomto serveru.")
        return

    # ORM lookup
    with SessionLocal() as session:
        v = session.query(Verification).filter(Verification.user_id == user_id).order_by(Verification.id.desc()).first()

    if v is None:
        verification_status = "Ověření nebylo zahájeno."
        user_email = "Neznámý"
    else:
        verification_status = "Ověřeno" if v.verified else "Neověřeno"
        user_email = v.mail

    embed = discord.Embed(title=f"Informace o účtu {member.name}", color=discord.Color.blue())
    embed.add_field(name="Uživatelské jméno", value=member.name, inline=True)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Ověření", value=verification_status, inline=True)
    embed.add_field(name="E-mail", value=user_email, inline=True)
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)


@whois.error
async def whois_error(ctx, error):
    if isinstance(error, commands.CheckFailure):                            # pokud se objevi chyba kontroly (napr. neni vlastnik)
        await ctx.send("Tento příkaz může použít pouze vlastník bota.")     # posle zprávu, ze nema opravneni

    
@bot.command()
@commands.check(is_owner)  # only owner or allowed role
async def strip(ctx, user_id: int):
    """Smaze vsechny verifikace daneho usera a odebere role."""
    # db delete all rows for this user
    from db.session import SessionLocal
    from db.models import Verification

    with SessionLocal() as session:
        deleted = session.query(Verification)\
            .filter(Verification.user_id == user_id)\
            .delete(synchronize_session=False)  # delete all rows
        session.commit()

    # remove roles from member (keep @everyone)
    member = ctx.guild.get_member(user_id)
    if member:
        if len(member.roles) > 1:
            try:
                await member.remove_roles(*member.roles[1:])
            except discord.Forbidden:
                await ctx.send("Nemám oprávnění odebrat některé role.")
        await ctx.send(f"Smazáno z DB: {deleted} záznamů. Role byly odebrány.")
    else:
        await ctx.send(f"Smazáno z DB: {deleted} záznamů. Uživatel není na serveru.")


@strip.error
async def strip_error(ctx, error):
    if isinstance(error, commands.CheckFailure):                            # pokud se objevi chyba kontroly (napr. neni vlastnik)
        await ctx.send("Tento příkaz může použít pouze vlastník bota.")     # posle zpravu, ze nema opravneni




@bot.event
async def setup_hook():
    print("[setup_hook] start")
    guild = discord.Object(id=GUILD_ID) if GUILD_ID else None

    # 1) Smaž staré definice v guilde i globálně (pro jistotu)
    try:
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=guild)
        print("[SYNC] cleared guild commands")
    except Exception as e:
        print(f"[SYNC] guild clear failed: {e}")

    try:
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        print("[SYNC] cleared global commands")
    except Exception as e:
        print(f"[SYNC] global clear failed: {e}")

    # 2) Načti cogy
    for ext in [
        "cogs.hello",
        "cogs.botInfo",
        "cogs.verify",
        "cogs.role",
        "cogs.reviews",
        "utils.vyber_oboru",
        "utils.nastav_prava",
        "cogs.welcome_todo",
    ]:
        try:
            await bot.load_extension(ext)
            print(f"✅ Cog '{ext}' načten")
        except Exception as e:
            print(f"❌ Chyba při načítání '{ext}': {e}")

    # 3) Zaregistruj skupiny jen do guildu (rychlá propagace)
    if guild:
        # /predmet z utils.subject_management
        from utils.subject_management import predmet
        bot.tree.add_command(predmet, guild=guild)

        # /hodnoceni skupina je přidaná v cogu reviews.setup(), takže stačí jen sync
        cmds = await bot.tree.sync(guild=guild)
        print(f"[SYNC] {len(cmds)} guild cmds -> {GUILD_ID}: " + ", ".join(sorted(c.name for c in cmds)))
    else:
        # fallback: globální (pomalejší)
        cmds = await bot.tree.sync()
        print(f"[SYNC] {len(cmds)} global cmds: " + ", ".join(sorted(c.name for c in cmds)))



@bot.event
async def on_ready():
    print(f"✅ Bot prihlasen jako {bot.user} (ID: {bot.user.id})")

bot.run(TOKEN)

