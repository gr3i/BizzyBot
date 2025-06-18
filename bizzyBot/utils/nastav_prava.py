import discord
from discord import app_commands
from discord.ext import commands

@commands.command(name="prirad_prava_bak_ep1")
@commands.has_permissions(administrator=True)
async def prirad_prava_bak_ep1(self, ctx):
    guild = ctx.guild
    hlavni_role = guild.get_role(1384961946046042284)  # BAK-EP1
    predmetove_role_ids = [
        1383522776664637544, 1383522880347832432, 1383522782343598082,
        1383522885339054150, 1383522832356475024, 1383522822713905366,
        1383522839239327874, 1383522736986656950, 1383522770130047036,
        1383522843593015379, 1383522746167857202, 1383522758658490551,
        1383522850505494710, 1383522765092425788, 1383522890456240150,
        1383522896760016928, 1383522816938348655, 1383522811058061373,
        1383522787821355200, 1383522873120919718
    ]

    predmetove_role_ids = set(predmetove_role_ids)
    upraveno = []

    for kanal in guild.channels:
        # Zkontroluj, jestli kanál má oprávnění pro některou předmětovou roli
        for role_id in predmetove_role_ids:
            role = guild.get_role(role_id)
            if not role:
                continue

            overwrites = kanal.overwrites_for(role)
            if overwrites.view_channel:  # Pokud tahle role vidí kanál
                # Přidáme stejný overwrite pro BAK-EP1
                bak_overwrite = kanal.overwrites_for(hlavni_role)
                bak_overwrite.view_channel = True
                await kanal.set_permissions(hlavni_role, overwrite=bak_overwrite)
                upraveno.append(kanal.name)
                break  # Stačí jedna shoda

    if upraveno:
        await ctx.send(f"✅ Role BAK-EP1 dostala přístup do kanálů: {', '.join(set(upraveno))}")
    else:
        await ctx.send("ℹ️ Nenalezeny žádné kanály s předmětovými rolemi k přiřazení.")
async def setup(bot):
    await bot.add_cog(NastavPrava(bot))

