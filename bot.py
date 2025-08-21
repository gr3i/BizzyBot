import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ORM init – tabulky vytvoříme při startu
from db.session import engine
from db.models import Base
Base.metadata.create_all(engine)

load_dotenv()
TOKEN    = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.reactions = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def setup_hook():
    print("[setup_hook] start")

    # 1) načti cogy (reviews registruje groupu v setupu)
    extensions = [
        "cogs.hello",
        "cogs.botInfo",
        "cogs.verify",
        "cogs.role",
        "cogs.reviews",         # DŮLEŽITÉ: musí být načteno před syncem
        "utils.vyber_oboru",
        "utils.nastav_prava",
        "cogs.sort_categories",
    ]
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            print(f"✅ Cog '{ext}' nacten")
        except Exception as e:
            print(f"❌ Chyba pri nacitani '{ext}': {e}")

    # 2) tvrdý re-sync: smaž staré příkazy a nahraj nové
    guild = discord.Object(id=GUILD_ID) if GUILD_ID else None

    # vymaž GUILD-scoped
    if guild:
        bot.tree.clear_commands(guild=guild)
        print(f"[sync] cleared GUILD commands for {GUILD_ID}")

    # vymaž GLOBAL (v této verzi lib má clear_commands povinný keyword 'guild')
    bot.tree.clear_commands(guild=None)
    print("[sync] cleared GLOBAL commands")

    # re-sync do guildy (okamžité)
    if guild:
        cmds = await bot.tree.sync(guild=guild)
        print(f"[SYNC] {len(cmds)} commands -> guild {GUILD_ID}: " +
              ", ".join(sorted(c.name for c in cmds)))
    else:
        cmds = await bot.tree.sync()
        print(f"[SYNC] {len(cmds)} global commands")

@bot.event
async def on_ready():
    print(f"✅ Bot prihlasen jako {bot.user} (ID: {bot.user.id})")

# owner helper: ruční tvrdý resync, kdyby sis to chtěl pustit bez restartu
OWNER_IDS = {685958402442133515}

@bot.command()
async def reslash(ctx):
    if ctx.author.id not in OWNER_IDS:
        return await ctx.reply("no perms")
    guild = discord.Object(id=GUILD_ID) if GUILD_ID else None
    if guild:
        bot.tree.clear_commands(guild=guild)
    bot.tree.clear_commands(guild=None)
    if guild:
        cmds = await bot.tree.sync(guild=guild)
        await ctx.reply(f"resynced {len(cmds)} guild commands")
    else:
        cmds = await bot.tree.sync()
        await ctx.reply(f"resynced {len(cmds)} global commands")

bot.run(TOKEN)

