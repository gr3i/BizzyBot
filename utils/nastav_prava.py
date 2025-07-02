import discord
from discord.ext import commands

class NastavPrava(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="prirad_prava_oboru_min1")
    @commands.has_permissions(administrator=True)
    async def prirad_prava_bak_ep1(self, ctx):
        guild = ctx.guild
        hlavni_role = guild.get_role( 1390043190702112939    )  # BAK-EP1
        predmetove_role_ids = [

1383523555203088394, 1383522758658490551, 1383523560433385594,
1383523583682154576, 1383523588631429293, 1383523595233529957,
1383523603206635701, 1383522787821355200, 1383522811058061373,
1383522816938348655, 1383523609657606265, 1383523614548295884,
1383523620239970535, 1383523643782332496, 1383523648480084039,
1383523660282859605, 1383523666880626819, 1383523673499107358,
1383522832356475024, 1383522890456240150, 1383522896760016928
        
       
        
            
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

