import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ORM init (vytvoreni tabulek)
from db.session import engine
from db.models import Base
Base.metadata.create_all(engine)

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

gid_raw = os.getenv("GUILD_ID", "").strip()
try:
    GUILD_ID = int(gid_raw) if gid_raw else 0
except ValueError:
    GUILD_ID = 0

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def setup_hook():
    print("[setup_hook] start")

    # nacti cogy
    for ext in [
        "cogs.hello",
        "cogs.botInfo",
        "cogs.verify",
        "cogs.role",
        "cogs.reviews",
        "utils.vyber_oboru",
        "utils.nastav_prava",
        "cogs.sort_categories",  # ujisti se, ze soubor je cogs/sort_categories.py
    ]:
        try:
            await bot.load_extension(ext)
            print(f"✅ Cog '{ext}' nacten")
        except Exception as e:
            print(f"❌ Chyba pri nacitani '{ext}': {e}")

    # per-guild sync (bez clear_commands -> v 2.x vyzaduje guild=)
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        cmds = await bot.tree.sync(guild=guild)
        print(f"[SYNC] {len(cmds)} commands -> guild {GUILD_ID}: " + ", ".join(sorted(c.name for c in cmds)))
    else:
        cmds = await bot.tree.sync()
        print(f"[SYNC] {len(cmds)} commands -> global: " + ", ".join(sorted(c.name for c in cmds)))

@bot.event
async def on_ready():
    print(f"✅ Bot prihlasen jako {bot.user} (ID: {bot.user.id}), GUILD_ID={GUILD_ID}")

bot.run(TOKEN)

