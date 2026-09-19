from pathlib import Path

import discord
from discord.ext import commands


# Opravneni

FP_ROLE_ID = 1466036385017233636

TEACHER_EMPLOYEE_ROLE_ID = 1431724268160549096
DOKTORAND_ROLE_ID = 1433984072266285097

BIZZYBOT_ROLE_ID = 1358887045115941059
NURI_ROLE_ID = 1531974882978431039

HELPER_ROLE_IDS = {
    1370842977479692338,
    1370843216898953307,
}

SUBMOD_ROLE_IDS = {
    1370841996977246218,
    1370842282084925541,
}

MOD_ROLE_IDS = {
    1359508102222975087,
    1358898283782602932,
}

VUT_ROLE_ID = 1358911329737642014


# Role, ktere maji videt public i private mistnosti
COMMON_ACCESS_IDS = {
    FP_ROLE_ID,
    BIZZYBOT_ROLE_ID,
    NURI_ROLE_ID,
    *HELPER_ROLE_IDS,
    *SUBMOD_ROLE_IDS,
    *MOD_ROLE_IDS,
    VUT_ROLE_ID,
}


PRIVATE_ACCESS_IDS = {
    FP_ROLE_ID,
    BIZZYBOT_ROLE_ID,
    NURI_ROLE_ID,
    *HELPER_ROLE_IDS,
    *SUBMOD_ROLE_IDS,
    *MOD_ROLE_IDS,
    VUT_ROLE_ID,
}


PUBLIC_ACCESS_IDS = {
    *PRIVATE_ACCESS_IDS,
    TEACHER_EMPLOYEE_ROLE_ID,
    DOKTORAND_ROLE_ID,
}

# Pouze pro public mistnosti
PUBLIC_EXTRA_ACCESS_IDS = {
    TEACHER_EMPLOYEE_ROLE_ID,
    DOKTORAND_ROLE_ID,
}


# SOUBORY

ROOT_DIR = Path(__file__).resolve().parent.parent

OLD_SUBJECTS_FILE = ROOT_DIR / "utils" / "subjects.txt"
NEW_SUBJECTS_FILE = ROOT_DIR / "utils" / "subjects_2026.txt"


OWNER_IDS = {
    685958402442133515,
}


def normalize_subject(subject: str) -> str:
    return subject.strip().lower()


def load_subjects(path: Path) -> list[str]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        return [
            line.strip()
            for line in file
            if line.strip()
        ]


def can_run_script(ctx: commands.Context) -> bool:
    return ctx.author.id in OWNER_IDS


class CreateSubjectChannels(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def build_overwrites(
        self,
        guild: discord.Guild,
        allowed_ids: set[int],
    ) -> tuple[dict, list[int]]:

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            )
        }

        missing_ids = []

        for target_id in allowed_ids:
            # Nejdriv zkusim ID jako Discord roli
            target = guild.get_role(target_id)

            # Kdyby nektere ID bylo primo ID uzivatele/bota,
            # umim pouzit i Member overwrite.
            if target is None:
                target = guild.get_member(target_id)

            if target is None:
                missing_ids.append(target_id)
                continue

            overwrites[target] = discord.PermissionOverwrite(
                view_channel=True
            )

        return overwrites, missing_ids

    @commands.command(name="subjectChannelsStatus")
    @commands.check(can_run_script)
    async def subject_channels_status(self, ctx: commands.Context):
        """
        Pouze diagnostika
        Nic nevytvari ani neupravuje
        """

        guild = ctx.guild

        if guild is None:
            await ctx.send("Tento prikaz lze pouzit pouze na serveru")
            return

        new_subjects = load_subjects(NEW_SUBJECTS_FILE)

        if not new_subjects:
            await ctx.send(
                "Soubor utils/subjects_2026.txt je prazdny nebo neexistuje"
            )
            return

        complete = []
        only_public = []
        only_private = []
        completely_missing = []

        public_count = 0
        private_count = 0

        for subject in new_subjects:
            subject_code = normalize_subject(subject)

            public_name = f"{subject_code}-public"
            private_name = f"{subject_code}-private"

            public_channel = discord.utils.get(
                guild.text_channels,
                name=public_name,
            )

            private_channel = discord.utils.get(
                guild.text_channels,
                name=private_name,
            )

            has_public = public_channel is not None
            has_private = private_channel is not None

            if has_public:
                public_count += 1

            if has_private:
                private_count += 1

            if has_public and has_private:
                complete.append(subject_code)

            elif has_public:
                only_public.append(subject_code)

            elif has_private:
                only_private.append(subject_code)

            else:
                completely_missing.append(subject_code)

        missing_public = len(new_subjects) - public_count
        missing_private = len(new_subjects) - private_count

        missing_channels_total = missing_public + missing_private

        await ctx.send(
            "Subject channels status\n"
            f"Celkem kanalu na serveru {len(guild.channels)} / 500\n"
            f"Textovych kanalu {len(guild.text_channels)}\n"
            f"Kategorii {len(guild.categories)}\n\n"
            f"Predmetu v subjects_2026.txt {len(new_subjects)}\n\n"
            f"Kompletni dvojice {len(complete)}\n"
            f"Existujici PUBLIC {public_count}\n"
            f"Existujici PRIVATE {private_count}\n\n"
            f"Jen PUBLIC {len(only_public)}\n"
            f"Jen PRIVATE {len(only_private)}\n"
            f"Nemaji ani jednu mistnost {len(completely_missing)}\n\n"
            f"Chybi PUBLIC mistnosti {missing_public}\n"
            f"Chybi PRIVATE mistnosti {missing_private}\n"
            f"Celkem jeste chybi {missing_channels_total}"
        )

        details = []

        if only_public:
            details.append(
                "Maji pouze PUBLIC\n"
                + ", ".join(only_public)
            )

        if only_private:
            details.append(
                "Maji pouze PRIVATE\n"
                + ", ".join(only_private)
            )

        if completely_missing:
            details.append(
                "Nemaji zadnou mistnost\n"
                + ", ".join(completely_missing)
            )

        for detail in details:
            if len(detail) <= 1900:
                await ctx.send(detail)
                continue

            lines = detail.split(", ")

            chunk = ""

            for line in lines:
                addition = line + ", "

                if len(chunk) + len(addition) > 1900:
                    await ctx.send(chunk.rstrip(", "))
                    chunk = ""

                chunk += addition

            if chunk:
                await ctx.send(chunk.rstrip(", "))

    @commands.command(name="fixSubjectChannelPermissions")
    @commands.check(can_run_script)
    async def fix_subject_channel_permissions(
        self,
        ctx: commands.Context,
    ):
        guild = ctx.guild

        if guild is None:
            await ctx.send(
                "Tento prikaz lze pouzit pouze na serveru"
            )
            return

        all_access_ids = PUBLIC_ACCESS_IDS

        targets = {}
        missing_ids = []

        for target_id in all_access_ids:
            target = guild.get_role(target_id)

            if target is None:
                target = guild.get_member(target_id)

            if target is None:
                try:
                    target = await guild.fetch_member(target_id)
                except discord.NotFound:
                    target = None
                except discord.HTTPException:
                    target = None

            if target is None:
                missing_ids.append(target_id)
            else:
                targets[target_id] = target

        if missing_ids:
            await ctx.send(
                "Nektera ID nebyla nalezena\n"
                + "\n".join(str(target_id) for target_id in missing_ids)
                + "\n\nNic nebylo zmeneno"
            )
            return

        checked_channels = 0
        changed_channels = 0
        unchanged_channels = 0
        removed_overwrites = 0
        added_or_fixed_overwrites = 0

        changed_names = []

        for channel in guild.text_channels:
            channel_name = channel.name.lower()

            if channel_name.endswith("-private"):
                allowed_ids = PRIVATE_ACCESS_IDS

            elif channel_name.endswith("-public"):
                allowed_ids = PUBLIC_ACCESS_IDS

            else:
                continue

            checked_channels += 1

            current_overwrites = channel.overwrites

            expected_ids = set(allowed_ids)
            expected_ids.add(guild.default_role.id)

            channel_needs_update = False

            for target, overwrite in current_overwrites.items():
                if target.id not in expected_ids:
                    removed_overwrites += 1
                    channel_needs_update = True

            everyone_overwrite = channel.overwrites_for(
                guild.default_role
            )

            if everyone_overwrite.view_channel is not False:
                channel_needs_update = True
                added_or_fixed_overwrites += 1

            for target_id in allowed_ids:
                target = targets[target_id]

                overwrite = channel.overwrites_for(target)

                if overwrite.view_channel is not True:
                    channel_needs_update = True
                    added_or_fixed_overwrites += 1

            if not channel_needs_update:
                unchanged_channels += 1
                continue

            new_overwrites = {}

            everyone_overwrite = channel.overwrites_for(
                guild.default_role
            )

            everyone_overwrite.view_channel = False

            new_overwrites[guild.default_role] = everyone_overwrite

            for target_id in allowed_ids:
                target = targets[target_id]

                overwrite = channel.overwrites_for(target)

                overwrite.view_channel = True

                new_overwrites[target] = overwrite

            try:
                await channel.edit(
                    overwrites=new_overwrites,
                    reason="Fix subject channel permissions",
                )

                changed_channels += 1
                changed_names.append(channel.name)

            except discord.Forbidden:
                await ctx.send(
                    f"Missing permissions for {channel.name}"
                )

            except discord.HTTPException as error:
                await ctx.send(
                    f"Failed to update {channel.name} {error}"
                )

        await ctx.send(
            "Subject channel permissions finished\n"
            f"Checked channels {checked_channels}\n"
            f"Changed channels {changed_channels}\n"
            f"Unchanged channels {unchanged_channels}\n"
            f"Removed overwrites {removed_overwrites}\n"
            f"Added or fixed overwrites {added_or_fixed_overwrites}"
        )

        if changed_names:
            text = "Changed channels\n"

            for channel_name in changed_names:
                addition = f"{channel_name}\n"

                if len(text) + len(addition) > 1900:
                    await ctx.send(text)
                    text = ""

                text += addition

            if text:
                await ctx.send(text)

    @commands.command(name="createSubjectChannels_script")
    @commands.check(can_run_script)
    async def create_subject_channels(self, ctx: commands.Context):
        """
        Vytvoří PUBLIC a PRIVATE místnosti pro nové předměty.
        Nevytváří žádné Discord role.
        """

        guild = ctx.guild

        if guild is None:
            await ctx.send("Tento příkaz lze použít pouze na serveru.")
            return

        new_subjects = load_subjects(NEW_SUBJECTS_FILE)

        if not new_subjects:
            await ctx.send(
                "Soubor utils/subjects_2026.txt je prázdný nebo neexistuje."
            )
            return

        public_access_ids = (
            COMMON_ACCESS_IDS
            | PUBLIC_EXTRA_ACCESS_IDS
        )

        private_access_ids = COMMON_ACCESS_IDS

        public_overwrites, public_missing = self.build_overwrites(
            guild,
            public_access_ids,
        )

        private_overwrites, private_missing = self.build_overwrites(
            guild,
            private_access_ids,
        )

        missing_ids = sorted(
            set(public_missing + private_missing)
        )

        if missing_ids:
            await ctx.send(
                "Nektera ID roli nebo uzivatelu nebyla nalezena\n"
                + "\n".join(str(role_id) for role_id in missing_ids)
                + "\nNic nebylo vytvoreno"
            )
            return

        created_public = 0
        created_private = 0

        existing_public = 0
        existing_private = 0

        skipped_legacy_channels = 0

        for subject in new_subjects:
            subject_code = normalize_subject(subject)


            # Kontrola stareho kanalu bez -public/-private
            # napr. #ma1p
            legacy_channel = discord.utils.get(
                guild.text_channels,
                name=subject_code,
            )

            if legacy_channel is not None:
                skipped_legacy_channels += 1
                continue

            public_channel_name = f"{subject_code}-public"
            private_channel_name = f"{subject_code}-private"

            # PUBLIC
            public_channel = discord.utils.get(
                guild.text_channels,
                name=public_channel_name,
            )

            if public_channel is None:
                await guild.create_text_channel(
                    name=public_channel_name,
                    overwrites=public_overwrites,
                )

                created_public += 1

                await ctx.send(
                    f"Public vytvořen #{public_channel_name}"
                )

            else:
                existing_public += 1

            # PRIVATE
            private_channel = discord.utils.get(
                guild.text_channels,
                name=private_channel_name,
            )

            if private_channel is None:
                await guild.create_text_channel(
                    name=private_channel_name,
                    overwrites=private_overwrites,
                )

                created_private += 1

                await ctx.send(
                    f"Private vytvořen #{private_channel_name}"
                )

            else:
                existing_private += 1


        # VYSLEDEK
        await ctx.send(
            "## Hotovo\n"
            f"Nové PUBLIC místnosti: **{created_public}**\n"
            f"Nové PRIVATE místnosti: **{created_private}**\n"
            f"PUBLIC už existovaly: **{existing_public}**\n"
            f"PRIVATE už existovaly: **{existing_private}**\n"
            f"Předměty ze starého subjects.txt: **{skipped_old_subjects}**\n"
            f"Předměty se starým kanálem: **{skipped_legacy_channels}**"
        )

    @create_subject_channels.error
    async def create_subject_channels_error(
        self,
        ctx: commands.Context,
        error,
    ):
        if isinstance(error, commands.CheckFailure):
            await ctx.send(
                "Tento příkaz může použít pouze vlastník bota."
            )
            return

        raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(CreateSubjectChannels(bot))