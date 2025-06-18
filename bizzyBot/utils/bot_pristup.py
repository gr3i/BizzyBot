import discord
from discord.ext import commands

class BotPristup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pridej_pristup_botovi")
    @commands.has_permissions(administrator=True)
    async def pridej_pristup_botovi(self, ctx):
        guild = ctx.guild
        bot_member = guild.me  # Bot jako member
        bot_role = bot_member.top_role  # Nejvyšší role bota

        predmetove_role_ids = [
            1383522736986656950, 1383522746167857202, 1383522758658490551,
            1383522765092425788, 1383522770130047036, 1383522776664637544,
            1383522782343598082, 1383522787821355200, 1383522811058061373,
            1383522816938348655, 1383522822713905366, 1383522832356475024,
            1383522839239327874, 1383522843593015379, 1383522850505494710,
            1383522873120919718, 1383522880347832432, 1383522885339054150,
            1383522890456240150, 1383522896760016928,  # ... můžeš přidat všechny další ID z tvého seznamu
            # Pro zkrácení jsem dal část, doplň zbytek nebo celý seznam
        ]

        upraveno = []

        for kanal in guild.channels:
            for role_id in predmetove_role_ids:
                role = guild.get_role(role_id)
                if not role:
                    continue

                overwrites = kanal.overwrites_for(role)
                if overwrites.view_channel:
                    bot_overwrite = kanal.overwrites_for(bot_role)
                    bot_overwrite.view_channel = True
                    try:
                        await kanal.set_permissions(bot_role, overwrite=bot_overwrite)
                        upraveno.append(kanal.name)
                    except discord.Forbidden:
                        await ctx.send(f"❌ Bot nemá právo upravit kanál: {kanal.name}")
                    except Exception as e:
                        await ctx.send(f"⚠️ Chyba u kanálu {kanal.name}: {e}")
                    break  # Stačí jedna role s přístupem

        if upraveno:
            await ctx.send(f"✅ Bot dostal přístup do kanálů: {', '.join(set(upraveno))}")
        else:
            await ctx.send("ℹ️ Nebyly nalezeny žádné kanály k úpravě.")

async def setup(bot):
    await bot.add_cog(BotPristup(bot))

