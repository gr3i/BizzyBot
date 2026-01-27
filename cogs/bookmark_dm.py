import discord
from discord.ext import commands


class BookmarkDM(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # reaguj jen na emoji zalozky
        if str(payload.emoji) != "🔖":
            return

        # ignoruj reakce od botu
        if payload.member and payload.member.bot:
            return

        # musi jit o reakci na serveru
        if payload.guild_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        channel = guild.get_channel(payload.channel_id)
        if channel is None:
            return

        # uzivatel, ktery reagoval
        user = payload.member or guild.get_member(payload.user_id)
        if user is None or user.bot:
            return

        # nacti zpravu
        try:
            message = await channel.fetch_message(payload.message_id)
        except (discord.NotFound, discord.Forbidden):
            return

        # volitelne: neukladej vlastni zpravy
        # if message.author.id == user.id:
        #     return

        # priprav text zpravy
        text = message.content.strip() if message.content else "*[bez textu]*"
        jump_url = message.jump_url

        embed = discord.Embed(description=text)
        embed.set_author(
            name=f"{message.author} v #{getattr(channel, 'name', 'kanal')}",
            icon_url=getattr(message.author.display_avatar, "url", None),
        )
        embed.add_field(
            name="Odkaz na zprávu <:huggers:1379563250307563550>",
            value=jump_url,
            inline=False
        )
        embed.timestamp = message.created_at

        # zpracuj prilohy
        if message.attachments:
            first = message.attachments[0]
            if first.content_type and first.content_type.startswith("image/"):
                embed.set_image(url=first.url)
            else:
                embed.add_field(
                    name="Priloha",
                    value=first.url,
                    inline=False
                )

        # posli zpravu do soukrome zpravy
        try:
            await user.send(embed=embed)
        except discord.Forbidden:
            # uzivatel ma zavrene soukrome zpravy
            return
        except discord.HTTPException:
            return


async def setup(bot: commands.Bot):
    await bot.add_cog(BookmarkDM(bot))

