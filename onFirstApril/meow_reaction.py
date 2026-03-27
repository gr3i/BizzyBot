import discord
from discord.ext import commands


ALLOWED_WORDS = ("mňau", "mnau", "meow")
TARGET_CHANNEL_IDS = {
    1487121536686096564,
    # sem muzes pridat dalsi channel ID
}

REACTION_EMOJI = "<:koteseni:1361038813719302175>"


class MeowReaction(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def is_target_channel(self, channel_id: int) -> bool:
        return not TARGET_CHANNEL_IDS or channel_id in TARGET_CHANNEL_IDS

    def contains_allowed_word(self, content: str) -> bool:
        lowered = content.casefold()
        return any(word in lowered for word in ALLOWED_WORDS)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            await self.bot.process_commands(message)
            return

        if not self.is_target_channel(message.channel.id):
            await self.bot.process_commands(message)
            return

        if not message.content or not message.content.strip():
            await self.bot.process_commands(message)
            return

        if self.contains_allowed_word(message.content):
            try:
                emoji = discord.PartialEmoji.from_str(REACTION_EMOJI)
                await message.add_reaction(emoji)
            except discord.Forbidden:
                print("[meow_reaction] Chybi prava na pridavani reakci.")
            except discord.HTTPException as e:
                print(f"[meow_reaction] Discord chyba pri reakci: {e}")
            except Exception as e:
                print(f"[meow_reaction] Neocekavana chyba pri reakci: {e}")

        await self.bot.process_commands(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(MeowReaction(bot))
