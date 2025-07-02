import discord
from discord.ext import commands

class NastavPrava(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="prirad_prava_oboru BAK-EP2")
    @commands.has_permissions(administrator=True)
    async def prirad_prava_bak_ep1(self, ctx):
        guild = ctx.guild
        hlavni_role = guild.get_role(1384962230298349649)  # BAK-EP1
        predmetove_role_ids = [
        1383522977982972125, 1383523100834009088, 1383523036116025456,
        1383522983007748237, 1383523129187631164, 1383522948928770060,
        1383522934236381270, 1383523017832796183, 1383523070685352097,
        1383522938963365960, 1383522988665868401, 1383523134539436205,
        1383522993510023238, 1383523024082309202, 1383523140612657273,
        1383523031275802735, 1383523151807385621, 1383523082366615612,
        1383523041195331737, 1383522903387017348, 1383522928200515596,
        1383522973046149281, 1383523064125329470, 1383523123667927061,
        1383523075852599340, 1383523088305623040, 1383522943992074422,
        1383523093741305916
            
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

