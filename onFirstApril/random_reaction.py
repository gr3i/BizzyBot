import os
import random

import discord
from discord.ext import commands


TARGET_CHANNEL_IDS = {
    1487121536686096564, 
}

MIN_TRIGGER = 2
MAX_TRIGGER = 5

REACTIONS = [
    "🚿",
    "<:Koteseni:1156329924764901406>",
    "<a:hutaoris:1441556265900965968>",
    "<:KannaSip:1359694460807811344>",
    "<:cheemsBlush:1439311238097015009>",
    "<:sweatduck:1359699350544056400>",
    "<:koteseni:1361038813719302175>",
]


class RandomReactor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_counter = {}
        self.next_trigger = {}

    def is_enabled(self) -> bool:
        return os.getenv("ENABLE_RANDOM_REACTOR", "true").lower() == "true"

    def get_next_trigger(self, channel_id: int) -> int:
        if channel_id not in self.next_trigger:
            self.next_trigger[channel_id] = random.randint(MIN_TRIGGER, MAX_TRIGGER)
        return self.next_trigger[channel_id]

    def bump_counter(self, channel_id: int) -> int:
        current = self.message_counter.get(channel_id, 0) + 1
        self.message_counter[channel_id] = current
        return current

    def reset_cycle(self, channel_id: int):
        self.message_counter[channel_id] = 0
        self.next_trigger[channel_id] = random.randint(MIN_TRIGGER, MAX_TRIGGER)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.is_enabled():
            return

        if message.author.bot:
            return

        if message.channel.id not in TARGET_CHANNEL_IDS:
            return

        count = self.bump_counter(message.channel.id)
        trigger_at = self.get_next_trigger(message.channel.id)

        if count < trigger_at:
            return

        try:
            reaction = random.choice(REACTIONS)
            await message.reply(reaction, mention_author=False)
            print(f"[random_reactor] Replied in channel {message.channel.id} with {reaction}")
        except discord.Forbidden:
            print("[random_reactor] Missing permissions to send messages.")
        except discord.HTTPException as e:
            print(f"[random_reactor] Discord error: {e}")
        except Exception as e:
            print(f"[random_reactor] Unexpected error: {e}")
        finally:
            self.reset_cycle(message.channel.id)


async def setup(bot: commands.Bot):
    await bot.add_cog(RandomReactor(bot))
