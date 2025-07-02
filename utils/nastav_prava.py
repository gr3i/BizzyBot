import discord
from discord.ext import commands

class NastavPrava(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="prirad_prava_oboru_pm2")
    @commands.has_permissions(administrator=True)
    async def prirad_prava_bak_ep1(self, ctx):
        guild = ctx.guild
        hlavni_role = guild.get_role( 1390033955776106546) # BAK-EP1
        predmetove_role_ids = [
        1383523157482279012, 1383523999245533195, 1383524004664709242,
        1383524015527952515, 1383522943992074422, 1383522973046149281,
        1383524020527566878, 1383523738137530481, 1383522977982972125,
        1383522988665868401, 1383522993510023238, 1383523024082309202,
        1383523031275802735, 1383524026944716981, 1383523064125329470,
        1383524033957466204, 1383524056506306601, 1383524062730649610,
        1383524068300685463, 1383524074332098700, 1383524086474604598,
        1383523082366615612, 1383523811718332428, 1383523100834009088,
        1383523134539436205, 1383523140612657273, 1383523151807385621,
        1383522832356475024, 1390037910996123818
        
       
        
            
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

