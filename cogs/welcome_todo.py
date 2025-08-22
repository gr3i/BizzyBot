# cogs/welcome_todo.py
import asyncio
from typing import Set

import discord
from discord.ext import commands

# ID role VUT
VUT_ROLE_ID = 1358915656782844094


TODO_LINES = [
    "✅ Nastav si VUT roli podle fakulty (#vut-role).",
    "✅ Pokud jsi z FP, nastav si obor, který studuješ. (napiš `/` a vyber `obor`)",
    "✅ Když budeš potřebovat, tak pomocí `/predmet` si můžeš přidat předmět",
    "✅ Pokud všechno tohle uděláš, dostaneš přístup do nových místností.",
    "✅ Když něco nejde, napiš do #general nebo @moderátorům.",
]

class WelcomeTodo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # v jednoduche verzi si drzim runtime cache, at uzivatele nespamujeme,
        # kdyz by mu nekdo roli odebral a znovu pridal behem jedne session.
        self._sent_users: Set[int] = set()

    @app_commands.command(name="todo_reset", description="Resetuje TODO DM cache (owner only).")
    @app_commands.describe(user="Komu znovu povolit DM; nech prázdné pro reset všech")
    async def todo_reset(self, interaction: discord.Interaction, user: discord.User | None = None):
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

        # at neposilame vickrat v ramci jednoho behu bota
        if after.id in self._sent_users:
            return
        self._sent_users.add(after.id)

        # posli TODO do DM
        try:
            dm = await after.create_dm()
            # embed
            embed = discord.Embed(
                title="🎉 Vítej na serveru VUT!",
                description="Super, ověření proběhlo a máš roli **VUT**.\n"
                            "Tady je rychlý TODO list, ať máš vše po ruce:",
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

