import re
from pathlib import Path

import discord
from discord.ext import commands


OWNER_IDS = {
    685958402442133515,
}


ROOT_DIR = Path(__file__).resolve().parent.parent

DESCRIPTIONS_FILE = (
    ROOT_DIR
    / "text_files"
    / "channel_descriptions.txt"
)


LINE_PATTERN = re.compile(
    r"^\(([^()]+)\)\s+\((.*)\)$"
)


def can_run_script(ctx: commands.Context) -> bool:
    return ctx.author.id in OWNER_IDS


class ChannelDescriptions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def send_lines(
        self,
        ctx: commands.Context,
        header: str,
        lines: list[str],
    ):
        if not lines:
            return

        text = header + "\n"

        for line in lines:
            addition = line + "\n"

            if len(text) + len(addition) > 1900:
                await ctx.send(text)
                text = ""

            text += addition

        if text:
            await ctx.send(text)

    def load_rules(
        self,
    ) -> tuple[
        dict[str, str],
        list[str],
        list[str],
    ]:
        rules = {}
        invalid_lines = []
        conflicting_codes = set()

        if not DESCRIPTIONS_FILE.exists():
            invalid_lines.append(
                "Soubor channel_descriptions.txt neexistuje"
            )

            return (
                rules,
                invalid_lines,
                [],
            )

        raw_input = DESCRIPTIONS_FILE.read_text(
            encoding="utf-8"
        )

        if not raw_input.strip():
            invalid_lines.append(
                "Soubor channel_descriptions.txt je prazdny"
            )

            return (
                rules,
                invalid_lines,
                [],
            )

        for line_number, line in enumerate(
            raw_input.splitlines(),
            start=1,
        ):
            line = line.strip()

            if not line:
                continue

            match = LINE_PATTERN.match(line)

            if match is None:
                invalid_lines.append(
                    f"Radek {line_number} ma spatny format {line}"
                )
                continue

            code = match.group(1).strip().lower()
            description = match.group(2).strip()

            if not code:
                invalid_lines.append(
                    f"Radek {line_number} nema zkratku"
                )
                continue

            if not description:
                invalid_lines.append(
                    f"Radek {line_number} nema popisek"
                )
                continue

            if len(description) > 1024:
                invalid_lines.append(
                    f"Radek {line_number} ma popisek delsi nez 1024 znaku"
                )
                continue

            if code in conflicting_codes:
                continue

            if code in rules:
                if rules[code] != description:
                    conflicting_codes.add(code)
                    rules.pop(code, None)

                continue

            rules[code] = description

        return (
            rules,
            invalid_lines,
            sorted(conflicting_codes),
        )

    def topic_contains_description(
        self,
        topic: str,
        description: str,
    ) -> bool:
        if topic == description:
            return True

        if topic.endswith(
            f", {description}"
        ):
            return True

        return False

    @commands.command(name="setChannelDescriptions")
    @commands.check(can_run_script)
    async def set_channel_descriptions(
        self,
        ctx: commands.Context,
    ):
        guild = ctx.guild

        if guild is None:
            await ctx.send(
                "Tento prikaz lze pouzit pouze na serveru"
            )
            return

        rules, invalid_lines, conflicting_codes = (
            self.load_rules()
        )

        if not rules and invalid_lines:
            await self.send_lines(
                ctx,
                "Chyby v channel_descriptions.txt",
                invalid_lines,
            )

            await ctx.send(
                "Nebyla nalezena zadna platna pravidla"
            )
            return

        if invalid_lines:
            await self.send_lines(
                ctx,
                "Tyto radky budou preskoceny",
                invalid_lines,
            )

        if conflicting_codes:
            await self.send_lines(
                ctx,
                "Tyto zkratky maji vice ruznych popisku a budou preskoceny",
                conflicting_codes,
            )

        planned_changes = []

        matched_codes = set()

        already_assigned_channels = []
        channels_without_rule = []
        too_long_channels = []

        for channel in guild.text_channels:
            channel_name = channel.name.lower()

            if channel_name.endswith("-private"):
                subject_code = channel_name.removesuffix(
                    "-private"
                )

            elif channel_name.endswith("-public"):
                subject_code = channel_name.removesuffix(
                    "-public"
                )

            else:
                continue

            if subject_code not in rules:
                channels_without_rule.append(
                    channel.name
                )
                continue

            description = rules[subject_code]

            matched_codes.add(
                subject_code
            )

            current_topic = (
                channel.topic.strip()
                if channel.topic
                else ""
            )

            if self.topic_contains_description(
                current_topic,
                description,
            ):
                already_assigned_channels.append(
                    channel.name
                )
                continue

            if current_topic:
                new_topic = (
                    f"{current_topic}, {description}"
                )
            else:
                new_topic = description

            if len(new_topic) > 1024:
                too_long_channels.append(
                    f"{channel.name} {len(new_topic)} znaku"
                )
                continue

            planned_changes.append(
                (
                    channel,
                    subject_code,
                    new_topic,
                )
            )

        unmatched_codes = sorted(
            code
            for code in rules
            if code not in matched_codes
        )

        changed_channels = []

        original_topics = {}

        try:
            for (
                channel,
                subject_code,
                new_topic,
            ) in planned_changes:

                original_topics[channel.id] = (
                    channel.topic
                )

                await channel.edit(
                    topic=new_topic,
                    reason=(
                        "Append subject channel description "
                        f"for {subject_code}"
                    ),
                )

                changed_channels.append(
                    channel
                )

        except (
            discord.Forbidden,
            discord.HTTPException,
        ) as error:

            rollback_failed = []

            for changed_channel in reversed(
                changed_channels
            ):
                try:
                    await changed_channel.edit(
                        topic=original_topics[
                            changed_channel.id
                        ],
                        reason=(
                            "Rollback subject channel "
                            "description update"
                        ),
                    )

                except (
                    discord.Forbidden,
                    discord.HTTPException,
                ):
                    rollback_failed.append(
                        changed_channel.name
                    )

            await ctx.send(
                "Pri uprave nastala chyba\n"
                f"{type(error).__name__} {error}\n"
                "Pokusil jsem se vratit provedene zmeny"
            )

            if rollback_failed:
                await self.send_lines(
                    ctx,
                    "Rollback selhal u techto mistnosti",
                    rollback_failed,
                )

            return

        await ctx.send(
            "Channel descriptions finished\n"
            f"Platnych pravidel {len(rules)}\n"
            f"Konfliktnich zkratek {len(conflicting_codes)}\n"
            f"Chybnych radku {len(invalid_lines)}\n"
            f"Zmenenych mistnosti {len(changed_channels)}\n"
            f"Popisek uz byl prirazen {len(already_assigned_channels)}\n"
            f"Zkratek bez mistnosti {len(unmatched_codes)}\n"
            f"Mistnosti bez odpovidajici zkratky {len(channels_without_rule)}\n"
            f"Preskoceno kvuli delce {len(too_long_channels)}"
        )

        if changed_channels:
            await self.send_lines(
                ctx,
                "Zmenene mistnosti",
                [
                    channel.name
                    for channel in changed_channels
                ],
            )

        if already_assigned_channels:
            await self.send_lines(
                ctx,
                "Mistnosti kde popisek uz byl",
                sorted(already_assigned_channels),
            )

        if unmatched_codes:
            await self.send_lines(
                ctx,
                "Zkratky bez nalezene mistnosti",
                unmatched_codes,
            )

        if channels_without_rule:
            await self.send_lines(
                ctx,
                "Mistnosti bez odpovidajici zkratky v souboru",
                sorted(channels_without_rule),
            )

        if too_long_channels:
            await self.send_lines(
                ctx,
                "Mistnosti preskocene kvuli maximalni delce popisku",
                too_long_channels,
            )

    @set_channel_descriptions.error
    async def set_channel_descriptions_error(
        self,
        ctx: commands.Context,
        error,
    ):
        if isinstance(
            error,
            commands.CheckFailure,
        ):
            await ctx.send(
                "Tento prikaz muze pouzit pouze vlastnik bota"
            )
            return

        raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(
        ChannelDescriptions(bot)
    )