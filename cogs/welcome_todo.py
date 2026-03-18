# cogs/welcome_todo.py
import os
from typing import Set, Optional

import discord
from discord import app_commands
from discord.ext import commands

# --------- KONFIG ---------
VUT_ROLE_ID = 1358911329737642014               # ID role VUT
HOST_ROLE_ID = 1358905374500982995              # ID role Host
FP_ROLE_ID = 1466036385017233636                # ID role FP
TEACH_ROLE_ID = 1431724268160549096             # ID role Vyucujici/Zamestnanec
DOKTORAND_ID = 1433984072266285097              # ID role Doktoranda 
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
    "✅ Pokud jsi z FP, ale máš roli VUT, kontaktuj někoho z modů.",
    "✅ Kdyby jsi chtěl*a někoho pozvat, můžeš použít příkaz `/pozvanka`, kde je QR kód.",
]

FP_TODO_LINES = [
    "✅ Nastav si obor, který studuješ (napiš `/` a vyber `obor`). ",
    "✅ Příkaz použij klidně v místnosti #general. Zprávu uvidíš jen ty...",
    "✅ Pokud tohle uděláš, dostaneš přístup do nových místností.",
    "✅ Do [předmět]-public vidí i vyučující.",
    "✅ Do [předmět]-private pouze studenti, co studují bakaláře nebo magistra.",
    "✅ V #bot-spam si vyzkoušej např. příkaz `/room` pro vyhledání místnosti na FP.",
    "✅ Kdyby jsi chtěl*a někoho pozvat, můžeš použít příkaz `/pozvanka`, kde je QR kód.",
]

TEACH_TODO_LINES = [
    "✅ Vaši předmětovou místnost najdete v přehledu kanálů podle názvu předmětu.",
    "✅ Pokud jste poradce nebo máte na VUT jinou roli, napište prosím někomu z Mod týmu – nastavíme Vám odpovídající oprávnění.",
    "✅ Kanál [předmět]-public je společný pro studenty i vyučující.",
    "✅ Kanál [předmět]-private je určen pouze studentům daného bakalářského / magisterského studia.",
    "✅ Zda a jak budete se studenty komunikovat mimo výuku ve svém volném čase, je zcela na Vás.",
    "✅ Discord můžete využít ke sdílení materiálů, diskusi k tématům nebo sběru zpětné vazby.",
    "✅ Byl zde také návrh, že se dá Discord použít k tvorbě studijních materiálů spolu se studenty. Můžete to zkusit!",
    "✅ Server je neoficiální a vzniká komunitně – budeme rádi za podněty ke zlepšení.",
]


class WelcomeTodo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # runtime cache, aby se TODO neposilal vickrat behem jednoho behu bota
        self._sent_users: Set[str] = set()

    # kdyz nekdo nove dostane roli VUT/FP/[Vyucujici/Zamestnanec], posli TODO do DM
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
                lines = VUT_TODO_LINES

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
            elif kind == "teach":
                title = "🎉 Vítejte na serveru VUT FP!"
                description = (
                    "Super, ověření proběhlo a máte roli **Vyucujici/Zamestnanec**.\n"
                    "Tady je rychlý TODO list, ať máte vše po ruce:" 
                )
                lines = TEACH_TODO_LINES
            elif kind == "doktorand":
                title = "🎉 Vítejte na serveru VUT FP!"
                description = (
                    "Super, ověření proběhlo a máte roli **Doktorand**.\n"
                    "Tady je rychlý TODO list, ať máte vše po ruce:" 
                )
                lines = TEACH_TODO_LINES 
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
                text="Nebojte se psát do chatů a reagovat na ostatní. Tenhle server jsme nedělali proto, aby tu byl mrtvý chat, ale aby to byl prostor, co studentům reálně pomůže a zároveň tím nejvíc oceníte práci lidí, co ho tvořili.\n\nKdykoliv napiš moderátorům, když si nebudeš vědět rady."
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

        # TEACH role
        if (TEACH_ROLE_ID not in before_roles) and (TEACH_ROLE_ID in after_roles):
            await self._send_todo_once(after, "teach")

        # Doktorand role 
        if (DOKTORAND_ID not in before_roles) and (DOKTORAND_ID in after_roles):
            await self._send_todo_once(after, "doktorand")


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeTodo(bot))
    print("[welcome_todo] cog loaded")

