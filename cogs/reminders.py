import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks

from db.models import ScheduledReminder
from db.session import SessionLocal


logger = logging.getLogger(__name__)


# uzivatel zadava cas normalne v ceskem case
LOCAL_TIMEZONE = ZoneInfo("Europe/Prague")

# bot kontroluje upominky kazdych 30 sekund
CHECK_INTERVAL_SECONDS = 30


ALLOWED_ROLE_IDS = [
    1358898283782602932,
    1370841996977246218,
    1370842977479692338,
]

ALLOWED_USER_IDS = [
    685958402442133515,
]


def user_is_allowed(
    interaction: discord.Interaction
) -> bool:

    if interaction.user.id in ALLOWED_USER_IDS:
        return True

    member = interaction.user

    if isinstance(member, discord.Member):
        return any(
            role.id in ALLOWED_ROLE_IDS
            for role in member.roles
        )

    return False


def utc_now_naive() -> datetime:
    return (
        datetime.now(timezone.utc)
        .replace(tzinfo=None)
    )


def parse_local_datetime(
    date_value: str,
    time_value: str
) -> datetime | None:

    value = (
        f"{date_value.strip()} "
        f"{time_value.strip()}"
    )

    # povolime napr.
    # 20.01.2027
    # nebo 2027-01-20
    for date_format in (
        "%d.%m.%Y",
        "%Y-%m-%d"
    ):

        try:

            local_dt = datetime.strptime(
                value,
                f"{date_format} %H:%M",
            ).replace(
                tzinfo=LOCAL_TIMEZONE
            )

            return (
                local_dt
                .astimezone(timezone.utc)
                .replace(tzinfo=None)
            )

        except ValueError:
            continue

    return None


def utc_to_local(
    value: datetime
) -> datetime:

    return (
        value
        .replace(tzinfo=timezone.utc)
        .astimezone(LOCAL_TIMEZONE)
    )


class ReminderCog(commands.Cog):

    reminder = app_commands.Group(
        name="reminder",
        description="Sprava naplanovanych upominek.",
    )


    def __init__(
        self,
        bot: commands.Bot
    ):

        self.bot = bot

        self.dispatch_reminders.start()


    def cog_unload(self):

        self.dispatch_reminders.cancel()


    async def _not_allowed(
        self,
        interaction: discord.Interaction,
    ):

        await interaction.response.send_message(
            "Na tento prikaz nemas opravneni.",
            ephemeral=True,
        )


    @reminder.command(
        name="create",
        description=(
            "Naplanovani verejne upominky "
            "do vybraneho kanalu."
        )
    )
    @app_commands.guild_only()
    @app_commands.describe(
        kanal=(
            "Kanal, do ktereho ma bot "
            "upominku poslat."
        ),
        datum=(
            "Datum ve formatu DD.MM.RRRR, "
            "napr. 20.01.2027."
        ),
        cas=(
            "Cas ve formatu HH:MM, "
            "napr. 18:00."
        ),
        nadpis="Nadpis upominky.",
        popis="Text upominky.",
    )
    async def reminder_create(
        self,
        interaction: discord.Interaction,
        kanal: discord.TextChannel,
        datum: str,
        cas: str,
        nadpis: str,
        popis: str,
    ):

        if not user_is_allowed(
            interaction
        ):

            await self._not_allowed(
                interaction
            )

            return


        if len(nadpis) > 256:

            await interaction.response.send_message(
                (
                    "Nadpis muze mit maximalne "
                    "256 znaku."
                ),
                ephemeral=True,
            )

            return


        if len(popis) > 4000:

            await interaction.response.send_message(
                (
                    "Popis muze mit maximalne "
                    "4000 znaku."
                ),
                ephemeral=True,
            )

            return


        scheduled_for = parse_local_datetime(
            datum,
            cas,
        )


        if scheduled_for is None:

            await interaction.response.send_message(
                (
                    "Neplatne datum nebo cas. "
                    "Pouzij napr. `20.01.2027` "
                    "a `18:00`."
                ),
                ephemeral=True,
            )

            return


        if scheduled_for <= utc_now_naive():

            await interaction.response.send_message(
                (
                    "Upominku je potreba "
                    "naplanovat do budoucnosti."
                ),
                ephemeral=True,
            )

            return


        if interaction.guild is None:

            await interaction.response.send_message(
                (
                    "Tento prikaz lze pouzit "
                    "jen na serveru."
                ),
                ephemeral=True,
            )

            return


        bot_member = interaction.guild.me


        if bot_member is None:

            await interaction.response.send_message(
                (
                    "Nepodarilo se overit "
                    "opravneni bota."
                ),
                ephemeral=True,
            )

            return


        permissions = kanal.permissions_for(
            bot_member
        )


        if not (
            permissions.view_channel
            and permissions.send_messages
            and permissions.embed_links
        ):

            await interaction.response.send_message(
                (
                    "V tomto kanalu nemam opravneni "
                    "zobrazit kanal, posilat zpravy "
                    "a embedy."
                ),
                ephemeral=True,
            )

            return


        reminder = ScheduledReminder(
            channel_id=str(
                kanal.id
            ),
            title=nadpis,
            description=popis,
            scheduled_for=scheduled_for,
            created_by_user_id=str(
                interaction.user.id
            ),
        )


        with SessionLocal() as session:

            session.add(
                reminder
            )

            session.commit()

            reminder_id = reminder.id


        local_dt = utc_to_local(
            scheduled_for
        )


        await interaction.response.send_message(
            (
                f"Upominka **#{reminder_id}** "
                f"byla naplanovana.\n"
                f"Kanal: {kanal.mention}\n"
                f"Termin: "
                f"**{local_dt:%d.%m.%Y %H:%M}**"
            ),
            ephemeral=True,
        )


    @reminder.command(
        name="list",
        description=(
            "Ukaze cekajici naplanovane upominky."
        )
    )
    @app_commands.guild_only()
    async def reminder_list(
        self,
        interaction: discord.Interaction,
    ):

        if not user_is_allowed(
            interaction
        ):

            await self._not_allowed(
                interaction
            )

            return


        with SessionLocal() as session:

            reminders = (
                session.query(
                    ScheduledReminder
                )
                .filter(
                    ScheduledReminder.sent_at.is_(
                        None
                    )
                )
                .order_by(
                    ScheduledReminder
                    .scheduled_for
                    .asc()
                )
                .limit(20)
                .all()
            )


        if not reminders:

            await interaction.response.send_message(
                (
                    "Nejsou naplanovane zadne "
                    "cekajici upominky."
                ),
                ephemeral=True,
            )

            return


        lines = []


        for reminder in reminders:

            local_dt = utc_to_local(
                reminder.scheduled_for
            )


            lines.append(
                (
                    f"**#{reminder.id}** - "
                    f"<#{reminder.channel_id}> - "
                    f"**{local_dt:%d.%m.%Y %H:%M}**\n"
                    f"{reminder.title}"
                )
            )


        embed = discord.Embed(
            title="Naplanovane upominky",
            description="\n\n".join(
                lines
            ),
            color=discord.Color.blue(),
        )


        if len(reminders) == 20:

            embed.set_footer(
                text=(
                    "Zobrazeno maximalne "
                    "20 nejblizsich upominek."
                )
            )


        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )


    @reminder.command(
        name="cancel",
        description=(
            "Zrusi naplanovanou upominku."
        )
    )
    @app_commands.guild_only()
    @app_commands.describe(
        id=(
            "ID upominky z /reminder list."
        )
    )
    async def reminder_cancel(
        self,
        interaction: discord.Interaction,
        id: int,
    ):

        if not user_is_allowed(
            interaction
        ):

            await self._not_allowed(
                interaction
            )

            return


        with SessionLocal() as session:

            reminder = session.get(
                ScheduledReminder,
                id,
            )


            if reminder is None:

                await interaction.response.send_message(
                    (
                        "Upominka s timto ID "
                        "neexistuje."
                    ),
                    ephemeral=True,
                )

                return


            if reminder.sent_at is not None:

                await interaction.response.send_message(
                    (
                        "Tato upominka uz byla "
                        "odeslana a nelze ji zrusit."
                    ),
                    ephemeral=True,
                )

                return


            title = reminder.title

            session.delete(
                reminder
            )

            session.commit()


        await interaction.response.send_message(
            (
                f"Upominka **#{id} - {title}** "
                f"byla zrusena."
            ),
            ephemeral=True,
        )


    @tasks.loop(
        seconds=CHECK_INTERVAL_SECONDS
    )
    async def dispatch_reminders(self):

        try:

            now = utc_now_naive()


            with SessionLocal() as session:

                reminder_ids = [
                    reminder.id
                    for reminder in (
                        session.query(
                            ScheduledReminder
                        )
                        .filter(
                            ScheduledReminder.sent_at.is_(
                                None
                            ),
                            ScheduledReminder
                            .scheduled_for <= now,
                        )
                        .order_by(
                            ScheduledReminder
                            .scheduled_for
                            .asc()
                        )
                        .limit(20)
                        .all()
                    )
                ]


            for reminder_id in reminder_ids:

                try:

                    with SessionLocal() as session:

                        reminder = session.get(
                            ScheduledReminder,
                            reminder_id,
                        )


                        if (
                            reminder is None
                            or reminder.sent_at
                            is not None
                        ):

                            continue


                        channel_id = int(
                            reminder.channel_id
                        )

                        title = reminder.title

                        description = (
                            reminder.description
                        )


                    channel = self.bot.get_channel(
                        channel_id
                    )


                    if channel is None:

                        channel = (
                            await self.bot.fetch_channel(
                                channel_id
                            )
                        )


                    if not isinstance(
                        channel,
                        discord.abc.Messageable
                    ):

                        raise RuntimeError(
                            (
                                f"Kanal {channel_id} "
                                "nepodporuje zpravy"
                            )
                        )


                    embed = discord.Embed(
                        title=title,
                        description=description,
                        color=discord.Color.blue(),
                    )


                    embed.set_footer(
                        text="Naplanovana upominka"
                    )


                    message = await channel.send(
                        embed=embed
                    )


                    with SessionLocal() as session:

                        reminder = session.get(
                            ScheduledReminder,
                            reminder_id,
                        )


                        if (
                            reminder is None
                            or reminder.sent_at
                            is not None
                        ):

                            continue


                        reminder.sent_at = (
                            utc_now_naive()
                        )

                        reminder.discord_message_id = (
                            str(message.id)
                        )

                        session.commit()


                    logger.info(
                        (
                            "Odeslana upominka #%s "
                            "do kanalu %s"
                        ),
                        reminder_id,
                        channel_id,
                    )


                except Exception:

                    logger.exception(
                        (
                            "Nepodarilo se odeslat "
                            "upominku #%s"
                        ),
                        reminder_id,
                    )


        except Exception:

            logger.exception(
                (
                    "Chyba pri kontrole "
                    "naplanovanych upominek"
                )
            )


    @dispatch_reminders.before_loop
    async def before_dispatch_reminders(
        self
    ):

        await self.bot.wait_until_ready()


async def setup(
    bot: commands.Bot
):

    await bot.add_cog(
        ReminderCog(bot)
    )