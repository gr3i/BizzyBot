import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ORM init (vytvor tabulky hned po startu)
from db.session import engine
from db.models import Base

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

Base.metadata.create_all(engine)

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.reactions = True
intents.message_content = True  # pokud nepotrebujes text cmd, muzes vypnout

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def setup_hook():
    print("[setup_hook] start")

    # nacti cogy PRED syncem
    exts = [
        "cogs.verify",
        "cogs.role",
        "cogs.reviews",     # tento cog sám zaregistruje groupu do guildy
        "cogs.hello",
        "cogs.botInfo",
        "utils.vyber_oboru",
        "utils.nastav_prava",
        # "cogs.sort_categories",  # zapni az bude 100% bez chyby
    ]
    for ext in exts:
        try:
            await bot.load_extension(ext)
            print(f"✅ cog loaded: {ext}")
        except Exception as e:
            print(f"❌ cog load failed: {ext}: {e}")

    # per-guild sync (staci jednou; zbytek resi reviews.setup)
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        cmds = await bot.tree.sync(guild=guild)
        print(f"[SYNC] {len(cmds)} commands -> guild {GUILD_ID}")
    else:
        cmds = await bot.tree.sync()
        print(f"[SYNC] {len(cmds)} global commands")


@bot.event
async def on_ready():
    print(f"Bot prihlasen jako {bot.user} (ID: {bot.user.id})")


bot.run(TOKEN)

