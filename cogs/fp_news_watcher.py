import logging
from collections import Counter
from datetime import datetime, timedelta

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from sqlalchemy.exc import IntegrityError

from db.models import (
    FpNewsAssignment,
    FpNewsItem,
    FpNewsReminder,
    FpWatcherState,
)

from db.session import SessionLocal
from services.fp_news import FP_NEWS_URL, NewsItem, parse_news

from services.fp_events import (
    FP_EVENTS_URL,
    CalendarEvent,
    parse_events,
)


logger = logging.getLogger(__name__)


TARGET_CHANNEL_ID = 1407312413170335744

CHECK_INTERVAL_HOURS = 1
REMINDER_AFTER_HOURS = 0 #24
REMINDER_CHECK_INTERVAL_HOURS = 1
# TEST - automaticke uvolneni po 1 minute
AUTO_RELEASE_AFTER = timedelta(minutes=1)

# PRODUKCE:
# AUTO_RELEASE_AFTER = timedelta(hours=48)

AUTO_RELEASE_CHECK_INTERVAL_HOURS = 1


ALLOWED_ROLE_IDS = [
    1358898283782602932,
    1370841996977246218,
    1370842977479692338,
]

ALLOWED_USER_IDS = [
    685958402442133515,
]


TEST_FP_NEWS = True 
TEST_FP_EVENTS = True 


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

def format_assignment_age(claimed_at: datetime) -> str:
    delta = datetime.now() - claimed_at

    total_minutes = int(
        delta.total_seconds() // 60
    )

    days = total_minutes // 1440
    hours = (total_minutes % 1440) // 60
    minutes = total_minutes % 60

    if days > 0:
        return f"{days} d {hours} h"

    if hours > 0:
        return f"{hours} h {minutes} min"

    return f"{minutes} min"

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
        self.check_fp_news_reminders.start()
        self.check_fp_news_auto_release.start()


    def cog_unload(self):
        self.check_fp_news.cancel()
        self.check_fp_news_reminders.cancel()
        self.check_fp_news_auto_release.cancel()


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


    async def _download_page(
        self,
        url: str
    ) -> str:

        timeout = aiohttp.ClientTimeout(
            total=20
        )

        headers = {
            "User-Agent": (
                "BizzyBot/1.0 "
                "(FP Discord watcher)"
            ),
        }


        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers
        ) as session:

            async with session.get(
                url
            ) as response:

                response.raise_for_status()

                return await response.text()


    async def _download_news_page(
        self
    ) -> str:

        return await self._download_page(
            FP_NEWS_URL
        )


    async def _download_events_page(
        self
    ) -> str:

        return await self._download_page(
            FP_EVENTS_URL
        )


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

        is_event = item.title.startswith(
            "📅 AKCE:"
        )


        if is_event:

            display_title = (
                item.title
                .removeprefix("📅 AKCE:")
                .strip()
            )

            embed_title = (
                "Nova akce v kalendari FP"
            )

            link_text = (
                "Otevrit akci"
            )

            footer_text = (
                "Pokud je akce relevantni pro server, "
                "prevezmi ji a zpracuj do skolniho infa."
            )


        else:

            display_title = item.title

            embed_title = (
                "Nova aktualita na webu FP"
            )

            link_text = (
                "Otevrit aktualitu"
            )

            footer_text = (
                "Pokud je aktualita relevantni pro server, "
                "prevezmi ji a zpracuj do skolniho infa."
            )


        embed = discord.Embed(
            title=embed_title,
            description=f"**{display_title}**",
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
                f"[{link_text}]"
                f"({item.url})"
            ),
            inline=False,
        )


        embed.set_footer(
            text=footer_text
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

            # u hotove aktuality si nechame ID cloveka,
            # ktery ji skutecne dokoncil
            assignment.assigned_user_id = str(
                interaction.user.id
            )

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

            reminder = (
                session.query(FpNewsReminder)
                .filter(
                    FpNewsReminder.assignment_id
                    == assignment.id
                )
                .first()
            )

            if reminder is not None:
                session.delete(
                    reminder
                )

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
        items: list[NewsItem],
        source: str = "news",
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

            state = session.get(
                FpWatcherState,
                source
            )


            if state is None:

                # aktuality uz historicky v DB mame,
                # tak je znovu nebaselineujeme
                if (
                    source == "news"
                    and session.query(
                        FpNewsItem
                    ).count() > 0
                ):

                    first_run = False

                else:

                    first_run = True


                session.add(
                    FpWatcherState(
                        source=source
                    )
                )


            else:

                first_run = False


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
                        "FP watcher ulozil vychozi stav "
                        "pro %s: %s polozek"
                    ),
                    source,
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

    #@tasks.loop(
    #    hours=REMINDER_CHECK_INTERVAL_HOURS
    #)

    @tasks.loop(seconds=30)
    async def check_fp_news_reminders(self):

        try:

            threshold = datetime.now() - timedelta(
                hours=REMINDER_AFTER_HOURS
            )

            with SessionLocal() as session:

                assignments = (
                    session.query(FpNewsAssignment)
                    .filter(
                        FpNewsAssignment.status == "claimed",
                        FpNewsAssignment.claimed_at <= threshold,
                    )
                    .all()
                )

                pending_reminders = []

                for assignment in assignments:

                    reminder = (
                        session.query(FpNewsReminder)
                        .filter(
                            FpNewsReminder.assignment_id
                            == assignment.id
                        )
                        .first()
                    )

                    if reminder is not None:
                        continue

                    item = session.get(
                        FpNewsItem,
                        assignment.news_item_id
                    )

                    if item is None:
                        continue

                    pending_reminders.append(
                        {
                            "assignment_id": assignment.id,
                            "user_id": assignment.assigned_user_id,
                            "title": item.title,
                            "message_id": item.discord_message_id,
                        }
                    )


            if not pending_reminders:
                return


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


            for reminder_data in pending_reminders:

                # pred odeslanim jeste jednou overime,
                # ze je aktualita porad prevzata
                with SessionLocal() as session:

                    assignment = session.get(
                        FpNewsAssignment,
                        reminder_data["assignment_id"]
                    )

                    if (
                        assignment is None
                        or assignment.status != "claimed"
                    ):
                        continue


                    existing_reminder = (
                        session.query(FpNewsReminder)
                        .filter(
                            FpNewsReminder.assignment_id
                            == assignment.id
                        )
                        .first()
                    )

                    if existing_reminder is not None:
                        continue


                original_message = ""

                guild = getattr(
                    channel,
                    "guild",
                    None
                )

                if (
                    guild is not None
                    and reminder_data["message_id"]
                ):

                    jump_url = (
                        f"https://discord.com/channels/"
                        f"{guild.id}/"
                        f"{TARGET_CHANNEL_ID}/"
                        f"{reminder_data['message_id']}"
                    )

                    original_message = (
                        f"\n[Přejít na původní upozornění]"
                        f"({jump_url})"
                    )


                embed = discord.Embed(
                    title="FP aktualita stale ceka na zpracovani",
                    description=(
                        f"**{reminder_data['title']}**\n\n"
                        f"Tato aktualita je prevzata uz "
                        f"vice nez {REMINDER_AFTER_HOURS} hodin."
                        f"{original_message}"
                    ),
                    color=discord.Color.orange(),
                )


                await channel.send(
                    content=(
                        f"<@{reminder_data['user_id']}> "
                        "pripominka k prevzate FP aktualite:"
                    ),
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions(
                        users=True,
                        roles=False,
                        everyone=False,
                    ),
                )


                # ulozime az po uspesnem odeslani
                with SessionLocal() as session:

                    assignment = session.get(
                        FpNewsAssignment,
                        reminder_data["assignment_id"]
                    )

                    if (
                        assignment is None
                        or assignment.status != "claimed"
                    ):
                        continue


                    existing_reminder = (
                        session.query(FpNewsReminder)
                        .filter(
                            FpNewsReminder.assignment_id
                            == assignment.id
                        )
                        .first()
                    )

                    if existing_reminder is None:

                        session.add(
                            FpNewsReminder(
                                assignment_id=assignment.id
                            )
                        )

                        session.commit()


        except Exception:

            logger.exception(
                "Chyba pri kontrole FP reminderu"
            )

    @tasks.loop(seconds=30)
    async def check_fp_news_auto_release(self):

        try:

            threshold = datetime.now() - AUTO_RELEASE_AFTER


            with SessionLocal() as session:

                assignments = (
                    session.query(FpNewsAssignment)
                    .filter(
                        FpNewsAssignment.status == "claimed",
                        FpNewsAssignment.claimed_at <= threshold,
                    )
                    .all()
                )


                assignment_ids = [
                    assignment.id
                    for assignment in assignments
                ]


            if not assignment_ids:
                return


            channel = self.bot.get_channel(
                TARGET_CHANNEL_ID
            )


            if channel is None:

                channel = await self.bot.fetch_channel(
                    TARGET_CHANNEL_ID
                )


            if not isinstance(
                channel,
                (discord.TextChannel, discord.Thread)
            ):

                raise RuntimeError(
                    f"Kanal {TARGET_CHANNEL_ID} "
                    "nepodporuje nacitani zprav"
                )


            for assignment_id in assignment_ids:

                with SessionLocal() as session:

                    assignment = session.get(
                        FpNewsAssignment,
                        assignment_id
                    )


                    # mezitim mohl nekdo dat Hotovo nebo Uvolnit
                    if (
                        assignment is None
                        or assignment.status != "claimed"
                        or assignment.claimed_at > threshold
                    ):
                        continue


                    item = session.get(
                        FpNewsItem,
                        assignment.news_item_id
                    )


                    if item is None:
                        continue


                    news_item_id = item.id

                    old_user_id = (
                        assignment.assigned_user_id
                    )

                    message_id = (
                        item.discord_message_id
                    )


                    # embed uz vratime do puvodniho stavu
                    embed = self._build_embed(
                        item
                    )


                    # reminder uz pro stare prevzeti nepotrebujeme
                    reminder = (
                        session.query(FpNewsReminder)
                        .filter(
                            FpNewsReminder.assignment_id
                            == assignment.id
                        )
                        .first()
                    )


                    if reminder is not None:

                        session.delete(
                            reminder
                        )


                    # smazeme samotne prevzeti
                    session.delete(
                        assignment
                    )

                    session.commit()


                # vratime tlacitka na puvodni zpravu
                if message_id:

                    try:

                        message = await channel.fetch_message(
                            int(message_id)
                        )


                        await message.edit(
                            embed=embed,
                            view=FpNewsActionView(
                                self,
                                news_item_id,
                                status="new",
                            ),
                        )


                    except discord.NotFound:

                        logger.warning(
                            (
                                "Puvodni FP zprava %s "
                                "uz neexistuje"
                            ),
                            message_id
                        )


                    except discord.HTTPException:

                        logger.exception(
                            (
                                "Nepodarilo se upravit "
                                "FP zpravu %s"
                            ),
                            message_id
                        )


                # informace modum
                await channel.send(
                    content=(
                        f"<@{old_user_id}> "
                        "prevzata FP aktualita byla "
                        "automaticky uvolnena pro ostatni, "
                        "protoze zustala prilis dlouho "
                        "nezpracovana."
                    ),
                    allowed_mentions=discord.AllowedMentions(
                        users=True,
                        roles=False,
                        everyone=False,
                    ),
                )


                logger.info(
                    (
                        "FP aktualita %s byla "
                        "automaticky uvolnena"
                    ),
                    news_item_id
                )


        except Exception:

            logger.exception(
                "Chyba pri automatickem uvolnovani FP aktualit"
            )


    @check_fp_news_auto_release.before_loop
    async def before_check_fp_news_auto_release(self):

        await self.bot.wait_until_ready()


    @check_fp_news_reminders.before_loop
    async def before_check_fp_news_reminders(self):

        await self.bot.wait_until_ready()


    @tasks.loop(
        hours=CHECK_INTERVAL_HOURS
    )
    async def check_fp_news(self):

        try:

            # -------------------
            # AKTUALITY
            # -------------------

            news_html = (
                await self._download_news_page()
            )

            news_items = parse_news(
                news_html
            )


            if TEST_FP_NEWS:

                news_items.append(
                    NewsItem(
                        title=(
                            "TEST - BizzyBot FP watcher"
                        ),
                        published_date="10. 10. 2026",
                        url=(
                            "https://www.fp.vut.cz/"
                            "cs/o-fakulte/aktuality"
                            "?bizzybot-test=12"
                        ),
                    )
                )


            # -------------------
            # KALENDAR AKCI
            # -------------------

            events_html = (
                await self._download_events_page()
            )

            events = parse_events(
                events_html
            )


            if TEST_FP_EVENTS:

                events.append(
                    CalendarEvent(
                        title=(
                            "TEST - BizzyBot FP kalendar"
                        ),
                        event_date="10.10.2026",
                        url=(
                            "https://www.fp.vut.cz/"
                            "cs/o-fakulte/aktuality"
                            "?bizzybot-test=11"
                        ),
                    )
                )


            # -------------------
            # ODSTRANENI DUPLICIT
            # -------------------

            # pokud je stejna polozka zaroven
            # v aktualitach i kalendari,
            # bereme ji pouze jako akci
            event_urls = {
                event.url
                for event in events
            }


            news_items = [
                item
                for item in news_items
                if item.url not in event_urls
            ]


            # -------------------
            # ZPRACOVANI AKTUALIT
            # -------------------

            await self._process_news(
                news_items,
                source="news",
            )


            # -------------------
            # ZPRACOVANI AKCI
            # -------------------

            event_items = [
                NewsItem(
                    title=(
                        f"📅 AKCE: "
                        f"{event.title}"
                    ),
                    published_date=(
                        event.event_date
                    ),
                    url=event.url,
                )
                for event in events
            ]


            await self._process_news(
                event_items,
                source="events",
            )


        except Exception:

            logger.exception(
                (
                    "Chyba pri kontrole "
                    "FP aktualit nebo akci"
                )
            )


    @check_fp_news.before_loop
    async def before_check_fp_news(self):

        await self.bot.wait_until_ready()


    @app_commands.command(
        name="fpstats",
        description="Ukaze statistiku dokoncenych FP aktualit a akci."
    )
    @app_commands.checks.check(
        user_is_allowed
    )
    @app_commands.guild_only()
    async def fpstats(
        self,
        interaction: discord.Interaction
    ):

        with SessionLocal() as session:

            completed = (
                session.query(FpNewsAssignment)
                .filter(
                    FpNewsAssignment.status == "done"
                )
                .all()
            )


            counts = Counter()
            news_counts = Counter()
            event_counts = Counter()


            for assignment in completed:

                user_id = (
                    assignment.assigned_user_id
                )

                counts[user_id] += 1


                item = session.get(
                    FpNewsItem,
                    assignment.news_item_id
                )


                if (
                    item is not None
                    and item.title.startswith(
                        "📅 AKCE:"
                    )
                ):

                    event_counts[user_id] += 1

                else:

                    news_counts[user_id] += 1


        if not counts:

            embed = discord.Embed(
                title="FP statistiky",
                description=(
                    "Zatim nebyla dokoncena "
                    "zadna FP aktualita."
                ),
                color=discord.Color.blue(),
            )

            await interaction.response.send_message(
                embed=embed
            )

            return


        sorted_users = sorted(
            counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )


        lines = []


        for position, (user_id, count) in enumerate(
            sorted_users,
            start=1
        ):

            if position == 1:
                position_text = "🥇"

            elif position == 2:
                position_text = "🥈"

            elif position == 3:
                position_text = "🥉"

            else:
                position_text = f"**{position}.**"


            lines.append(
                (
                    f"{position_text} "
                    f"<@{user_id}> — "
                    f"**{count}** "
                    f"(aktuality: {news_counts[user_id]}, "
                    f"akce: {event_counts[user_id]})"
                )
            )


        embed = discord.Embed(
            title="FP statistiky",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )


        embed.set_footer(
            text=(
                f"Celkem dokoncenych polozek: {len(completed)}"
                f"{len(completed)}"
            )
        )


        await interaction.response.send_message(
            embed=embed
        )

    @fpstats.error
    async def fpstats_error(
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
            "Chyba v /fpstats",
            exc_info=error
        )


        if interaction.response.is_done():

            await interaction.followup.send(
                "Pri nacitani FP statistik nastala chyba.",
                ephemeral=True,
            )

        else:

            await interaction.response.send_message(
                "Pri nacitani FP statistik nastala chyba.",
                ephemeral=True,
            )

    @app_commands.command(
        name="fppending",
        description="Ukaze FP aktuality, ktere cekaji na zpracovani."
    )
    @app_commands.checks.check(
        user_is_allowed
    )
    @app_commands.guild_only()
    async def fppending(
        self,
        interaction: discord.Interaction
    ):

        with SessionLocal() as session:

            items = (
                session.query(FpNewsItem)
                .filter(
                    FpNewsItem.discord_message_id.isnot(None)
                )
                .order_by(
                    FpNewsItem.id.desc()
                )
                .all()
            )


            unassigned = []
            claimed = []


            for item in items:

                assignment = (
                    session.query(FpNewsAssignment)
                    .filter(
                        FpNewsAssignment.news_item_id
                        == item.id
                    )
                    .first()
                )


                # zadne prirazeni = ceka na nekoho
                if assignment is None:

                    unassigned.append(
                        {
                            "title": item.title,
                            "message_id": item.discord_message_id,
                        }
                    )


                elif assignment.status == "claimed":

                    claimed.append(
                        {
                            "title": item.title,
                            "message_id": item.discord_message_id,
                            "user_id": assignment.assigned_user_id,
                            "claimed_at": assignment.claimed_at,
                        }
                    )


        embed = discord.Embed(
            title="FP Pending",
            description=(
                f"🆕 Nezpracovane: **{len(unassigned)}**\n"
                f"🟡 Prevzate: **{len(claimed)}**"
            ),
            color=discord.Color.blue(),
        )


        guild_id = interaction.guild_id


        if unassigned:

            lines = []

            for item in unassigned[:8]:

                if (
                    guild_id is not None
                    and item["message_id"]
                ):

                    url = (
                        f"https://discord.com/channels/"
                        f"{guild_id}/"
                        f"{TARGET_CHANNEL_ID}/"
                        f"{item['message_id']}"
                    )

                    line = (
                        f"• [{item['title'][:70]}]"
                        f"({url})"
                    )

                else:

                    line = (
                        f"• {item['title'][:70]}"
                    )

                lines.append(
                    line
                )


            if len(unassigned) > 8:

                lines.append(
                    f"*... a dalsich "
                    f"{len(unassigned) - 8}*"
                )


            embed.add_field(
                name="🆕 Ceka na prevzeti",
                value="\n".join(lines),
                inline=False,
            )


        if claimed:

            lines = []

            for item in claimed[:8]:

                age = format_assignment_age(
                    item["claimed_at"]
                )


                if (
                    guild_id is not None
                    and item["message_id"]
                ):

                    url = (
                        f"https://discord.com/channels/"
                        f"{guild_id}/"
                        f"{TARGET_CHANNEL_ID}/"
                        f"{item['message_id']}"
                    )

                    title = (
                        f"[{item['title'][:60]}]"
                        f"({url})"
                    )

                else:

                    title = item["title"][:60]


                lines.append(
                    (
                        f"• {title}\n"
                        f"  ↳ <@{item['user_id']}> "
                        f"— {age}"
                    )
                )


            if len(claimed) > 8:

                lines.append(
                    f"*... a dalsich "
                    f"{len(claimed) - 8}*"
                )


            embed.add_field(
                name="🟡 Prevzate",
                value="\n".join(lines),
                inline=False,
            )


        if not unassigned and not claimed:

            embed.description = (
                "✅ Zadna FP aktualita ani akce momentalne "
                "neceka na zpracovani."
            )


        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    @fppending.error
    async def fppending_error(
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
            "Chyba v /fppending",
            exc_info=error
        )


        if interaction.response.is_done():

            await interaction.followup.send(
                "Pri nacitani FP aktualit nastala chyba.",
                ephemeral=True,
            )

        else:

            await interaction.response.send_message(
                "Pri nacitani FP aktualit nastala chyba.",
                ephemeral=True,
            )

    @app_commands.command(
        name="fpeventcheck",
        description=(
            "Zkontroluje akce, ktere "
            "BizzyBot vidi v kalendari FP."
        )
    )
    @app_commands.checks.check(
        user_is_allowed
    )
    @app_commands.guild_only()
    async def fpeventcheck(
        self,
        interaction: discord.Interaction
    ):

        try:

            html = (
                await self._download_events_page()
            )

            events = parse_events(
                html
            )


        except Exception as error:

            await interaction.response.send_message(
                (
                    "FP kalendar se nepodarilo nacist.\n"
                    f"Chyba: `{type(error).__name__}`"
                ),
                ephemeral=True,
            )

            return


        if not events:

            await interaction.response.send_message(
                (
                    "Stranka se nacetla, ale bot "
                    "na ni nenasel zadnou akci."
                ),
                ephemeral=True,
            )

            return


        preview = "\n".join(
            (
                f"• **{event.event_date}** — "
                f"[{event.title}]({event.url})"
            )
            for event in events[:5]
        )


        embed = discord.Embed(
            title="FP Event Check",
            description=(
                f"Bot aktualne vidi "
                f"**{len(events)} akci**.\n\n"
                f"{preview}"
            ),
            color=discord.Color.blue(),
        )


        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    @fpeventcheck.error
    async def fpeventcheck_error(
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
            "Chyba v /fpeventcheck",
            exc_info=error
        )


        if interaction.response.is_done():

            await interaction.followup.send(
                (
                    "Pri kontrole FP kalendare "
                    "nastala chyba."
                ),
                ephemeral=True,
            )

        else:

            await interaction.response.send_message(
                (
                    "Pri kontrole FP kalendare "
                    "nastala chyba."
                ),
                ephemeral=True,
            )

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