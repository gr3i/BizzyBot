import discord
from discord.ext import commands

class NastavPrava(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="prirad_prava_oboru_pm1")
    @commands.has_permissions(administrator=True)
    async def prirad_prava_bak_ep1(self, ctx):
        guild = ctx.guild
        hlavni_role = guild.get_role(1390033798418399254)  # BAK-EP1
        predmetove_role_ids = [
        1383523951845703731, 1383522758658490551, 1383522770130047036,
        1383523707049349192, 1383523588631429293, 1383522776664637544,
        1383522782343598082, 1383522787821355200, 1383522811058061373,
        1383522816938348655, 1383523614548295884, 1383523958267183165,
        1383523963266662441, 1383522843593015379, 1383523093741305916,
        1383522885339054150, 1383522880347832432, 1383523985966235699,
        1383523992068948011, 1383522832356475024, 1383522890456240150,
        1383522896760016928
       
        
            
        ]

        predmetove_role_ids = set(predmetove_role_ids)
        upraveno = []

        for kanal in guild.channels:
            for role_id in predmetove_role_ids:
                role = guild.get_role(role_id)
                if not role:
                    continue

                overwrites = kanal.overwrites_for(role)
                if overwrites.view_channel:
                    bak_overwrite = kanal.overwrites_for(hlavni_role)
                    bak_overwrite.view_channel = True
                    await kanal.set_permissions(hlavni_role, overwrite=bak_overwrite)
                    upraveno.append(kanal.name)
                    break

        if upraveno:
            await ctx.send(f"✅ Role BAK-EP1 dostala přístup do kanálů: {', '.join(set(upraveno))}")
        else:
            await ctx.send("ℹ️ Nenalezeny žádné kanály s předmětovými rolemi k přiřazení.")

async def setup(bot):
    await bot.add_cog(NastavPrava(bot))

