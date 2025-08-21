# bot.py — stabilniii start + per-guild sync

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# --- ORM init (nechava tabulky vytvorit pri startu) ---
from db.session import engine
from db.models import Base
Base.metadata.create_all(engine)

# --- Config & ENV ---
load_dotenv()

def get_guild_id(default: int) -> int:
    raw = os.getenv("GUILD_ID", "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"[WARN] GUILD_ID='{raw}' neni cislo, pouzivam default {default}")
        return default

TOKEN    = os.getenv("DISCORD_TOKEN")              # musi byt v .env
GUILD_ID = get_guild_id(1357455204391321712)       # uprav default na svuj server

# --- Discord intents ---
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.reactions = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# jednoduchy testovaci slash (pomuze overit sync)
@bot.tree.command(name="ping", description="test")
async def ping_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("pong", ephemeral=True)

@bot.event
async def setup_hook():
    print("[setup_hook] start")

    guild = discord.Object(id=GUILD_ID)

    # 1) vycistit lokalni strom pro guildu (POZOR: pred loadem cogů)
    bot.tree.clear_commands(guild=guild)

    # 2) nacist cogy (tady se do stromu zaregistruji slash prikazy)
    extensions = [
        "cogs.hello",
        "cogs.botInfo",
        "cogs.verify",
        "cogs.role",
        "cogs.reviews",
        "utils.vyber_oboru",
        "utils.nastav_prava",
       
    ]
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            print(f"✅ Cog '{ext}' nacten")
        except Exception as e:
            print(f"❌ Chyba pri nacitani '{ext}': {e}")

    # 3) per-guild SYNC (zapise aktualni definice)
    cmds = await bot.tree.sync(guild=guild)
    print(f"[SYNC] {len(cmds)} commands -> guild {GUILD_ID}: " + ", ".join(sorted(c.name for c in cmds)))


@bot.event
async def on_ready():
    print(f"✅ Bot prihlasen jako {bot.user} (ID: {bot.user.id})")

# --- start ---
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN neni nastaven v .env")

bot.run(TOKEN)

