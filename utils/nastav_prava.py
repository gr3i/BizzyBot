import discord
from discord.ext import commands

class NastavPrava(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="prirad_prava_oboru_uad1")
    @commands.has_permissions(administrator=True)
    async def prirad_prava_bak_ep1(self, ctx):
        guild = ctx.guild
        hlavni_role = guild.get_role(    1390049660076298290  )  # BAK-EP1
        predmetove_role_ids = [


1383524320525160489, 1383524326426280017, 1383524350879072466,
1383524356394586316, 1383524361805369367, 1383524367446708375,
1383524372941115483, 1383523193213681846, 1383523209252438036,
1383523243293671515, 1383523249752641597, 1383523255461351555,
1383523261652140254, 1383524396743790653, 1383524402242523248,
1383524407938387978, 1383523285324664872, 1383524413596631070




        
       
        
            
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

