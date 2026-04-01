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
   1358887045115941059 
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

    def get_member_role_ids(self, member: discord.abc.User | discord.Member) -> list[int]:
        if not isinstance(member, discord.Member):
            return []
        return [role.id for role in member.roles]

    def get_member_role_names(self, member: discord.abc.User | discord.Member) -> list[str]:
        if not isinstance(member, discord.Member):
            return []
        return [role.name for role in member.roles]

    def has_exempt_role(self, member: discord.abc.User | discord.Member) -> bool:
        if not isinstance(member, discord.Member):
            return False
        return any(role.id in EXEMPT_ROLE_IDS for role in member.roles)

    def contains_allowed_word(self, content: str) -> bool:
        lowered = content.casefold()
        return any(word in lowered for word in ALLOWED_WORDS)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        role_ids = self.get_member_role_ids(message.author)
        role_names = self.get_member_role_names(message.author)

        print("=" * 70)
        print("[meow_guard] nova zprava")
        print(f"[meow_guard] author          = {message.author}")
        print(f"[meow_guard] author_id       = {message.author.id}")
        print(f"[meow_guard] author_bot      = {message.author.bot}")
        print(f"[meow_guard] webhook_id      = {message.webhook_id}")
        print(f"[meow_guard] guild_id        = {message.guild.id if message.guild else None}")
        print(f"[meow_guard] channel_id      = {message.channel.id}")
        print(f"[meow_guard] content         = {message.content!r}")
        print(f"[meow_guard] role_ids        = {role_ids}")
        print(f"[meow_guard] role_names      = {role_names}")
        print(f"[meow_guard] enabled         = {self.is_enabled()}")
        print(f"[meow_guard] target_channel  = {self.is_target_channel(message.channel.id)}")
        print(f"[meow_guard] exempt_user     = {self.is_exempt_user(message.author.id)}")
        print(f"[meow_guard] exempt_role     = {self.has_exempt_role(message.author)}")
        print(f"[meow_guard] contains_word   = {self.contains_allowed_word(message.content or '')}")
        print(f"[meow_guard] exempt_user_ids = {sorted(EXEMPT_USER_IDS)}")
        print(f"[meow_guard] exempt_role_ids = {sorted(EXEMPT_ROLE_IDS)}")

        if self.is_exempt_user(message.author.id):
            print("[meow_guard] action = SKIP (exempt user)")
            await self.bot.process_commands(message)
            return

        if self.has_exempt_role(message.author):
            print("[meow_guard] action = SKIP (exempt role)")
            await self.bot.process_commands(message)
            return

        if message.author.bot:
            print("[meow_guard] action = SKIP (author is bot)")
            await self.bot.process_commands(message)
            return

        if message.webhook_id is not None:
            print("[meow_guard] action = SKIP (webhook)")
            await self.bot.process_commands(message)
            return

        if not self.is_enabled():
            print("[meow_guard] action = SKIP (guard disabled)")
            await self.bot.process_commands(message)
            return

        if not self.is_target_channel(message.channel.id):
            print("[meow_guard] action = SKIP (wrong channel)")
            await self.bot.process_commands(message)
            return

        if not message.content or not message.content.strip():
            print("[meow_guard] action = SKIP (empty content)")
            await self.bot.process_commands(message)
            return

        if self.contains_allowed_word(message.content):
            print("[meow_guard] action = SKIP (contains allowed word)")
            await self.bot.process_commands(message)
            return

        try:
            print("[meow_guard] action = DELETE (missing allowed word)")
            await message.delete()
            print("[meow_guard] delete ok")

            warning = await message.channel.send(
                f"{message.author.mention}, musis do zpravy dopsat `mňau`, `mnau` nebo `meow`."
            )
            print(f"[meow_guard] warning sent, warning_id = {warning.id}")

            await asyncio.sleep(WARNING_DELETE_AFTER)

            try:
                await warning.delete()
                print("[meow_guard] warning deleted")
            except discord.HTTPException as e:
                print(f"[meow_guard] warning delete failed: {e}")

        except discord.Forbidden:
            print("[meow_guard] ERROR: chybi prava na mazani nebo posilani zprav")
        except discord.HTTPException as e:
            print(f"[meow_guard] ERROR: discord chyba: {e}")
        except Exception as e:
            print(f"[meow_guard] ERROR: neocekavana chyba: {e}")

        await self.bot.process_commands(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(MeowGuard(bot))
