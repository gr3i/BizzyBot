import platform
import discord
from discord.ext import commands
from discord import app_commands, Interaction, Embed
import time
from datetime import timedelta
import psutil
import os   # pro získání PID procesu


@botCommand.command(name="info", description="Zobrazí detailní informace o botovi.")
async def botinfo(self, interaction: Interaction):
python_version = platform.python_version()
discord_version = discord.__version__
latency = round(self.bot.latency * 1000)
uptime = self.get_uptime()

# kolik paměti zabírá proces
process = psutil.Process(os.getpid())
mem_info = process.memory_info()
ram_usage_mb = mem_info.rss / 1024 / 1024

total_commands = len(self.bot.tree.get_commands())

embed = Embed(
    title="🤖 BizzyBot – FP Discord Bot",
    color=self.get_latency_color(latency)
)
embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None) 

# základní informace
embed.add_field(name="🆔 Aplikační ID", value="1358884104413904998", inline=False)

# odezva a uptime
embed.add_field(
    name="📈 Odezva & ⏱️ Uptime",
    value=f"**{latency} ms, {uptime}**",
    inline=False
)

# technické info
embed.add_field(
    name="⚙️ Technologie",
    value=f"Python `{python_version}`\ndiscord.py `{discord_version}`",
    inline=False
)

# paměť
embed.add_field(
    name="💾 Paměť",
    value=f"{ram_usage_mb:.2f} MB",
    inline=False
)

# příkazy
embed.add_field(
    name="📚 Příkazy",
    value=f"Celkem: **{total_commands}**",
    inline=False
)

# GitHub odkaz
embed.add_field(
    name="🔗 Odkaz",
    value="[🌐 GitHub](https://github.com/gr3i/BizzyBot)",
    inline=False
)

await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(BotInfo(bot))

