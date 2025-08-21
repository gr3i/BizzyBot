import os
import discord
from discord import app_commands
from discord.ext import commands

# --- KONFIG ---
TOKEN = os.getenv("DISCORD_TOKEN")             # musí být v .env
GUILD_ID = 1357455204391321712                 # TVOJE guilda (pevně, ať obejdeme .env)

# --- BOT / INTENTS ---
intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- GLOBÁLNÍ HANDLER CHYB (ať vidíme proč by to spadlo) ---
@bot.tree.error
async def on_tree_error(interaction: discord.Interaction, error: Exception):
    try:
        await interaction.response.send_message(f"Chyba: {error}", ephemeral=True)
    except discord.InteractionResponded:
        await interaction.followup.send(f"Chyba: {error}", ephemeral=True)

# --- /ping (rychlý test) ---
@bot.tree.command(name="ping", description="test ping")
async def ping_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("pong", ephemeral=True)

# --- /hodnoceni test (skupina + 1 příkaz) ---
hodnoceni = app_commands.Group(name="hodnoceni", description="Test skupina")

@hodnoceni.command(name="test", description="Vrati OK – test")
async def hodnoceni_test(interaction: discord.Interaction):
    await interaction.response.send_message("OK (hodnoceni/test)", ephemeral=True)

# --- Registrace a tvrdý per-guild sync ---
@bot.event
async def setup_hook():
    print("[setup_hook] start")
    guild = discord.Object(id=GUILD_ID)

    # Vyčisti aktuální guild příkazy a zaregistruj znova
    bot.tree.clear_commands(guild=guild)        # DŮLEŽITÉ kvůli starým signaturám
    bot.tree.add_command(hodnoceni, guild=guild)
    bot.tree.add_command(ping_cmd, guild=guild)

    cmds = await bot.tree.sync(guild=guild)
    print(f"[SYNC] {len(cmds)} commands -> guild {GUILD_ID}: " + ", ".join(c.name for c in cmds))

@bot.event
async def on_ready():
    print(f"✅ Bot přihlášen jako {bot.user} (ID: {bot.user.id})")

# --- START ---
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN není nastaven!")
bot.run(TOKEN)

