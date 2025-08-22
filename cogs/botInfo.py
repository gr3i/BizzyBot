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

    def get_latency_color(self, latency: int) -> discord.Color:
        if latency < 100:
            return discord.Color.green()
        elif latency < 300:
            return discord.Color.yellow()
        else:
            return discord.Color.red()

    # Skupina /bot — POZOR: musíme ji přidat do tree v setup() níže
    botCommand = app_commands.Group(
        name="bot",
        description="Bot - Info"
    )

    @botCommand.command(name="info", description="Zobrazí detailní informace o botovi.")
    async def botinfo(self, interaction: Interaction):
        python_version = platform.python_version()
        discord_version = discord.__version__
        latency = round(self.bot.latency * 1000)
        uptime = self.get_uptime()

        # kolik paměti zabírá proces (RSS v MB)
        process = psutil.Process(os.getpid())
        ram_usage_mb = process.memory_info().rss / 1024 / 1024

        total_commands = len(self.bot.tree.get_commands())

        embed = Embed(
            title="🤖 BizzyBot – FP Discord Bot",
            color=self.get_latency_color(latency)
        )
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        embed.add_field(name="🆔 Aplikační ID", value=str(self.bot.application_id), inline=False)
        embed.add_field(name="📈 Odezva & ⏱️ Uptime", value=f"**{latency} ms, {uptime}**", inline=False)
        embed.add_field(name="⚙️ Technologie", value=f"Python `{python_version}`\ndiscord.py `{discord_version}`", inline=False)
        embed.add_field(name="💾 Paměť", value=f"{ram_usage_mb:.2f} MB", inline=False)
        embed.add_field(name="📚 Příkazy", value=f"Celkem: **{total_commands}**", inline=False)
        embed.add_field(name="🔗 Odkaz", value="[🌐 GitHub](https://github.com/gr3i/BizzyBot)", inline=False)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Zaregistruje cog a PŘIDÁ group /bot do CommandTree (per-guild, pokud GUILD_ID existuje)."""
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

