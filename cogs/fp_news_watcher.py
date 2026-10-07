import logging
from datetime import datetime

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from sqlalchemy.exc import IntegrityError

from db.models import FpNewsAssignment, FpNewsItem
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


TEST_FP_NEWS = True


def user_is_allowed(interaction: discord.Interaction) -> bool:
    if interaction.user.id in ALLOWED_USER_IDS:
        return True

    member = interaction.user

    if isinstance(member, discord.Member):
        return any(
            role.id in ALLOWED_ROLE_IDS
            for role in member.roles
        )

    return False


def can_finish_assignment(
    interaction: discord.Interaction,
    assignment: FpNewsAssignment,
) -> bool:

    # dokoncit/uvolnit muze ten, kdo prispevek prevzal,
    # nebo uzivatel z ALLOWED_USER_IDS
    return (
        str(interaction.user.id) == assignment.assigned_user_id
        or interaction.user.id in ALLOWED_USER_IDS
    )


class FpNewsActionView(discord.ui.View):
    def __init__(
        self,
        cog: "FpNewsWatcher",
        news_item_id: int,
        status: str = "new",
    ):
        super().__init__(timeout=None)

        self.cog = cog
        self.news_item_id = news_item_id


        if status == "new":

            claim_button = discord.ui.Button(
                label="Prevzit",
                style=discord.ButtonStyle.primary,
                emoji="✋",
                custom_id=f"fp_news:claim:{news_item_id}",
            )

            claim_button.callback = self._claim

            self.add_item(claim_button)


            ignore_button = discord.ui.Button(
                label="Ignorovat",
                style=discord.ButtonStyle.secondary,
                emoji="🗑️",
                custom_id=f"fp_news:ignore:{news_item_id}",
            )

            ignore_button.callback = self._ignore

            self.add_item(ignore_button)


        elif status == "claimed":

            done_button = discord.ui.Button(
                label="Hotovo",
                style=discord.ButtonStyle.success,
                emoji="✅",
                custom_id=f"fp_news:done:{news_item_id}",
            )

            done_button.callback = self._done

            self.add_item(done_button)


            release_button = discord.ui.Button(
                label="Uvolnit",
                style=discord.ButtonStyle.secondary,
                emoji="↩️",
                custom_id=f"fp_news:release:{news_item_id}",
            )

            release_button.callback = self._release

            self.add_item(release_button)


    async def _claim(
        self,
        interaction: discord.Interaction
    ):
        await self.cog.claim_item(
            interaction,
            self.news_item_id
        )


    async def _ignore(
        self,
        interaction: discord.Interaction
    ):
        await self.cog.ignore_item(
            interaction,
            self.news_item_id
        )


    async def _done(
        self,
        interaction: discord.Interaction
    ):
        await self.cog.finish_item(
            interaction,
            self.news_item_id
        )


    async def _release(
        self,
        interaction: discord.Interaction
    ):
        await self.cog.release_item(
            interaction,
            self.news_item_id
        )


class FpNewsWatcher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # po restartu znovu zaregistrujeme tlacitka
        self._register_persistent_views()

        self.check_fp_news.start()


    def cog_unload(self):
        self.check_fp_news.cancel()


    def _register_persistent_views(self):

        with SessionLocal() as session:

            items = (
                session.query(FpNewsItem)
                .filter(
                    FpNewsItem.discord_message_id.isnot(None)
                )
                .all()
            )


            for item in items:

                assignment = (
                    session.query(FpNewsAssignment)
                    .filter(
                        FpNewsAssignment.news_item_id == item.id
                    )
                    .first()
                )


                if assignment is None:
                    status = "new"

                elif assignment.status == "claimed":
                    status = "claimed"

                else:
                    # hotove a ignorovane uz tlacitka nepotrebuji
                    continue


                try:
                    message_id = int(
                        item.discord_message_id
                    )

                except (TypeError, ValueError):
                    continue


                self.bot.add_view(
                    FpNewsActionView(
                        self,
                        item.id,
                        status=status
                    ),
                    message_id=message_id,
                )


    async def _download_news_page(self) -> str:

        timeout = aiohttp.ClientTimeout(
            total=20
        )

        headers = {
            "User-Agent": (
                "BizzyBot/1.0 "
                "(FP Discord news watcher)"
            ),
        }


        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers
        ) as session:

            async with session.get(
                FP_NEWS_URL
            ) as response:

                response.raise_for_status()

                return await response.text()


    def _build_embed(
        self,
        item: FpNewsItem,
        assignment: FpNewsAssignment | None = None,
    ) -> discord.Embed:


        if assignment is None:

            status_text = "🆕 Nezpracovano"

            color = discord.Color.blue()


        elif assignment.status == "claimed":

            status_text = (
                f"🟡 Prevzal "
                f"<@{assignment.assigned_user_id}>"
            )

            color = discord.Color.orange()


        elif assignment.status == "done":

            status_text = (
                f"✅ Zpracoval "
                f"<@{assignment.assigned_user_id}>"
            )

            color = discord.Color.green()


        elif assignment.status == "ignored":

            status_text = (
                f"⚪ Ignoroval "
                f"<@{assignment.assigned_user_id}>"
            )

            color = discord.Color.light_grey()


        else:

            status_text = assignment.status

            color = discord.Color.blue()


        embed = discord.Embed(
            title="Nova aktualita na webu FP",
            description=f"**{item.title}**",
            color=color,
        )


        if item.published_date:

            embed.add_field(
                name="Datum",
                value=item.published_date,
                inline=True,
            )


        embed.add_field(
            name="Stav",
            value=status_text,
            inline=True,
        )


        embed.add_field(
            name="Odkaz",
            value=(
                f"[Otevrit aktualitu]"
                f"({item.url})"
            ),
            inline=False,
        )


        embed.set_footer(
            text=(
                "Pokud je aktualita relevantni pro server, "
                "prevezmi ji a zpracuj do skolniho infa."
            )
        )


        return embed


    async def _send_notification(
        self,
        item: FpNewsItem
    ) -> int:

        channel = self.bot.get_channel(
            TARGET_CHANNEL_ID
        )


        if channel is None:

            channel = await self.bot.fetch_channel(
                TARGET_CHANNEL_ID
            )


        if not isinstance(
            channel,
            discord.abc.Messageable
        ):

            raise RuntimeError(
                f"Kanal {TARGET_CHANNEL_ID} "
                "nepodporuje zpravy"
            )


        embed = self._build_embed(
            item
        )


        view = FpNewsActionView(
            self,
            item.id,
            status="new"
        )


        message = await channel.send(
            embed=embed,
            view=view,
        )


        return message.id


    async def _not_allowed(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.send_message(
            "Na tuto akci nemas opravneni.",
            ephemeral=True,
        )


    async def claim_item(
        self,
        interaction: discord.Interaction,
        news_item_id: int,
    ):

        if not user_is_allowed(interaction):

            await self._not_allowed(
                interaction
            )

            return


        try:

            with SessionLocal() as session:

                item = session.get(
                    FpNewsItem,
                    news_item_id
                )


                if item is None:

                    await interaction.response.send_message(
                        "Tato aktualita uz neni v databazi.",
                        ephemeral=True,
                    )

                    return


                assignment = (
                    session.query(FpNewsAssignment)
                    .filter(
                        FpNewsAssignment.news_item_id
                        == news_item_id
                    )
                    .first()
                )


                if assignment is not None:

                    await interaction.response.send_message(
                        (
                            "Tuto aktualitu uz nekdo prevzal "
                            "nebo uz byla vyrizena."
                        ),
                        ephemeral=True,
                    )

                    return


                assignment = FpNewsAssignment(
                    news_item_id=news_item_id,
                    status="claimed",
                    assigned_user_id=str(
                        interaction.user.id
                    ),
                    claimed_at=datetime.now(),
                )


                session.add(
                    assignment
                )

                session.commit()


                embed = self._build_embed(
                    item,
                    assignment
                )


            await interaction.response.edit_message(
                embed=embed,
                view=FpNewsActionView(
                    self,
                    news_item_id,
                    status="claimed",
                ),
            )


        except IntegrityError:

            await interaction.response.send_message(
                (
                    "Tuto aktualitu mezitim "
                    "prevzal nekdo jiny."
                ),
                ephemeral=True,
            )


    async def ignore_item(
        self,
        interaction: discord.Interaction,
        news_item_id: int,
    ):

        if not user_is_allowed(interaction):

            await self._not_allowed(
                interaction
            )

            return


        try:

            with SessionLocal() as session:

                item = session.get(
                    FpNewsItem,
                    news_item_id
                )


                if item is None:

                    await interaction.response.send_message(
                        "Tato aktualita uz neni v databazi.",
                        ephemeral=True,
                    )

                    return


                assignment = (
                    session.query(FpNewsAssignment)
                    .filter(
                        FpNewsAssignment.news_item_id
                        == news_item_id
                    )
                    .first()
                )


                if assignment is not None:

                    await interaction.response.send_message(
                        (
                            "Tuto aktualitu uz nekdo prevzal "
                            "nebo uz byla vyrizena."
                        ),
                        ephemeral=True,
                    )

                    return


                assignment = FpNewsAssignment(
                    news_item_id=news_item_id,
                    status="ignored",
                    assigned_user_id=str(
                        interaction.user.id
                    ),
                    claimed_at=datetime.now(),
                    finished_at=datetime.now(),
                )


                session.add(
                    assignment
                )

                session.commit()


                embed = self._build_embed(
                    item,
                    assignment
                )


            await interaction.response.edit_message(
                embed=embed,
                view=None,
            )


        except IntegrityError:

            await interaction.response.send_message(
                (
                    "Tuto aktualitu mezitim "
                    "prevzal nekdo jiny."
                ),
                ephemeral=True,
            )


    async def finish_item(
        self,
        interaction: discord.Interaction,
        news_item_id: int,
    ):

        if not user_is_allowed(interaction):

            await self._not_allowed(
                interaction
            )

            return


        with SessionLocal() as session:

            item = session.get(
                FpNewsItem,
                news_item_id
            )


            assignment = (
                session.query(FpNewsAssignment)
                .filter(
                    FpNewsAssignment.news_item_id
                    == news_item_id
                )
                .first()
            )


            if item is None or assignment is None:

                await interaction.response.send_message(
                    (
                        "Tato aktualita nema "
                        "aktivni prirazeni."
                    ),
                    ephemeral=True,
                )

                return


            if assignment.status != "claimed":

                await interaction.response.send_message(
                    "Tato aktualita uz byla vyrizena.",
                    ephemeral=True,
                )

                return


            if not can_finish_assignment(
                interaction,
                assignment
            ):

                await interaction.response.send_message(
                    (
                        "Dokoncit ji muze jen ten, "
                        "kdo ji prevzal, nebo owner."
                    ),
                    ephemeral=True,
                )

                return


            assignment.status = "done"

            assignment.finished_at = datetime.now()

            session.commit()


            embed = self._build_embed(
                item,
                assignment
            )


        await interaction.response.edit_message(
            embed=embed,
            view=None,
        )


    async def release_item(
        self,
        interaction: discord.Interaction,
        news_item_id: int,
    ):

        if not user_is_allowed(interaction):

            await self._not_allowed(
                interaction
            )

            return


        with SessionLocal() as session:

            item = session.get(
                FpNewsItem,
                news_item_id
            )


            assignment = (
                session.query(FpNewsAssignment)
                .filter(
                    FpNewsAssignment.news_item_id
                    == news_item_id
                )
                .first()
            )


            if item is None or assignment is None:

                await interaction.response.send_message(
                    (
                        "Tato aktualita nema "
                        "aktivni prirazeni."
                    ),
                    ephemeral=True,
                )

                return


            if assignment.status != "claimed":

                await interaction.response.send_message(
                    "Tato aktualita uz byla vyrizena.",
                    ephemeral=True,
                )

                return


            if not can_finish_assignment(
                interaction,
                assignment
            ):

                await interaction.response.send_message(
                    (
                        "Uvolnit ji muze jen ten, "
                        "kdo ji prevzal, nebo owner."
                    ),
                    ephemeral=True,
                )

                return


            session.delete(
                assignment
            )

            session.commit()


            embed = self._build_embed(
                item
            )


        await interaction.response.edit_message(
            embed=embed,
            view=FpNewsActionView(
                self,
                news_item_id,
                status="new",
            ),
        )


    async def _process_news(
        self,
        items: list[NewsItem]
    ):

        if not items:

            logger.warning(
                (
                    "FP watcher nenasel na strance "
                    "zadne aktuality"
                )
            )

            return


        with SessionLocal() as session:

            first_run = (
                session.query(FpNewsItem).count() == 0
            )


            for item in items:

                existing = (
                    session.query(FpNewsItem)
                    .filter(
                        FpNewsItem.url == item.url
                    )
                    .first()
                )


                if existing is None:

                    session.add(
                        FpNewsItem(
                            url=item.url,
                            title=item.title,
                            published_date=item.published_date,
                            notified=first_run,
                            notified_at=(
                                datetime.now()
                                if first_run
                                else None
                            ),
                        )
                    )


                else:

                    existing.title = item.title

                    existing.published_date = (
                        item.published_date
                    )


            session.commit()


            if first_run:

                logger.info(
                    (
                        "FP watcher ulozil vychozi stav: "
                        "%s aktualit"
                    ),
                    len(items)
                )

                return


        with SessionLocal() as session:

            pending = (
                session.query(FpNewsItem)
                .filter(
                    FpNewsItem.notified.is_(False)
                )
                .order_by(
                    FpNewsItem.id.asc()
                )
                .all()
            )


            for item in pending:

                try:

                    message_id = (
                        await self._send_notification(
                            item
                        )
                    )


                    item.notified = True

                    item.discord_message_id = str(
                        message_id
                    )

                    item.notified_at = datetime.now()


                    session.commit()


                    logger.info(
                        (
                            "FP watcher poslal novou "
                            "aktualitu: %s"
                        ),
                        item.title
                    )


                except Exception:

                    session.rollback()


                    logger.exception(
                        (
                            "FP watcher nedokazal poslat "
                            "aktualitu: %s"
                        ),
                        item.url
                    )


    @tasks.loop(
        hours=CHECK_INTERVAL_HOURS
    )
    async def check_fp_news(self):

        try:

            html = await self._download_news_page()

            items = parse_news(
                html
            )


            if TEST_FP_NEWS:

                items.append(
                    NewsItem(
                        title=(
                            "TEST - BizzyBot FP watcher"
                        ),
                        published_date="7. 10. 2026",
                        url=(
                            "https://www.fp.vut.cz/"
                            "cs/o-fakulte/aktuality"
                            "?bizzybot-test=2"
                        ),
                    )
                )


            await self._process_news(
                items
            )


        except Exception:

            logger.exception(
                "Chyba pri kontrole FP aktualit"
            )


    @check_fp_news.before_loop
    async def before_check_fp_news(self):

        await self.bot.wait_until_ready()


    @app_commands.command(
        name="fpnewscheck",
        description=(
            "Zkontroluje aktuality, ktere "
            "BizzyBot vidi na webu FP."
        )
    )
    @app_commands.checks.check(
        user_is_allowed
    )
    @app_commands.guild_only()
    async def fpnewscheck(
        self,
        interaction: discord.Interaction
    ):

        try:

            html = await self._download_news_page()

            items = parse_news(
                html
            )


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
                f"Bot aktualne vidi "
                f"**{len(items)} aktualit**.\n\n"
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

        if isinstance(
            error,
            app_commands.CheckFailure
        ):

            message = (
                "Na tento prikaz nemas opravneni."
            )


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
                (
                    "Pri kontrole aktualit "
                    "nastala chyba."
                ),
                ephemeral=True,
            )


        else:

            await interaction.response.send_message(
                (
                    "Pri kontrole aktualit "
                    "nastala chyba."
                ),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):

    await bot.add_cog(
        FpNewsWatcher(bot)
    )