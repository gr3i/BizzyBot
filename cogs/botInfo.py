import platform
import discord
from discord.ext import commands
from discord import app_commands, Interaction, Embed
import time
from datetime import timedelta

class BotInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = time.time()

    def get_uptime(self) -> str:
        return str(timedelta(seconds=int(time.time() - self.start_time)))

    def get_latency_color(self, latency_ms: int) -> discord.Color:
        if latency_ms < 100:
            return discord.Color.green()
        elif latency_ms < 300:
            return discord.Color.yellow()
        else:
            return discord.Color.red()

    def _count_commands(self, guild_id: int | None):
        """
        Vrátí trojici (total, global_count, guild_count).
        Počítá top-level příkazy, groupy i subpříkazy (pomocí qualified_name).
        """
        tree = self.bot.tree

        # global
        global_set = {cmd.qualified_name for cmd in tree.walk_commands()}

        # guild (pokud jsme v kontextu guildy)
        guild_set = set()
        if guild_id:
            guild_obj = discord.Object(id=guild_id)
            guild_set = {cmd.qualified_name for cmd in tree.walk_commands(guild=guild_obj)}

        # sjednocený součet (některé příkazy mohou existovat jak globálně, tak per-guild)
        total_set = global_set | guild_set
        return len(total_set), len(global_set), len(guild_set)

    botCommand = app_commands.Group(
        name="bot",
        description="Bot - Info"
    )

    @botCommand.command(name="info", description="Zobrazí detailní informace o botovi.")
    async def botinfo(self, interaction: Interaction):
        python_version = platform.python_version()
        discord_version = discord.__version__
        latency_ms = round(self.bot.latency * 1000)
        uptime = self.get_uptime()

        # spočti příkazy v kontextu aktuální guildy (pokud je)
        total_commands, global_commands, guild_commands = self._count_commands(
            interaction.guild_id
        )

        embed = Embed(
            title="🤖 BizzyBot – FP Discord Bot",
            color=self.get_latency_color(latency_ms)
        )

        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        # základní informace
        embed.add_field(name="🆔 Aplikační ID", value=str(self.bot.application_id), inline=False)

        # odezva a uptime
        embed.add_field(
            name="📈 Odezva & ⏱️ Uptime",
            value=f"**{latency_ms} ms, {uptime}**",
            inline=False
        )

        # technologie
        embed.add_field(
            name="⚙️ Technologie",
            value=f"Python `{python_version}`\ndiscord.py `{discord_version}`",
            inline=False
        )

        # příkazy (celkem + rozpad)
        embed.add_field(
            name="📚 Příkazy",
            value=(
                f"Celkem: **{total_commands}**\n"
                f"• Global: `{global_commands}`\n"
                f"• Guild: `{guild_commands}`"
            ),
            inline=False
        )

        # GitHub odkaz
        embed.add_field(
            name="🔗 Odkaz",
            value="[🌐 GitHub](https://github.com/gr3i/BizzyBot)",
            inline=False
        )

        # popis latence
        embed.add_field(
            name="🎨 Latency barva",
            value=(
                "🟩 **Zelená** – < 100ms (vynikající)\n"
                "🟨 **Žlutá** – 100–300ms (v pořádku)\n"
                "🟥 **Červená** – > 300ms (vysoká latence)"
            ),
            inline=False
        )

        if self.bot.user and self.bot.user.avatar:
            embed.set_footer(
                text="BizzyBot • Discord bot",
                icon_url=self.bot.user.avatar.url
            )
        else:
            embed.set_footer(text="BizzyBot • Discord bot")

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(BotInfo(bot))

