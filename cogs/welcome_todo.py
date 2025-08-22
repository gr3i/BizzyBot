# cogs/welcome_todo.py
import asyncio
from typing import Set

import discord
from discord.ext import commands

# ID role VUT – použij ten, který už máš v projektu
VUT_ROLE_ID = 1358915656782844094  # pokud bys měl jiný, přepiš

# Jednoduchý seznam úkolů – můžeš libovolně upravit text
TODO_LINES = [
    "✅ Přečti si pravidla serveru (#pravidla).",
    "✅ Nastav si předměty pomocí /predmet pridat.",
    "✅ Zkontroluj si oznámení a důležité kanály (#oznameni).",
    "✅ Přidej si fakultu/ročník, pokud je potřeba (#role).",
    "✅ Když něco nejde, napiš do #podpora nebo @moderátorům.",
]

class WelcomeTodo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # V jednoduché verzi si držíme runtime cache, ať uživatele nespamujeme,
        # když by mu někdo roli odebral a znovu přidal během jedné session.
        self._sent_users: Set[int] = set()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Spustí se, když se uživateli změní role. Když nově dostane VUT, pošleme TODO do DM."""
        # 1) ignoruj boty
        if after.bot:
            return

        # 2) zjisti, zda přibyla role VUT
        before_roles = {r.id for r in before.roles}
        after_roles = {r.id for r in after.roles}
        just_got_vut = (VUT_ROLE_ID not in before_roles) and (VUT_ROLE_ID in after_roles)
        if not just_got_vut:
            return

        # 3) ať neposíláme víckrát v rámci jednoho běhu bota
        if after.id in self._sent_users:
            return
        self._sent_users.add(after.id)

        # 4) pošli TODO do DM
        try:
            dm = await after.create_dm()
            # hezký embed
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
            # Uživatel má zamčené DMs – zkusíme mu po chvilce napsat do kanálu (pokud chceš),
            # ale nejjednodušší je to jen zalogovat.
            print(f"[welcome_todo] Nelze poslat DM uživateli {after} (DM uzamčené).")
        except Exception as e:
            print(f"[welcome_todo] Chyba při posílání TODO DM {after}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeTodo(bot))

