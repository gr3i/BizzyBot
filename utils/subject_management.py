# utils/subject_management.py
import os
import discord
from discord import app_commands

# seznam predmetu a jejich roli (zkráceno – nech svůj aktuální seznam)
subject_list = [
    ("epP", 1383522736986656950),
    # ... celý tvůj seznam ...
]

ALLOWED_ROLE_ID = 1358911329737642014

predmet = app_commands.Group(
    name="predmet",
    description="Přidání a odebrání předmětu"
)

async def predmet_autocomplete(interaction: discord.Interaction, current: str):
    matches = [name for name, _ in subject_list if current.lower() in name.lower()]
    return [app_commands.Choice(name=name, value=name) for name in matches[:25]]

@predmet.command(name="pridat", description="Vyber si předmět – role se přidá.")
@app_commands.guild_only()
@app_commands.describe(predmet="Název předmětu")
@app_commands.autocomplete(predmet=predmet_autocomplete)
@app_commands.checks.has_role(ALLOWED_ROLE_ID)
async def predmet_pridat(interaction: discord.Interaction, predmet: str):
    role_id = next((rid for name, rid in subject_list if name == predmet), None)
    if role_id is None:
        await interaction.response.send_message("Předmět nebyl nalezen.", ephemeral=True)
        return
    role = interaction.guild.get_role(role_id)
    if not role:
        await interaction.response.send_message("Role nebyla nalezena.", ephemeral=True)
        return
    if role in interaction.user.roles:
        await interaction.response.send_message("Tuto roli už máš.", ephemeral=True)
    else:
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"✅ Byla ti přidána role: **{role.name}**", ephemeral=True)

@predmet.command(name="odebrat", description="Vyber si předmět – role se odebere.")
@app_commands.guild_only()
@app_commands.describe(predmet="Název předmětu")
@app_commands.autocomplete(predmet=predmet_autocomplete)
@app_commands.checks.has_role(ALLOWED_ROLE_ID)
async def predmet_odebrat(interaction: discord.Interaction, predmet: str):
    role_id = next((rid for name, rid in subject_list if name == predmet), None)
    if role_id is None:
        await interaction.response.send_message("Předmět nebyl nalezen.", ephemeral=True)
        return
    role = interaction.guild.get_role(role_id)
    if not role:
        await interaction.response.send_message("Role nebyla nalezena.", ephemeral=True)
        return
    if role in interaction.user.roles:
        await interaction.user.remove_roles(role)
        await interaction.response.send_message(f"❌ Byla ti odebrána role: **{role.name}**", ephemeral=True)
    else:
        await interaction.response.send_message("Tuto roli nemáš.", ephemeral=True)

@predmet.error
@predmet_odebrat.error
async def predmet_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingRole):
        await interaction.response.send_message("❌ Nemáš oprávnění použít tento příkaz.", ephemeral=True)

# >>> DŮLEŽITÉ: extension entry-point <<<
async def setup(bot):
    GUILD_ID = int(os.getenv("GUILD_ID", "0"))
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.add_command(predmet, guild=guild)
        print(f"[subjects] group 'predmet' registered for guild {GUILD_ID}")
    else:
        bot.tree.add_command(predmet)
        print("[subjects] group 'predmet' registered (global)")

