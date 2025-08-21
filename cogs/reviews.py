import os
from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import text

from db.session import SessionLocal
from db.models import Review, Reaction

ALLOWED_ROLE_ID = 1358911329737642014
MAX_REVIEW_LENGTH = 3900

# short list for demo; dopln si vlastni
SUBJECTS = ["epP", "mak1P", "manP", "mkP", "ma1P"]

async def predmet_autocomplete(inter: discord.Interaction, current: str):
    return [app_commands.Choice(name=s, value=s) for s in SUBJECTS if current.lower() in s.lower()][:25]

async def id_autocomplete(inter: discord.Interaction, current: str):
    q = f"%{current}%"
    with SessionLocal() as s:
        rows = s.execute(
            text("SELECT id, predmet FROM hodnoceni WHERE CAST(id AS TEXT) LIKE :q OR predmet LIKE :q ORDER BY id DESC LIMIT 25"),
            {"q": q},
        ).all()
    return [app_commands.Choice(name=f"{rid} - {predmet}", value=rid) for rid, predmet in rows]

class Reviews(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _allowed(self, inter: discord.Interaction) -> bool:
        if not isinstance(inter.user, discord.Member):
            await inter.response.send_message("Pouze na serveru.", ephemeral=True)
            return False
        if any(r.id == ALLOWED_ROLE_ID for r in inter.user.roles):
            return True
        await inter.response.send_message("Nemas opravneni.", ephemeral=True)
        return False

    hodnoceni = app_commands.Group(name="hodnoceni", description="Hodnoceni predmetu")

    @hodnoceni.command(name="pridat", description="Pridej hodnoceni predmetu.")
    @app_commands.guild_only()
    @app_commands.autocomplete(predmet=predmet_autocomplete)
    @app_commands.describe(predmet="Nazev predmetu", znamka="A-F", recenze="Text recenze")
    async def pridat(self, inter: discord.Interaction, predmet: str, znamka: str, recenze: str):
        if not await self._allowed(inter):
            return
        if predmet not in SUBJECTS or znamka.upper() not in list("ABCDEF"):
            await inter.response.send_message("Neplatny predmet nebo znamka.", ephemeral=True)
            return
        if len(recenze) > MAX_REVIEW_LENGTH:
            await inter.response.send_message(f"Recenze je prilis dlouha (max {MAX_REVIEW_LENGTH}).", ephemeral=True)
            return
        with SessionLocal() as s:
            s.add(Review(
                predmet=predmet,
                znamka=znamka.upper(),
                recenze=recenze,
                autor_id=inter.user.id,
                datum=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            ))
            s.commit()
        await inter.response.send_message("Hodnoceni pridano.", ephemeral=True)

    @hodnoceni.command(name="zobrazit", description="Zobraz hodnoceni predmetu.")
    @app_commands.guild_only()
    @app_commands.autocomplete(predmet=predmet_autocomplete)
    @app_commands.describe(predmet="Nazev predmetu")
    async def zobrazit(self, inter: discord.Interaction, predmet: str):
        if not await self._allowed(inter):
            return
        with SessionLocal() as s:
            rows = (
                s.query(Review)
                .filter(Review.predmet == predmet)
                .order_by(Review.id.desc())
                .all()
            )
        if not rows:
            await inter.response.send_message("Zadna hodnoceni.", ephemeral=True)
            return
        r = rows[0]
        emb = discord.Embed(title=f"{r.predmet} — #{r.id}", description=r.recenze)
        emb.add_field(name="Znamka", value=r.znamka)
        emb.add_field(name="Likes", value=str(r.likes))
        emb.add_field(name="Dislikes", value=str(r.dislikes))
        await inter.response.send_message(embed=emb, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Reviews(bot))
    gid = int(os.getenv("GUILD_ID", "0"))
    if gid:
        bot.tree.add_command(Reviews.hodnoceni, guild=discord.Object(id=gid))
        print(f"[reviews] group 'hodnoceni' registered for guild {gid}")
    else:
        bot.tree.add_command(Reviews.hodnoceni)
        print("[reviews] group 'hodnoceni' registered (global)")

