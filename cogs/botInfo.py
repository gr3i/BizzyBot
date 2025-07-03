import platform
import discord
from discord.ext import commands
from discord import app_commands, Interaction, Embed
import time
from datetime import timedelta

class BotInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    def get_uptime(self):
        return str(timedelta(seconds=int(time.time() - self.start_time)))

    def get_latency_color(self, latency: int) -> discord.Color:
        if latency < 100:
            return discord.Color.green()
        elif latency < 300:
            return discord.Color.yellow()
        else:
            return discord.Color.red()

    @app_commands.command(name="bot_info", description="Zobrazí detailní informace o botovi.")
    async def botinfo(self, interaction: Interaction):
        python_version = platform.python_version()
        discord_version = discord.__version__
        latency = round(self.bot.latency * 1000)
        uptime = self.get_uptime()

        total_commands = len(self.bot.tree.get_commands())
        slash_commands = len([cmd for cmd in self.bot.tree.get_commands() if isinstance(cmd, app_commands.Command)])
        text_commands = len(self.bot.commands)

        embed = Embed(
            title="🤖 BizzyBot – FP Discord Bot",
            color=self.get_latency_color(latency)
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1138833451334424686.webp?size=96&quality=lossless")

        # Základní informace
        embed.add_field(name="🆔 Aplikační ID", value="1358884104413904998", inline=False)

        # Odezva a uptime vedle sebe
        embed.add_field(
            name="📈 Odezva & ⏱️ Uptime",
            value=f"**{latency} ms**\n**{uptime}**",
            inline=False
        )
           

        # Technické info
        embed.add_field(
            name="⚙️ Technologie",
            value=f"Python `{python_version}`\ndiscord.py `{discord_version}`",
            inline=False
        )

        # Příkazy
        embed.add_field(
            name="📚 Příkazy",
            value=(
                f"Celkem: **{total_commands}**\n"
                f"Slash: **{slash_commands}**\n"
                f"Textových: **{text_commands}**"
            ),
            inline=False
        )

        # GitHub odkaz
        embed.add_field(
            name="🔗 Odkaz",
            value="[🌐 GitHub](https://github.com/gr3i/BizzyBot)",
            inline=False
        )

        # Legenda k barvě embedu
        embed.add_field(
            name="🎨 Latency barva",
            value=(
                "🟩 **Zelená** – < 100ms (vynikající)\n"
                "🟨 **Žlutá** – 100–300ms (v pořádku)\n"
                "🟥 **Červená** – > 300ms (vysoká latence)"
            ),
            inline=False
        )

        embed.set_footer(
            text="BizzyBot • Discord bot",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(BotInfo(bot))

