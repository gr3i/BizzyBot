import os
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
# PRO TEST SI TADY NASTAV PEVNE ID GUILDY (abychom vyřadili .env z rovnice)
GUILD_ID = 1357455204391321712  # <<-- tvoje guilda

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.tree.command(name="ping", description="test ping")
async def ping_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("pong", ephemeral=True)

@bot.event
async def setup_hook():
    # načti pouze reviews (test), nic víc
    try:
        await bot.load_extension("cogs.reviews")
        print("✅ loaded cogs.reviews")
    except Exception as e:
        print("❌ load reviews:", e)

    # tvrdý per-guild sync (okamžitě viditelný)
    guild = discord.Object(id=GUILD_ID)
    cmds = await bot.tree.sync(guild=guild)
    print(f"[SYNC] {len(cmds)} commands for guild {GUILD_ID}: " + ", ".join(c.name for c in cmds))

@bot.event
async def on_ready():
    print(f"✅ logged in as {bot.user} ({bot.user.id})")

bot.run(TOKEN)

