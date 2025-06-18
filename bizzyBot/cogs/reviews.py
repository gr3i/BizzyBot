import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import sqlite3
import os
from datetime import datetime

DB_PATH = "db/reviews.db"
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

os.makedirs("db", exist_ok=True)
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS hodnoceni (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    predmet TEXT,
    znamka TEXT,
    recenze TEXT,
    autor_id INTEGER,
    datum TEXT,
    likes INTEGER DEFAULT 0,
    dislikes INTEGER DEFAULT 0
)''')
c.execute('''CREATE TABLE IF NOT EXISTS reakce (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hodnoceni_id INTEGER,
    user_id INTEGER,
    typ TEXT,
    datum TEXT
)''')
conn.commit()

async def predmet_autocomplete(interaction: discord.Interaction, current: str):
    return [app_commands.Choice(name=sub, value=sub) for sub in SUBJECTS if current.lower() in sub.lower()][:25]

async def id_autocomplete(interaction: discord.Interaction, current: str):
    c.execute("SELECT id, predmet FROM hodnoceni WHERE CAST(id AS TEXT) LIKE ? OR predmet LIKE ? LIMIT 25", (f"%{current}%", f"%{current}%"))
    rows = c.fetchall()
    return [app_commands.Choice(name=f"{row[0]} - {row[1]}", value=row[0]) for row in rows]

class ReviewView(View):
    def __init__(self, reviews, user_id, bot):
        super().__init__(timeout=300)
        self.reviews = reviews
        self.index = 0
        self.user_id = user_id
        self.bot = bot

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user_id

    def create_embed(self):
        r = self.reviews[self.index]
        embed = discord.Embed(title=f"{r['predmet']} - hodnocení #{r['id']}", description=r['recenze'])
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
    async def prev(self, interaction, button):
        if self.index > 0:
            self.index -= 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label='➡', style=discord.ButtonStyle.secondary)
    async def next(self, interaction, button):
        if self.index < len(self.reviews) - 1:
            self.index += 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label='👍', style=discord.ButtonStyle.success)
    async def like(self, interaction, button):
        await self.react(interaction, 'like')

    @discord.ui.button(label='👎', style=discord.ButtonStyle.danger)
    async def dislike(self, interaction, button):
        await self.react(interaction, 'dislike')

    async def react(self, interaction, typ):
        r = self.reviews[self.index]
        c.execute("SELECT * FROM reakce WHERE hodnoceni_id = ? AND user_id = ?", (r['id'], interaction.user.id))
        if c.fetchone():
            await interaction.response.send_message("Už jsi reagoval.", ephemeral=True)
            return
        datum = datetime.now().isoformat()
        c.execute("INSERT INTO reakce (hodnoceni_id, user_id, typ, datum) VALUES (?, ?, ?, ?)", (r['id'], interaction.user.id, typ, datum))
        if typ == 'like':
            c.execute("UPDATE hodnoceni SET likes = likes + 1 WHERE id = ?", (r['id'],))
            r['likes'] += 1
        else:
            c.execute("UPDATE hodnoceni SET dislikes = dislikes + 1 WHERE id = ?", (r['id'],))
            r['dislikes'] += 1
        conn.commit()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

class Reviews(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _has_allowed_role(self, interaction: discord.Interaction):
        if any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles):
            return True
        await interaction.response.send_message("Nemáš oprávnění použít tento příkaz.", ephemeral=True)
        return False

    @app_commands.command(name="pridat_hodnoceni", description="Přidej hodnocení předmětu.")
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

        if len(recenze) > MAX_REVIEW_LENGTH:
            await interaction.response.send_message(f"Recenze je příliš dlouhá. Maximálně {MAX_REVIEW_LENGTH} znaků.", ephemeral=True)
            return

        datum = datetime.now().isoformat()
        c.execute("INSERT INTO hodnoceni (predmet, znamka, recenze, autor_id, datum) VALUES (?, ?, ?, ?, ?)",
                  (predmet, znamka.upper(), recenze, interaction.user.id, datum))
        conn.commit()
        await interaction.response.send_message("Hodnocení přidáno.")

    @app_commands.command(name="zobraz_hodnoceni", description="Zobraz hodnocení předmětu.")
    @app_commands.describe(predmet="Název předmětu")
    @app_commands.autocomplete(predmet=predmet_autocomplete)
    async def zobraz_hodnoceni(self, interaction: discord.Interaction, predmet: str):
        if not await self._has_allowed_role(interaction):
            return
        c.execute("SELECT * FROM hodnoceni WHERE predmet = ? ORDER BY datum DESC", (predmet,))
        rows = c.fetchall()
        if not rows:
            await interaction.response.send_message("Žádná hodnocení.", ephemeral=True)
            return
        reviews = [{
            'id': r[0], 'predmet': r[1], 'znamka': r[2], 'recenze': r[3], 'autor_id': r[4], 'datum': r[5], 'likes': r[6], 'dislikes': r[7]
        } for r in rows]
        view = ReviewView(reviews, interaction.user.id, self.bot)
        await interaction.response.send_message(embed=view.create_embed(), view=view)

    @app_commands.command(name="edit_hodnoceni", description="Edituj své hodnocení.")
    @app_commands.describe(id_hodnoceni="ID hodnocení", znamka="Nová známka", recenze="Nová recenze")
    @app_commands.autocomplete(id_hodnoceni=id_autocomplete)
    async def edit_hodnoceni(self, interaction: discord.Interaction, id_hodnoceni: int, znamka: str, recenze: str):
        if not await self._has_allowed_role(interaction):
            return

        if len(recenze) > MAX_REVIEW_LENGTH:
            await interaction.response.send_message(f"Recenze je příliš dlouhá. Maximálně {MAX_REVIEW_LENGTH} znaků.", ephemeral=True)
            return

        c.execute("SELECT autor_id FROM hodnoceni WHERE id = ?", (id_hodnoceni,))
        row = c.fetchone()
        if not row or row[0] != interaction.user.id:
            await interaction.response.send_message("Nemáš oprávnění.", ephemeral=True)
            return
        c.execute("UPDATE hodnoceni SET znamka = ?, recenze = ? WHERE id = ?", (znamka.upper(), recenze, id_hodnoceni))
        conn.commit()
        await interaction.response.send_message("Hodnocení upraveno.")

    @app_commands.command(name="smazat_hodnoceni", description="Smaž hodnocení.")
    @app_commands.describe(id_hodnoceni="ID hodnocení")
    @app_commands.autocomplete(id_hodnoceni=id_autocomplete)
    async def smazat_hodnoceni(self, interaction: discord.Interaction, id_hodnoceni: int):
        if not await self._has_allowed_role(interaction):
            return
        c.execute("SELECT autor_id FROM hodnoceni WHERE id = ?", (id_hodnoceni,))
        row = c.fetchone()
        if not row:
            await interaction.response.send_message("Hodnocení nenalezeno.", ephemeral=True)
            return
        if row[0] != interaction.user.id and not any(r.id in MOD_ROLE_IDS for r in interaction.user.roles) and interaction.user.id not in OWNER_IDS:
            await interaction.response.send_message("Nemáš oprávnění.", ephemeral=True)
            return
        c.execute("DELETE FROM hodnoceni WHERE id = ?", (id_hodnoceni,))
        conn.commit()
        await interaction.response.send_message("Hodnocení smazáno.")

async def setup(bot):
    await bot.add_cog(Reviews(bot))

