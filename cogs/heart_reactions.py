import asyncio
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

# cas do odebrani reakce v sekundach
HEART_REMOVE_DELAY = 3600


class HeartReactions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.pending_removals = {}

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
                "Nelze pridat srdicko na zpravu %s.",
                message.id,
            )

        except discord.HTTPException:
            logger.exception(
                "Chyba pri pridavani srdicka na zpravu %s.",
                message.id,
            )

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self, payload: discord.RawReactionActionEvent
    ):
        if payload.channel_id not in HEART_CHANNEL_IDS:
            return

        if str(payload.emoji) != HEART_EMOJI:
            return

        if self.bot.user is None:
            return

        if payload.user_id == self.bot.user.id:
            return

        if payload.guild_id is None:
            return

        key = (payload.channel_id, payload.message_id)

        if key in self.pending_removals:
            return

        task = asyncio.create_task(
            self.remove_heart_after_delay(
                payload.channel_id,
                payload.message_id,
            )
        )

        self.pending_removals[key] = task

        task.add_done_callback(
            lambda finished_task, k=key: self.cleanup_task(
                k, finished_task
            )
        )

    def cleanup_task(self, key, task):
        if self.pending_removals.get(key) is task:
            self.pending_removals.pop(key, None)

    async def remove_heart_after_delay(
        self, channel_id: int, message_id: int
    ):
        await asyncio.sleep(HEART_REMOVE_DELAY)

        try:
            channel = self.bot.get_channel(channel_id)

            if channel is None:
                channel = await self.bot.fetch_channel(channel_id)

            message = await channel.fetch_message(message_id)

            for reaction in message.reactions:
                if str(reaction.emoji) != HEART_EMOJI:
                    continue

                # bot musi mit vlastni reakci
                if not reaction.me:
                    return

                # srdicko musi mit alespon jeden dalsi uzivatel
                if reaction.count < 2:
                    return

                await message.remove_reaction(
                    HEART_EMOJI,
                    self.bot.user,
                )

                logger.info(
                    "Odebrano srdicko ze zpravy %s v kanalu %s.",
                    message_id,
                    channel_id,
                )
                return

        except (discord.Forbidden, discord.NotFound):
            logger.debug(
                "Nelze odebrat srdicko ze zpravy %s.",
                message_id,
            )

        except discord.HTTPException:
            logger.exception(
                "Chyba pri odebirani srdicka ze zpravy %s.",
                message_id,
            )

    def cog_unload(self):
        for task in self.pending_removals.values():
            task.cancel()

        self.pending_removals.clear()


async def setup(bot: commands.Bot):
    await bot.add_cog(HeartReactions(bot))