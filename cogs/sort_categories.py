# cogs/sort_categories.py
from __future__ import annotations

import asyncio
from typing import Optional, Literal, List

import discord
from discord import app_commands
from discord.ext import commands

# ===== Access settings (copy your values from main or edit) =====
ALLOWED_USER_IDS = {685958402442133515}          # users with access
ALLOWED_ROLE_IDS = {1358898283782602932}         # roles with access
# ================================================================

SLEEP_BETWEEN_EDITS = 0.4  # gentle pace due to rate-limits

def _has_access(member: discord.Member) -> bool:
    if member.id in ALLOWED_USER_IDS:
        return True
    return any(r.id in ALLOWED_ROLE_IDS for r in member.roles)

def _sort_key(ch: discord.abc.GuildChannel):
    # case-insensitive
    return ch.name.casefold()

async def _sort_one_category(cat: discord.CategoryChannel, ascending: bool = True) -> int:
    """Sort channels inside one category (no moving between categories)."""
    channels = list(cat.channels)  # text/voice/stage/forum
    if not channels:
        return 0

    sorted_channels = sorted(channels, key=_sort_key, reverse=not ascending)
    changed = 0
    for pos, ch in enumerate(sorted_channels):
        if ch.position != pos:
            await ch.edit(position=pos, reason="Alphabetical sort (per-category)")
            changed += 1
            await asyncio.sleep(SLEEP_BETWEEN_EDITS)
    return changed

async def _safe_move_and_position(
    ch: discord.abc.GuildChannel,
    target_cat: discord.CategoryChannel,
    pos: int,
    reason: str
) -> bool:
    """Safely move channel to target category (if needed) and set position."""
    try:
        if ch.category_id != target_cat.id:
            await ch.edit(category=target_cat, reason=reason)
            await asyncio.sleep(SLEEP_BETWEEN_EDITS)
        await ch.edit(position=pos, reason=reason)
        await asyncio.sleep(SLEEP_BETWEEN_EDITS)
        return True
    except discord.HTTPException as e:
        print(f"Move/position failed for {ch.name}: {e}")
        return False

async def _global_sort_and_reflow(
    categories: List[discord.CategoryChannel],
    ascending: bool = True,
    soft_max_per_category: Optional[int] = None
) -> tuple[int, int]:
    """
    Take all channels from given categories, sort them and distribute
    to categories in given order. Returns (changes, total).
    """
    all_channels = []
    for cat in categories:
        all_channels.extend(list(cat.channels))

    total = len(all_channels)
    if total == 0:
        return (0, 0)

    all_sorted = sorted(all_channels, key=_sort_key, reverse=not ascending)

    changed = 0
    idx = 0
    for cat in categories:
        pos = 0
        capacity = soft_max_per_category  # None = no limit

        while idx < total:
            if capacity is not None and pos >= capacity:
                break
            ch = all_sorted[idx]
            ok = await _safe_move_and_position(ch, cat, pos, reason="Alphabetical global sort & reflow")
            if ok:
                changed += 1
                pos += 1
                idx += 1
            else:
                # failed move -> try next category
                break

    # remaining (for example because of limits) at least reorder in place
    if idx < total:
        remaining = all_sorted[idx:]
        from collections import defaultdict
        group = defaultdict(list)
        for ch in remaining:
            group[ch.category_id].append(ch)

        for cat_id, chs in group.items():
            cat = next((c for c in categories if c.id == cat_id), None)
            if not cat:
                continue
            current = list(cat.channels)
            rest = [x for x in current if x not in chs]
            final = chs + rest
            for pos, c in enumerate(final):
                if c.position != pos:
                    try:
                        await c.edit(position=pos, reason="Cleanup ordering for leftovers")
                        changed += 1
                        await asyncio.sleep(SLEEP_BETWEEN_EDITS)
                    except discord.HTTPException as e:
                        print(f"Final reorder failed for {c.name}: {e}")

    return (changed, total)

class SortCategories(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Simple access check for slash command
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # guild only + bot must have Manage Channels + allowed users/roles
        if interaction.guild is None:
            await interaction.response.send_message("This command can be used only in a server.", ephemeral=True)
            return False
        me = interaction.guild.me
        if not me or not me.guild_permissions.manage_channels:
            await interaction.response.send_message("I do not have Manage Channels permission.", ephemeral=True)
            return False
        member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.guild.get_member(interaction.user.id)
        if not member or not _has_access(member):
            await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
            return False
        return True

    @app_commands.command(
        name="sort categories",
        description="Sort channels in 1-3 categories (per_category/global, A->Z/Z->A)."
        default_member_permissions=discord.Permissions(manage_channels=True),
        dm_permission=False 
    )
    @app_commands.describe(
        cat1="Category 1 (required)",
        cat2="Category 2 (optional)",
        cat3="Category 3 (optional)",
        mode="Sorting mode: per_category (no moving) or global (redistribute)",
        ascending="True = A->Z, False = Z->A",
        soft_max_per_category="Soft limit of channels per category (global only), empty = no limit"
    )
    # example: /sort-categories cat1:#kategorie1 cat2:#kategorie2 mode:per_category ascending:true

    async def sort_categories(
        self,
        interaction: discord.Interaction,
        cat1: discord.CategoryChannel,
        cat2: Optional[discord.CategoryChannel] = None,
        cat3: Optional[discord.CategoryChannel] = None,
        mode: Literal["per_category", "global"] = "per_category",
        ascending: bool = True,
        soft_max_per_category: Optional[int] = None
    ):
        categories = [c for c in (cat1, cat2, cat3) if c is not None]
        if not categories:
            await interaction.response.send_message("No categories specified.")
            return

        await interaction.response.defer(thinking=True)

        try:
            if mode == "per_category":
                total_changed = 0
                total_channels = 0
                for cat in categories:
                    changed = await _sort_one_category(cat, ascending=ascending)
                    total_changed += changed
                    total_channels += len(cat.channels)
                await interaction.followup.send(
                    f"Done (per_category). Changes: {total_changed}, total channels: {total_channels}.",
                )
            else:
                changed, total = await _global_sort_and_reflow(
                    categories,
                    ascending=ascending,
                    soft_max_per_category=soft_max_per_category
                )
                await interaction.followup.send(
                    f"Done (global). Moves/changes: {changed}/{total}.",
                )
        except Exception as e:
            await interaction.followup.send(f"❌ Error: `{e}`")

async def setup(bot: commands.Bot):
    await bot.add_cog(SortCategories(bot))

