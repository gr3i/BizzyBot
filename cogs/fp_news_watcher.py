import logging
from datetime import datetime

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

from db.models import FpNewsItem
from db.session import SessionLocal
from services.fp_news import FP_NEWS_URL, NewsItem, parse_news


logger = logging.getLogger(__name__)


TARGET_CHANNEL_ID = 1407312413170335744

CHECK_INTERVAL_HOURS = 1


ALLOWED_ROLE_IDS = [
    1358898283782602932,
    1370841996977246218,
    1370842977479692338,
]

ALLOWED_USER_IDS = [
    685958402442133515,
]


def user_is_allowed(interaction: discord.Interaction) -> bool:
    # konkretni povoleni uzivatele
    if interaction.user.id in ALLOWED_USER_IDS:
        return True

    # povoleni podle role
    member = interaction.user

    if isinstance(member, discord.Member):
        return any(
            role.id in ALLOWED_ROLE_IDS
            for role in member.roles
        )

    return False


class FpNewsWatcher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.check_fp_news.start()


    def cog_unload(self):
        self.check_fp_news.cancel()


    async def _download_news_page(self) -> str:
        timeout = aiohttp.ClientTimeout(total=20)

        headers = {
            "User-Agent": "BizzyBot/1.0 (FP Discord news watcher)",
        }

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers
        ) as session:

            async with session.get(FP_NEWS_URL) as response:
                response.raise_for_status()

                return await response.text()


    async def _send_notification(self, item: FpNewsItem) -> int:
        channel = self.bot.get_channel(TARGET_CHANNEL_ID)

        if channel is None:
            channel = await self.bot.fetch_channel(
                TARGET_CHANNEL_ID
            )

        if not isinstance(channel, discord.abc.Messageable):
            raise RuntimeError(
                f"Kanal {TARGET_CHANNEL_ID} nepodporuje zpravy"
            )

        embed = discord.Embed(
            title="Nova aktualita na webu FP",
            description=f"**{item.title}**",
            color=discord.Color.blue(),
        )

        if item.published_date:
            embed.add_field(
                name="Datum",
                value=item.published_date,
                inline=True,
            )

        embed.add_field(
            name="Odkaz",
            value=f"[Otevrit aktualitu]({item.url})",
            inline=False,
        )

        embed.set_footer(
            text=(
                "Pokud je aktualita relevantni pro server, "
                "muze ji nekdo z modu zpracovat do skolniho infa."
            )
        )

        message = await channel.send(embed=embed)

        return message.id


    async def _process_news(self, items: list[NewsItem]):
        if not items:
            logger.warning(
                "FP watcher nenasel na strance zadne aktuality"
            )

            return

        with SessionLocal() as session:

            # pokud v DB neni nic, jedna se o prvni spusteni
            first_run = (
                session.query(FpNewsItem).count() == 0
            )

            for item in items:

                existing = (
                    session.query(FpNewsItem)
                    .filter(FpNewsItem.url == item.url)
                    .first()
                )

                if existing is None:
                    session.add(
                        FpNewsItem(
                            url=item.url,
                            title=item.title,
                            published_date=item.published_date,

                            # pri prvnim spusteni stare aktuality neposleme
                            notified=first_run,

                            notified_at=(
                                datetime.now()
                                if first_run
                                else None
                            ),
                        )
                    )

                else:
                    # kdyby FP zmenilo nazev nebo datum
                    existing.title = item.title
                    existing.published_date = item.published_date

            session.commit()

            if first_run:
                logger.info(
                    "FP watcher ulozil vychozi stav: %s aktualit",
                    len(items)
                )

                return


        # najdeme nove aktuality, ktere jeste nebyly poslany
        with SessionLocal() as session:

            pending = (
                session.query(FpNewsItem)
                .filter(FpNewsItem.notified.is_(False))
                .order_by(FpNewsItem.id.asc())
                .all()
            )

            for item in pending:

                try:
                    message_id = await self._send_notification(
                        item
                    )

                    item.notified = True
                    item.discord_message_id = str(message_id)
                    item.notified_at = datetime.now()

                    session.commit()

                    logger.info(
                        "FP watcher poslal novou aktualitu: %s",
                        item.title
                    )

                except Exception:
                    session.rollback()

                    logger.exception(
                        "FP watcher nedokazal poslat aktualitu: %s",
                        item.url
                    )


    @tasks.loop(hours=CHECK_INTERVAL_HOURS)
    async def check_fp_news(self):
        try:
            html = await self._download_news_page()

            items = parse_news(html)

            await self._process_news(items)

        except Exception:
            logger.exception(
                "Chyba pri kontrole FP aktualit"
            )


    @check_fp_news.before_loop
    async def before_check_fp_news(self):
        await self.bot.wait_until_ready()


    @app_commands.command(
        name="fpnewscheck",
        description="Zkontroluje aktuality, ktere BizzyBot vidi na webu FP."
    )
    @app_commands.checks.check(user_is_allowed)
    @app_commands.guild_only()
    async def fpnewscheck(
        self,
        interaction: discord.Interaction
    ):
        try:
            html = await self._download_news_page()

            items = parse_news(html)

        except Exception as error:
            await interaction.response.send_message(
                (
                    "FP aktuality se nepodarilo nacist.\n"
                    f"Chyba: `{type(error).__name__}`"
                ),
                ephemeral=True,
            )

            return


        if not items:
            await interaction.response.send_message(
                (
                    "Stranka se nacetla, ale bot na ni "
                    "nenasel zadnou aktualitu."
                ),
                ephemeral=True,
            )

            return


        preview = "\n".join(
            (
                f"• **{item.published_date}** — "
                f"[{item.title}]({item.url})"
            )
            for item in items[:5]
        )


        embed = discord.Embed(
            title="FP News Check",
            description=(
                f"Bot aktualne vidi **{len(items)} aktualit**.\n\n"
                f"{preview}"
            ),
            color=discord.Color.blue(),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )


    @fpnewscheck.error
    async def fpnewscheck_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ):
        if isinstance(error, app_commands.CheckFailure):

            message = "Na tento prikaz nemas opravneni."

            if interaction.response.is_done():
                await interaction.followup.send(
                    message,
                    ephemeral=True,
                )

            else:
                await interaction.response.send_message(
                    message,
                    ephemeral=True,
                )

            return

        logger.exception(
            "Chyba v /fpnewscheck",
            exc_info=error
        )

        if interaction.response.is_done():
            await interaction.followup.send(
                "Pri kontrole aktualit nastala chyba.",
                ephemeral=True,
            )

        else:
            await interaction.response.send_message(
                "Pri kontrole aktualit nastala chyba.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(
        FpNewsWatcher(bot)
    )