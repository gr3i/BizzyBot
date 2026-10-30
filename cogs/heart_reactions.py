import logging

import discord
from discord.ext import commands


logger = logging.getLogger(__name__)

# ID kanalu
HEART_CHANNEL_IDS = {
    1422505714332602459,
    1441386334290841723,
    1413228774710841464
}

HEART_EMOJI = "❤️"


class HeartReactions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id not in HEART_CHANNEL_IDS:
            return

        if self.bot.user is not None and message.author.id == self.bot.user.id:
            return

        if message.guild is None:
            return

        me = message.guild.me
        if me is None:
            return

        permissions = message.channel.permissions_for(me)

        if not (
            permissions.view_channel
            and permissions.read_message_history
            and permissions.add_reactions
        ):
            return

        try:
            await message.add_reaction(HEART_EMOJI)

        except (discord.Forbidden, discord.NotFound):
            logger.debug(
                "Nelze pridat srdicko na zpravu %s v kanalu %s.",
                message.id,
                message.channel.id,
            )

        except discord.HTTPException:
            logger.exception(
                "Chyba pri pridavani srdicka na zpravu %s.",
                message.id,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(HeartReactions(bot))