import os
import random

import discord
from discord.ext import commands

TARGET_CHANNEL_IDS = {
    1487121536686096564,
    # 123456789012345678,
}

MIN_TRIGGER = 3
MAX_TRIGGER = 10

def reverse_text(text: str) -> str:
    return text[::-1]

class ReverseReposter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_counter = {}
        self.next_trigger = {}

    def is_enabled(self) -> bool:
        return os.getenv("ENABLE_REVERSE_REPOSTER", "true").lower() == "true"

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
        if not message.content.strip():
            return

        count = self.bump_counter(message.channel.id)
        trigger_at = self.get_next_trigger(message.channel.id)

        if count < trigger_at:
            return

        try:
            await message.reply(
                f"**{message.author.display_name} napsal pozpatku:**\n{reverse_text(message.content)}",
                mention_author=False
            )
        finally:
            self.reset_cycle(message.channel.id)

async def setup(bot: commands.Bot):
    await bot.add_cog(ReverseReposter(bot))
