# cogs/reviews.py  – ORM (SQLAlchemy) verze pro app.db

import os
from datetime import datetime
from typing import List

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View
import sqlalchemy as sa 

# ORM importy
from db.session import SessionLocal
from db.models import Review, Reaction

# konfigurace
MOD_ROLE_IDS = [1358898283782602932]
OWNER_IDS = [685958402442133515]
ALLOWED_ROLE_ID = 1358911329737642014

MAX_REVIEW_LENGTH = 3900

SUBJECTS = [
    "epP",
    "mak1P",
    "manP",
    "mkP",
    "ma1P",
    "HA1PZ",
    "HA2PZ",
    "pzmP",
    "pmzP",
    "pmrzP",
    "KeseP",
    "IG",
    "KinfP",
    "ma2P",
    "mik1P",
    "uceP",
    "HA2PL",
    "HA3PL",
    "pmlP",
    "pmrlP",
    "fpP",
    "ftP",
    "KjpP",
    "KrnP",
    "statP",
    "KikP",
    "kvmP",
    "AOP1",
    "KdetP",
    "VYF001",
    "VYI001",
    "KmmP",
    "VYN001",
    "VYS001",
    "KdasP",
    "fapP",
    "marP",
    "KobP",
    "pojP",
    "emP",
    "pprP",
    "zdP",
    "AOP2",
    "msmP",
    "KepP",
    "VYF002",
    "VYN002",
    "VYS002",
    "oprP",
    "KopxzP",
    "KosP",
    "prP",
    "KpdsP",
    "KdmP",
    "smarP",
    "KimP",
    "KrlrP",
    "VYF003",
    "VYI003",
    "VYN003",
    "VYS003",
    "bpsP",
    "KdsP",
    "Kme1P",
    "KopxlP",
    "BBIDE",
    "BECOE",
    "BMAE",
    "BMEE",
    "BMARE",
    "BMATE",
    "BDMSE",
    "BFMSE",
    "BLENE",
    "BPENE",
    "BBCDE",
    "BATE",
    "BEPR1E",
    "BMRE",
    "BPMAE",
    "BAASE",
    "BCCSME",
    "BEPR2E",
    "BHRME",
    "BSMAE",
    "BEPR3E",
    "BFT1E",
    "BISSCE",
    "BTSPE",
    "BBDAE",
    "BEPR4E",
    "BFT2E",
    "DFM",
    "MA1_M",
    "IUS",
    "ZE",
    "OA1Z",
    "OA2Z",
    "APV",
    "bdmP",
    "MA2_M",
    "NUM",
    "PLAB",
    "VT",
    "OA2L",
    "OA3",
    "DMSM",
    "EC",
    "EPO",
    "RD",
    "STA1",
    "DIT",
    "PPP",
    "BuceP",
    "IZP",
    "MRMU",
    "PRA",
    "RPICT",
    "STA2",
    "UPS",
    "ZFI",
    "ISJ",
    "ITW",
    "IZG",
    "DS_2",
    "MICT",
    "PIS",
    "PPR1",
    "PDS",
    "APSP",
    "rkP",
    "ITU",
    "DIS",
    "PRIS",
    "PPR2",
    "PICT",
    "infP",
    "BbpP",
    "kitP",
    "BelmP",
    "BmsP",
    "BopvP",
    "Bp1P",
    "BpmP",
    "ssrP",
    "rrpnP",
    "BomvP",
    "Bp2P",
    "BrprP",
    "BevpP",
    "BstP",
    "BbezP",
    "BlogaP",
    "BoppP",
    "BpisP",
    "BpdsP",
    "BsvP",
    "BdisP",
    "BmzP",
    "Bp3P",
    "BrkvP",
    "BtrtP",
    "PVA3",
    "PVA4",
    "PVB1",
    "PVB2",
    "PVB5",
    "PVB6",
    "UzpP",
    "UvfP",
    "UvpP",
    "UfuP",
    "UopP",
    "UzfoP",
    "UfudP",
    "UmpaP",
    "Uopx1P",
    "UzpoP",
    "UdphP",
    "UnuP",
    "Uopx2P",
    "UpdsP",
    "UupcP",
    "UvhoP",
    "UispP",
    "UdsP",
    "UmzpP",
    "UudpP",
    "UfifP",
    "PVB3",
    "PVB4",
]

VALID_GRADES = ["A", "B", "C", "D", "E", "F"]

# pomocne funkce pro autocomplete

async def predmet_autocomplete(inter: discord.Interaction, current: str):
    items = [s for s in SUBJECTS if current.lower() in s.lower()]
    return [app_commands.Choice(name=s, value=s) for s in items[:25]]

async def id_autocomplete(inter: discord.Interaction, current: str):
    q = f"%{current}%"

    filters = [Review.predmet.ilike(q)]
    if current.strip().isdigit():
        filters.append(Review.id == int(current))

    with SessionLocal() as s:
        rows = (
            s.query(Review.id, Review.predmet)
            .filter(sa.or_(*filters))
            .order_by(Review.id.desc())
            .limit(25)
            .all()
        )

    return [app_commands.Choice(name=f"{rid} - {predmet}", value=rid) for rid, predmet in rows]


# view s tlacitky

class ReviewView(View):
    def __init__(self, reviews: list[dict], user_id: int, bot: commands.Bot):
        super().__init__(timeout=300)
        self.reviews = reviews
        self.index = 0
        self.user_id = user_id
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    def create_embed(self) -> discord.Embed:
        r = self.reviews[self.index]
        embed = discord.Embed(
            title=f"{r['predmet']} - hodnocení #{r['id']}",
            description=r['recenze'],
        )
        embed.add_field(name="Známka", value=r['znamka'])
        embed.add_field(name="Likes", value=str(r['likes']))
        embed.add_field(name="Dislikes", value=str(r['dislikes']))
        author = self.bot.get_user(r['autor_id'])
        if author:
            embed.set_footer(text=f"{author.display_name} | {r['datum']}", icon_url=author.display_avatar.url)
        else:
            embed.set_footer(text=f"ID: {r['autor_id']} | {r['datum']}")
        return embed

    @discord.ui.button(label='⬅', style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label='➡', style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if self.index < len(self.reviews) - 1:
            self.index += 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label='👍', style=discord.ButtonStyle.success)
    async def like(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self._react(interaction, 'like')

    @discord.ui.button(label='👎', style=discord.ButtonStyle.danger)
    async def dislike(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self._react(interaction, 'dislike')

    async def _react(self, interaction: discord.Interaction, typ: str):
        r = self.reviews[self.index]
        with SessionLocal() as s:
            # uz reagoval?
            exists = (
                s.query(Reaction.id)
                .filter(Reaction.hodnoceni_id == r['id'], Reaction.user_id == interaction.user.id)
                .first()
            )
            if exists:
                await interaction.response.send_message("Už jsi reagoval.", ephemeral=True)
                return

            # ulozit reakci
            s.add(Reaction(
                hodnoceni_id=r['id'],
                user_id=interaction.user.id,
                typ=typ,
                datum=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            ))

            # aktualizovat pocitadla
            rev = s.query(Review).get(r['id'])
            if rev:
                if typ == 'like':
                    rev.likes += 1
                    r['likes'] += 1
                else:
                    rev.dislikes += 1
                    r['dislikes'] += 1
            s.commit()

        await interaction.response.edit_message(embed=self.create_embed(), view=self)


class Reviews(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _has_allowed_role(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Tento příkaz lze použít jen na serveru.", ephemeral=True)
            return False
        if any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles):
            return True
        await interaction.response.send_message("Nemáš oprávnění použít tento příkaz.", ephemeral=True)
        return False

    hodnoceni = app_commands.Group(
        name="hodnoceni",
        description="Hodnocení předmětů"
    )

    @hodnoceni.command(name="pridat", description="Přidej hodnocení předmětu.")
    @app_commands.guild_only()
    @app_commands.describe(predmet="Název předmětu", znamka="Známka A-F", recenze="Text recenze")
    @app_commands.autocomplete(predmet=predmet_autocomplete)
    async def pridat_hodnoceni(self, interaction: discord.Interaction, predmet: str, znamka: str, recenze: str):
        if not await self._has_allowed_role(interaction):
            return

        if predmet not in SUBJECTS or znamka.upper() not in VALID_GRADES:
            await interaction.response.send_message("Neplatný předmět nebo známka.", ephemeral=True)
            return

        if len(recenze) > MAX_REVIEW_LENGTH:
            await interaction.response.send_message(f"Recenze je příliš dlouhá. Maximálně {MAX_REVIEW_LENGTH} znaků.", ephemeral=True)
            return

        with SessionLocal() as s:
            r = Review(
                predmet=predmet,
                znamka=znamka.upper(),
                recenze=recenze,
                autor_id=interaction.user.id,
                datum=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            )
            s.add(r)
            s.commit()

        await interaction.response.send_message("Hodnocení přidáno.")

    @hodnoceni.command(name="zobrazit", description="Zobraz hodnocení předmětu.")
    @app_commands.guild_only()
    @app_commands.describe(predmet="Název předmětu")
    @app_commands.autocomplete(predmet=predmet_autocomplete)
    async def zobraz_hodnoceni(self, interaction: discord.Interaction, predmet: str):
        if not await self._has_allowed_role(interaction):
            return

        with SessionLocal() as s:
            rows: List[Review] = (
                s.query(Review)
                .filter(Review.predmet == predmet)
                .order_by(Review.id.desc())
                .all()
            )

        if not rows:
            await interaction.response.send_message("Žádná hodnocení.", ephemeral=True)
            return

        reviews = [{
            'id': r.id,
            'predmet': r.predmet,
            'znamka': r.znamka,
            'recenze': r.recenze,
            'autor_id': r.autor_id,
            'datum': r.datum or "",
            'likes': r.likes,
            'dislikes': r.dislikes,
        } for r in rows]

        view = ReviewView(reviews, interaction.user.id, self.bot)
        await interaction.response.send_message(embed=view.create_embed(), view=view)

    @hodnoceni.command(name="upravit", description="Edituj své hodnocení.")
    @app_commands.guild_only()
    @app_commands.describe(id_hodnoceni="ID hodnocení", znamka="Nová známka", recenze="Nová recenze")
    @app_commands.autocomplete(id_hodnoceni=id_autocomplete)
    async def edit_hodnoceni(self, interaction: discord.Interaction, id_hodnoceni: int, znamka: str, recenze: str):
        if not await self._has_allowed_role(interaction):
            return

        if znamka.upper() not in VALID_GRADES:
            await interaction.response.send_message("Neplatná známka (A–F).", ephemeral=True)
            return

        if len(recenze) > MAX_REVIEW_LENGTH:
            await interaction.response.send_message(f"Recenze je příliš dlouhá. Maximálně {MAX_REVIEW_LENGTH} znaků.", ephemeral=True)
            return

        with SessionLocal() as s:
            r = s.query(Review).get(id_hodnoceni)
            if not r or r.autor_id != interaction.user.id:
                await interaction.response.send_message("Nemáš oprávnění.", ephemeral=True)
                return

            r.znamka = znamka.upper()
            r.recenze = recenze
            s.commit()

        await interaction.response.send_message("Hodnocení upraveno.")

    @hodnoceni.command(name="smazat", description="Smaž hodnocení.")
    @app_commands.guild_only()
    @app_commands.describe(id_hodnoceni="ID hodnocení")
    @app_commands.autocomplete(id_hodnoceni=id_autocomplete)
    async def smazat_hodnoceni(self, interaction: discord.Interaction, id_hodnoceni: int):
        if not await self._has_allowed_role(interaction):
            return

        with SessionLocal() as s:
            r = s.query(Review).get(id_hodnoceni)
            if not r:
                await interaction.response.send_message("Hodnocení nenalezeno.", ephemeral=True)
                return

            is_mod = any(role.id in MOD_ROLE_IDS for role in interaction.user.roles)
            is_owner = interaction.user.id in OWNER_IDS
            if r.autor_id != interaction.user.id and not is_mod and not is_owner:
                await interaction.response.send_message("Nemáš oprávnění.", ephemeral=True)
                return

            # smazat navazane reakce
            s.query(Reaction).filter(Reaction.hodnoceni_id == id_hodnoceni).delete(synchronize_session=False)
            s.delete(r)
            s.commit()

        await interaction.response.send_message("Hodnocení smazáno.")


# registrace slash groupy do konkretni guildy (okamzite viditelne)
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

async def setup(bot: commands.Bot):
    cog = Reviews(bot)
    await bot.add_cog(cog)

    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.add_command(Reviews.hodnoceni, guild=guild)
        print(f"[reviews] group 'hodnoceni' registered for guild {GUILD_ID}")
    else:
        bot.tree.add_command(Reviews.hodnoceni)
        print("[reviews] group 'hodnoceni' registered (global)")

