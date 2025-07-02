import discord
from discord.ext import commands

class NastavPrava(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="prirad_prava_oboru_ep2")
    @commands.has_permissions(administrator=True)
    async def prirad_prava_bak_ep1(self, ctx):
        guild = ctx.guild
        hlavni_role = guild.get_role(1384962548733972600)  # BAK-EP1
        predmetove_role_ids = [
        1383523204030529617, 1383523290894569553, 1383523232849858570,
        1383523297546735667, 1383523302575964270, 1383523162569834657,
        1383523187806965771, 1383523198024421466, 1383523238738399353,
        1383523243293671515, 1383523249752641597, 1383523255461351555,
        1383523261652140254, 1383523285324664872, 1383523157482279012,
        1383523193213681846, 1383523209252438036
        
            
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

