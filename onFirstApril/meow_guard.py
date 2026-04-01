import os
import asyncio

import discord
from discord.ext import commands


ALLOWED_WORDS = ("mňau", "mnau", "meow")
TARGET_CHANNEL_IDS = {1358888500845346866, 1358913164493852682}

EXEMPT_USER_IDS = {
    1358884104413904998,
}

EXEMPT_ROLE_IDS = {
    1358887045115941059,
}

WARNING_DELETE_AFTER = 8


class MeowGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def is_enabled(self) -> bool:
        return os.getenv("ENABLE_MEOW_GUARD", "true").lower() == "true"

    def is_target_channel(self, channel_id: int) -> bool:
        return not TARGET_CHANNEL_IDS or channel_id in TARGET_CHANNEL_IDS

    def is_exempt_user(self, user_id: int) -> bool:
        return user_id in EXEMPT_USER_IDS

    def has_exempt_role(self, member: discord.abc.User | discord.Member) -> bool:
        if not isinstance(member, discord.Member):
            return False
        return any(role.id in EXEMPT_ROLE_IDS for role in member.roles)

    def contains_allowed_word(self, content: str) -> bool:
        lowered = content.casefold()
        return any(word in lowered for word in ALLOWED_WORDS)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.is_exempt_user(message.author.id):
            await self.bot.process_commands(message)
            return

        if self.has_exempt_role(message.author):
            await self.bot.process_commands(message)
            return

        if message.author.bot:
            await self.bot.process_commands(message)
            return

        if message.webhook_id is not None:
            await self.bot.process_commands(message)
            return

        if not self.is_enabled():
            await self.bot.process_commands(message)
            return

        if not self.is_target_channel(message.channel.id):
            await self.bot.process_commands(message)
            return

        if not message.content or not message.content.strip():
            await self.bot.process_commands(message)
            return

        if self.contains_allowed_word(message.content):
            await self.bot.process_commands(message)
            return

        try:
            await message.delete()

            warning = await message.channel.send(
                f"{message.author.mention}, musis do zpravy dopsat `mňau`, `mnau` nebo `meow`."
            )

            await asyncio.sleep(WARNING_DELETE_AFTER)

            try:
                await warning.delete()
            except discord.HTTPException:
                pass

        except discord.Forbidden:
            print("[meow_guard] Chybi prava na mazani nebo posilani zprav.", flush=True)
        except discord.HTTPException as e:
            print(f"[meow_guard] Discord chyba: {e}", flush=True)
        except Exception as e:
            print(f"[meow_guard] Neocekavana chyba: {e}", flush=True)

        await self.bot.process_commands(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(MeowGuard(bot))
