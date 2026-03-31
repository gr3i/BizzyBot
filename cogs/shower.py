import io
import math
import random

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFilter


ALLOWED_USER_IDS = {
    685958402442133515,
}

ALLOWED_ROLE_IDS = {
    1358898283782602932,
    1359508102222975087,
    1370841996977246218,
    1370842282084925541,
}


def user_is_allowed(interaction: discord.Interaction) -> bool:
    if interaction.user.id in ALLOWED_USER_IDS:
        return True

    member = interaction.user if isinstance(interaction.user, discord.Member) else None
    if member:
        return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)

    return False


def create_circular_avatar(avatar: Image.Image, size: int = 420) -> Image.Image:
    avatar = avatar.convert("RGBA").resize((size, size))

    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)

    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(avatar, (0, 0), mask)
    return result


def create_shower_image(avatar_bytes: bytes, username: str) -> io.BytesIO:
    base_size = (900, 900)
    canvas = Image.new("RGBA", base_size, (235, 245, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # lehky gradient pozadi
    for y in range(base_size[1]):
        ratio = y / base_size[1]
        r = int(235 - 20 * ratio)
        g = int(245 - 10 * ratio)
        b = int(255 - 5 * ratio)
        draw.line((0, y, base_size[0], y), fill=(r, g, b, 255))

    # "koupelna" / stena
    tile_color_1 = (220, 230, 240, 255)
    tile_color_2 = (210, 222, 235, 255)
    tile_size = 90

    for y in range(0, 700, tile_size):
        for x in range(0, 900, tile_size):
            color = tile_color_1 if ((x // tile_size) + (y // tile_size)) % 2 == 0 else tile_color_2
            draw.rectangle((x, y, x + tile_size, y + tile_size), fill=color, outline=(190, 200, 210, 255))

    # spodni cast
    draw.rectangle((0, 700, 900, 900), fill=(180, 190, 200, 255))

    # nacteni avataru
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar_circle = create_circular_avatar(avatar, 420)

    # stin pod avatar
    shadow = Image.new("RGBA", (460, 460), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.ellipse((20, 30, 440, 450), fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    canvas.alpha_composite(shadow, (220, 215))

    # avatar doprostred
    canvas.alpha_composite(avatar_circle, (240, 190))

    # jednoducha sprchova hlavice
    pipe_color = (150, 150, 155, 255)
    head_color = (110, 110, 115, 255)

    draw.rounded_rectangle((620, 70, 660, 250), radius=18, fill=pipe_color)
    draw.rounded_rectangle((500, 220, 660, 260), radius=18, fill=pipe_color)
    draw.ellipse((450, 230, 560, 320), fill=head_color)

    # dirky ve sprchove hlavici
    for row in range(3):
        for col in range(5):
            x = 470 + col * 18
            y = 248 + row * 16
            draw.ellipse((x, y, x + 7, y + 7), fill=(70, 70, 75, 255))

    # kapky vody
    water = Image.new("RGBA", base_size, (0, 0, 0, 0))
    water_draw = ImageDraw.Draw(water)

    for i in range(70):
        start_x = random.randint(470, 550)
        start_y = random.randint(285, 345)
        length = random.randint(120, 260)
        drift = random.randint(-35, 35)

        end_x = start_x + drift
        end_y = start_y + length

        water_draw.line(
            (start_x, start_y, end_x, end_y),
            fill=(120, 190, 255, random.randint(110, 180)),
            width=random.randint(2, 4),
        )

        # mala kapka na konci
        water_draw.ellipse(
            (end_x - 5, end_y - 5, end_x + 5, end_y + 5),
            fill=(140, 205, 255, random.randint(120, 190)),
        )

    water = water.filter(ImageFilter.GaussianBlur(1))
    canvas = Image.alpha_composite(canvas, water)

    # par bublin
    bubbles = Image.new("RGBA", base_size, (0, 0, 0, 0))
    bubbles_draw = ImageDraw.Draw(bubbles)

    for _ in range(18):
        radius = random.randint(12, 28)
        x = random.randint(180, 650)
        y = random.randint(430, 760)
        bubbles_draw.ellipse(
            (x, y, x + radius, y + radius),
            outline=(255, 255, 255, 180),
            width=3,
        )

    canvas = Image.alpha_composite(canvas, bubbles)

    # text bez nutnosti externiho fontu
    text_bar = Image.new("RGBA", (900, 100), (20, 20, 30, 180))
    canvas.alpha_composite(text_bar, (0, 800))

    draw = ImageDraw.Draw(canvas)
    caption = f"{username} je ve sprse"
    draw.text((30, 835), caption, fill=(255, 255, 255, 255))

    output = io.BytesIO()
    canvas.save(output, format="PNG")
    output.seek(0)
    return output


class Shower(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="sprcha",
        description="Vezme profilovku uzivatele a posle ji jako shower edit."
    )
    @app_commands.checks.check(user_is_allowed)
    @app_commands.guild_only()
    async def sprcha(self, interaction: discord.Interaction, uzivatel: discord.Member):
        await interaction.response.defer()

        avatar_asset = uzivatel.display_avatar.replace(size=512, format="png")
        avatar_bytes = await avatar_asset.read()

        image_buffer = create_shower_image(avatar_bytes, uzivatel.display_name)

        file = discord.File(fp=image_buffer, filename="sprcha.png")
        await interaction.followup.send(
            content=f"🚿 {uzivatel.mention} dostal sprchu.",
            file=file
        )

    @sprcha.error
    async def sprcha_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            if interaction.response.is_done():
                await interaction.followup.send(
                    "Na tento příkaz nemáš oprávnění.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "Na tento příkaz nemáš oprávnění.",
                    ephemeral=True
                )
            return

        if interaction.response.is_done():
            await interaction.followup.send(
                f"Něco se pokazilo: {error}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Něco se pokazilo: {error}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Shower(bot))
