import os
import discord
from db.session import engine
from db.models import Base
Base.metadata.create_all(engine)
from discord.ext import commands
from dotenv import load_dotenv
from db.session import SessionLocal
from db.models import Verification

# kvuli VUT API 
from config import Config
from services.vut_api import VutApiClient

# nacteni tokenu a databaze
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))


config = Config()

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

    allowed_role_ids = [1358898283782602932,1359508102222975087, 1370841996977246218, 1370842282084925541] # pridat povoleni pro konkretni roli napr. MOD 1358898283782602932

    if ctx.author.id in allowed_ids:
        return True

    if any(role.id in allowed_role_ids for role in ctx.author.roles):
        return True
    
    return False


@bot.command()
@commands.check(is_owner)  # tato kontrola zajisti, že prikaz muze spustit pouze vlastnik
async def writeasbot(ctx, *, text: str):
    """Příkaz pro bota, aby napsal zprávu za uživatele."""
    await ctx.send(text)

@writeasbot.error
async def writeasbot_error(ctx, error):
    if isinstance(error, commands.CheckFailure):                         # pokud se objevi chyba kontroly (napr. neni vlastnik)
        await ctx.send("Na tento příkaz nemáš oprávnění.")               # posle zpravu, ze nema opravneni

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
            await ctx.send("Soubor 'longmessage_for_bot.txt' je prázdný.")
        else:
            await ctx.send(content)
    
    except FileNotFoundError:
        await ctx.send("Soubor 'longmessage_for_bot.txt' nebyl nalezen.")
    except Exception as e:
        await ctx.send(f"Došlo k chybě při čtení souboru: {e}")

# osetreni chyby pro pripad, ze prikaz pouzije uzivatel bez prav
@writeasbot_longmessage.error
async def writeasbot_longmessage_error(ctx, error):
    if isinstance(error, commands.CheckFailure):                            # pokud se objevi chyba kontroly (napr. neni vlastnik)
        await ctx.send("Tento příkaz může použít pouze vlastník bota.")     # posle zpravu, ze nema opravneni

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

    bot.vut_api = VutApiClient(api_key=config.vut_api_key, owner_id=config.owner_id)
    await bot.vut_api.start() 

    guild = discord.Object(id=GUILD_ID)

    for ext in [
        "cogs.hello",
        "cogs.botInfo",
        "cogs.verify",
        "cogs.role",
        "cogs.reviews",
        "utils.vyber_oboru",
        "cogs.welcome_todo",
        "cogs.pozvanka",
        "cogs.send_image",
        "cogs.keyword_helper",
        "cogs.jail_cleanup",
        "cogs.room",
        "cogs.on_raw_reaction_add",
        "cogs.bookmark_dm",
        "cogs.role_spolku",
    ]:
        try:
            await bot.load_extension(ext)
            print(f"Cog '{ext}' načten")
        except Exception as e:
            print(f"Chyba při načítání '{ext}': {e}")


    # zkopiruj globalni prikazy (napr. z verify/role/botInfo/hello) do guildy
    bot.tree.copy_global_to(guild=guild)

    # sync pouze pro guildu (rychly, bez cekani) <-- snad je to pravda...
    cmds = await bot.tree.sync(guild=guild)
    print(f"[SYNC] {len(cmds)} commands -> {GUILD_ID}: " + ", ".join(sorted(c.name for c in cmds)))



@bot.event
async def on_ready():
    print(f"Bot prihlasen jako {bot.user} (ID: {bot.user.id})")

bot.run(TOKEN)


