import discord
from discord.ext import commands

class PinOnReacts(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "📌":
            return

        # ignoruj boty
        if payload.member and payload.member.bot:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        channel = guild.get_channel(payload.channel_id)
        if channel is None:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return
        except discord.Forbidden:
            # bot nema Read Message History / pristup do kanalu
            return

        if message.pinned:
            return

        # spocti 📌 reakce
        for reaction in message.reactions:
            if str(reaction.emoji) == "📌" and reaction.count >= 5:
                try:
                    await message.pin(reason="5× 📌 reakce")
                except discord.Forbidden:
                    # bot nema Manage Messages
                    return
                break


async def setup(bot: commands.Bot):
    await bot.add_cog(PinOnReacts(bot))

