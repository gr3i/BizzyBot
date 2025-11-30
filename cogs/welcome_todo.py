# cogs/welcome_todo.py
import os
from typing import Set, Optional

import discord
from discord import app_commands
from discord.ext import commands

# --------- KONFIG ---------
VUT_ROLE_ID = 1358911329737642014               # ID role VUT
OWNER_IDS: Set[int] = {685958402442133515}      # kdo muze volat /todo_reset
GUILD_ID = int(os.getenv("GUILD_ID", "0"))      # pro per-guild registraci slash prikazu

TODO_LINES = [
    "✅ Nastav si VUT roli podle fakulty (#vut-role).",
    "✅ Pokud jsi z FP, nastav si obor, který studuješ (napiš `/` a vyber `obor`).",
    "✅ Když budeš potřebovat, tak pomocí `/predmet` si můžeš přidat předmět.",
    "✅ Pokud všechno tohle uděláš, dostaneš přístup do nových místností.",
    "✅ Potřebuješ-li podrobnější popis, jak co udělat (#info).",
    "✅ V #bot-spam si vyzkoušej např. příkaz `/room` pro vyhledání místnosti na FP.",
]


class WelcomeTodo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # runtime cache, aby se TODO neposilal vickrat behem jednoho behu bota
        self._sent_users: Set[int] = set()

    # slash: /todo_reset
    # per-guild registrace (rychla) - pokud mam GUILD_ID
    if GUILD_ID:
        @app_commands.command(name="todo_reset", description="Resetuje TODO DM cache (owner only).")
        @app_commands.describe(user="Komu znovu povolit DM; nech prázdné pro reset všech")
        @app_commands.guilds(discord.Object(id=GUILD_ID))
        async def todo_reset(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
            if interaction.user.id not in OWNER_IDS:
                await interaction.response.send_message("Nemáš oprávnění.", ephemeral=True)
                return
            if user:
                self._sent_users.discard(user.id)
                msg = f"Resetnuto pro {user.mention}."
            else:
                self._sent_users.clear()
                msg = "Cache vyprázdněna pro všechny."
            await interaction.response.send_message(msg, ephemeral=True)
    else:
        # fallback: globalni registrace (pomalejsi propagace)
        @app_commands.command(name="todo_reset", description="Resetuje TODO DM cache (owner only).")
        @app_commands.describe(user="Komu znovu povolit DM; nech prázdné pro reset všech")
        async def todo_reset(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
            if interaction.user.id not in OWNER_IDS:
                await interaction.response.send_message("Nemáš oprávnění.", ephemeral=True)
                return
            if user:
                self._sent_users.discard(user.id)
                msg = f"Resetnuto pro {user.mention}."
            else:
                self._sent_users.clear()
                msg = "Cache vyprázdněna pro všechny."
            await interaction.response.send_message(msg, ephemeral=True)

    # kdyz nekdo nove dostane roli VUT, posli TODO do DM
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Spustí se, když se uživateli změní role. Když nově dostane VUT, pošleme TODO do DM."""
        # 1) ignoruj boty
        if after.bot:
            return

        # 2) zjisti, zda pribyla role VUT
        before_roles = {r.id for r in before.roles}
        after_roles = {r.id for r in after.roles}
        just_got_vut = (VUT_ROLE_ID not in before_roles) and (VUT_ROLE_ID in after_roles)
        if not just_got_vut:
            return

        # 3) neposílej vickrat v ramci jednoho behu bota
        if after.id in self._sent_users:
            return
        self._sent_users.add(after.id)

        # 4) posli TODO do DM
        try:
            dm = await after.create_dm()
            embed = discord.Embed(
                title="🎉 Vítej na serveru VUT FP!",
                description=(
                    "Super, ověření proběhlo a máš roli **VUT**.\n"
                    "Tady je rychlý TODO list, ať máš vše po ruce:"
                ),
                color=discord.Color.blurple(),
            )
            embed.add_field(
                name="📝 Co udělat dál",
                value="\n".join(f"- {line}" for line in TODO_LINES),
                inline=False
            )
            embed.set_footer(text="Kdykoliv napiš moderátorům, když si nebudeš vědět rady.")
            await dm.send(embed=embed)
        except discord.Forbidden:
            print(f"[welcome_todo] Nelze poslat DM uživateli {after} (DM uzamčené).")
        except Exception as e:
            print(f"[welcome_todo] Chyba při posílání TODO DM {after}: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeTodo(bot))
    print("[welcome_todo] cog loaded")

