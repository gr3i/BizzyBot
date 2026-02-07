# cogs/welcome_todo.py
import os
from typing import Set, Optional

import discord
from discord import app_commands
from discord.ext import commands

# --------- KONFIG ---------
VUT_ROLE_ID = 1358911329737642014               # ID role VUT
HOST_ROLE_ID = 1358905374500982995
FP_ROLE_ID = 1466036385017233636               # ID role FP
OWNER_IDS: Set[int] = {685958402442133515}      # kdo muze volat /todo_reset
GUILD_ID = int(os.getenv("GUILD_ID", "0"))      # pro per-guild registraci slash prikazu

HOST_TODO_LINES = [
    "✅ V budoucnu, pokud budeš studovat nebo pracovat na VUT, použij `/verify vut`.", 
    "✅ Příkaz použij klidně v místnosti #general. Zprávu uvidíš jen ty...",
    "✅ Dostaneš roli FP/VUT nebo Vyucujici/Zamestnanec",
    "✅ Po ověření získáš přístup do dalších kanálů.",
    "✅ Pokud máš dotaz, napiš do general/offtopic/poradna.",
]


VUT_TODO_LINES = [
    "✅ Pokud máš dotaz, napiš do general/offtopic/poradna.",
    "✅ Do [předmět]-public vidí i vyučující.",
    "✅ Do [předmět]-private pouze studenti, co studují bakaláře nebo magistra.",
    "✅ V #bot-spam si vyzkoušej např. příkaz `/room` pro vyhledání místnosti na FP.",
]

FP_TODO_LINES = [
    "✅ Nastav si obor, který studuješ (napiš `/` a vyber `obor`). "
    "✅ Příkaz použij klidně v místnosti #general. Zprávu uvidíš jen ty...",
    "✅ Pokud tohle uděláš, dostaneš přístup do nových místností.",
    "✅ Do [předmět]-public vidí i vyučující.",
    "✅ Do [předmět]-private pouze studenti, co studují bakaláře nebo magistra.",
    "✅ V #bot-spam si vyzkoušej např. příkaz `/room` pro vyhledání místnosti na FP.",
]


class WelcomeTodo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # runtime cache, aby se TODO neposilal vickrat behem jednoho behu bota
        self._sent_users: Set[str] = set()

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
                self._sent_users.discard(f"{user.id}:vut")
                self._sent_users.discard(f"{user.id}:host")
                self._sent_users.discard(f"{user.id}:fp")
                msg = f"Resetnuto pro {user.mention}."
            else:
                self._sent_users.clear()
                msg = "Cache vyprázdněna pro všechny."
            await interaction.response.send_message(msg, ephemeral=True)

        # kdyz nekdo nove dostane roli VUT, posli TODO do DM
    async def _send_todo_once(self, member: discord.Member, kind: str):
        key = f"{member.id}:{kind}"
        if key in self._sent_users:
            return
        self._sent_users.add(key)

        try:
            dm = await member.create_dm()

            if kind == "vut":
                title = "🎉 Vítej na serveru VUT FP!"
                description = (
                    "Super, ověření proběhlo a máš roli **VUT**.\n"
                    "Tady je rychlý TODO list, ať máš vše po ruce:"
                )
                lines = TODO_LINES

            elif kind == "host":
                title = "🎉 Vítej na serveru VUT FP!"
                description = (
                    "Super, ověření proběhlo a máš roli **Host**.\n"
                    "Tady je rychlý TODO list, ať máš vše po ruce:" 
                )
                lines = HOST_TODO_LINES
            elif kind == "fp":
                title = "🎉 Vítej na serveru VUT FP!"
                description = (
                    "Super, ověření proběhlo a máš roli **FP**.\n"
                    "Tady je rychlý TODO list, ať máš vše po ruce:" 
                )
                lines = FP_TODO_LINES
            else:
                return

            embed = discord.Embed(
                title=title,
                description=description,
                color=discord.Color.blurple(),
            )
            embed.add_field(
                name="📝 Co dál",
                value="\n".join(f"- {l}" for l in lines),
                inline=False
            )
            embed.set_footer(
                text="Kdykoliv napiš moderátorům, když si nebudeš vědět rady."
            )

            await dm.send(embed=embed)

        except discord.Forbidden:
            print(f"[welcome_todo] DM disabled for {member}")
        except Exception as e:
            print(f"[welcome_todo] DM error for {member}: {e}")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # ignoruj boty
        if after.bot:
            return

        before_roles = {r.id for r in before.roles}
        after_roles = {r.id for r in after.roles}

        # VUT role
        if (VUT_ROLE_ID not in before_roles) and (VUT_ROLE_ID in after_roles):
            await self._send_todo_once(after, "vut")

        # HOST role
        if (HOST_ROLE_ID not in before_roles) and (HOST_ROLE_ID in after_roles):
            await self._send_todo_once(after, "host")

        # FP role
        if (FP_ROLE_ID not in before_roles) and (FP_ROLE_ID in after_roles):
            await self._send_todo_once(after, "fp")


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeTodo(bot))
    print("[welcome_todo] cog loaded")

