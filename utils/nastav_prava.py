import discord
from discord.ext import commands

class NastavPrava(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="prirad_prava_oboru_uad1")
    @commands.has_permissions(administrator=True)
    async def prirad_prava_bak_ep1(self, ctx):
        guild = ctx.guild
        hlavni_role = guild.get_role(   1390049614534803626   )  # BAK-EP1
        predmetove_role_ids = [


1383522903387017348, 1383524257115537540, 1383524279978557510,
1383522943992074422, 1383524286077210624, 1383522928200515596,
1383522765092425788, 1383524020527566878, 1383522977982972125,
1383522988665868401, 1383522993510023238, 1383523024082309202,
1383523031275802735, 1383524292691497061, 1383523041195331737,
1383524302573539398, 1383524307740790937, 1383524313344376832,
1383523123667927061, 1383523082366615612, 1383523064125329470,
1383523088305623040, 1383523075852599340, 1383523093741305916,
1383523100834009088, 1383523134539436205, 1390037910996123818,
1383523140612657273, 1383523151807385621


        
       
        
            
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

