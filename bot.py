# bot.py — minimalni jistota

import os
import json
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ORM init
from db.session import engine
from db.models import Base
Base.metadata.create_all(engine)

# ---- config ----
load_dotenv()
TOKEN    = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "1357455204391321712"))  # uprav/ENV

# intents
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.reactions = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# rychly test slash
@bot.tree.command(name="ping", description="test")
async def ping_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("pong", ephemeral=True)

@bot.event
async def setup_hook():
    print("[setup_hook] start")

    # 1) load cogy PRED syncem
    extensions = [
        "cogs.hello",
        "cogs.botInfo",
        "cogs.verify",
        "cogs.role",
        "cogs.reviews",         # tvoje reviews (registruje groupu do guildy)
        "utils.vyber_oboru",
        "utils.nastav_prava",
        "cogs.sort_categories", # ujisti se, ze soubor je 'cogs/sort_categories.py'
    ]
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            print(f"✅ Cog '{ext}' nacten")
        except Exception as e:
            print(f"❌ Chyba pri nacitani '{ext}': {e}")

    # 2) per-guild sync (okamzity a spolehlivy)
    guild = discord.Object(id=GUILD_ID)
    # pokud mas dalsi extra prikazy mimo cogy, pridej sem jako guild-scoped:
    # from utils.subject_management import predmet
    # bot.tree.add_command(predmet, guild=guild)

    # pro jistotu tvrdý resync: vycistit a znovu nahrat
    bot.tree.clear_commands(guild=guild)
    cmds = await bot.tree.sync(guild=guild)
    print(f"[SYNC] {len(cmds)} commands -> guild {GUILD_ID}: " + ", ".join(sorted(c.name for c in cmds)))

@bot.event
async def on_ready():
    print(f"✅ Bot prihlasen jako {bot.user} (ID: {bot.user.id})")

# (tvé textové prikazy whois/strip atd. muzes nechat dole beze zmen)

bot.run(TOKEN)

