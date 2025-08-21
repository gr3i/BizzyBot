import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ORM init
from db.session import engine
from db.models import Base

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

# create tables if not exist
Base.metadata.create_all(engine)

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def setup_hook():
    print("[setup_hook] start")
    guild = discord.Object(id=GUILD_ID) if GUILD_ID else None

    # clear only target guild and sync empty to wipe old signatures
    if guild:
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=guild)

    # load cogs
    for ext in [
        "cogs.reviews",
        "cogs.verify",
    ]:
        try:
            await bot.load_extension(ext)
            print(f"✅ Cog '{ext}' nacten")
        except Exception as e:
            print(f"❌ Chyba pri nacitani '{ext}': {e}")

    # final guild sync
    if guild:
        cmds = await bot.tree.sync(guild=guild)
        print(f"[SYNC] {len(cmds)} commands -> guild {GUILD_ID}: " + ", ".join(sorted(c.name for c in cmds)))
    else:
        cmds = await bot.tree.sync()
        print(f"[SYNC] {len(cmds)} global commands: " + ", ".join(sorted(c.name for c in cmds)))

@bot.event
async def on_ready():
    print(f"✅ Bot prihlasen jako {bot.user} (ID: {bot.user.id})")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN chybi v .env")
bot.run(TOKEN)

