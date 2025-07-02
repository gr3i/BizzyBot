import discord
from discord.ext import commands

class NastavPrava(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="prirad_prava_oboru_min1")
    @commands.has_permissions(administrator=True)
    async def prirad_prava_bak_ep1(self, ctx):
        guild = ctx.guild
        hlavni_role = guild.get_role( 1390043447599042782   )  # BAK-EP1
        predmetove_role_ids = [

1383523678607773716, 1383523684073083002, 1383522973046149281,
1383523707049349192, 1383523711700963430, 1383523717388308480,
1383522977982972125, 1383523724438933734, 1383522988665868401,
1383522993510023238, 1383523024082309202, 1383523732462637188,
1383523031275802735, 1383523738137530481, 1383523742960849079,
1383523767312973887, 1383523774015606886, 1383523779376058498,
1383523784681853069, 1383523789500973201, 1383523811718332428,
1383523100834009088, 1383523134539436205, 1383522832356475024,
1390037910996123818, 1383523140612657273, 1383523816948498566,
1383523151807385621, 1383523822094782594, 1383523828252147833
        
       
        
            
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

