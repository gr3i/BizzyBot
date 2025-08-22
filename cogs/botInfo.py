import os
import platform
import time
from datetime import timedelta

import discord
from discord.ext import commands
from discord import app_commands, Interaction, Embed

import psutil


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
        return discord.Color.red()

    # /bot (skupina příkazů)
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

        # RAM aktuálního procesu (RSS v MB)
        ram_mb = psutil.Process().memory_info().rss / 1024 / 1024

        # jen orientační počet zaregistrovaných (v aktuálním scope)
        total_commands = len(self.bot.tree.get_commands())

        embed = Embed(
            title="🤖 BizzyBot – FP Discord Bot",
            color=self.get_latency_color(latency_ms)
        )
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        # aplikační ID vezmeme z klienta (ať to není napevno)
        app_id = getattr(self.bot, "application_id", "—")
        embed.add_field(name="🆔 Aplikační ID", value=str(app_id), inline=False)

        embed.add_field(name="📈 Odezva & ⏱️ Uptime",
                        value=f"**{latency_ms} ms, {uptime}**",
                        inline=False)

        embed.add_field(name="⚙️ Technologie",
                        value=f"Python `{python_version}`\ndiscord.py `{discord_version}`",
                        inline=False)

        embed.add_field(name="💾 Paměť",
                        value=f"{ram_mb:.2f} MB",
                        inline=False)

        embed.add_field(name="📚 Příkazy (v tomto scope)",
                        value=f"**{total_commands}**",
                        inline=False)

        embed.add_field(name="🔗 Odkaz",
                        value="[🌐 GitHub](https://github.com/gr3i/BizzyBot)",
                        inline=False)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Přidá cog a ZAREGISTRUJE skupinu /bot do CommandTree."""
    cog = BotInfo(bot)
    await bot.add_cog(cog)

    GUILD_ID = int(os.getenv("GUILD_ID", "0"))
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.add_command(cog.botCommand, guild=guild)
        print(f"[botInfo] group '/bot' registered for guild {GUILD_ID}")
    else:
        bot.tree.add_command(cog.botCommand)
        print("[botInfo] group '/bot' registered globally")

