import io
import math
import random

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFilter, ImageOps


CANVAS_W = 520
CANVAS_H = 520
AVATAR_SIZE = 230
FRAME_COUNT = 12
FRAME_DURATION_MS = 70


def crop_avatar_circle(raw_bytes: bytes, size: int) -> Image.Image:
    avatar = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
    avatar = ImageOps.fit(avatar, (size, size), method=Image.Resampling.LANCZOS)

    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size - 1, size - 1), fill=255)
    avatar.putalpha(mask)

    return avatar


def create_background() -> Image.Image:
    return Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))


def draw_shower_hardware(draw: ImageDraw.ImageDraw):
    pipe = (150, 152, 160, 255)
    head = (114, 116, 124, 255)
    dark = (76, 78, 84, 255)

    draw.rounded_rectangle((360, 48, 388, 164), radius=14, fill=pipe)
    draw.rounded_rectangle((246, 140, 388, 168), radius=14, fill=pipe)
    draw.ellipse((220, 142, 290, 212), fill=head)

    for row in range(3):
        for col in range(4):
            x = 236 + col * 14
            y = 158 + row * 12
            draw.ellipse((x, y, x + 5, y + 5), fill=dark)


def add_shadow(scene: Image.Image, avatar_box: tuple[int, int, int, int]):
    shadow = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)

    x0, y0, x1, y1 = avatar_box
    shadow_draw.ellipse(
        (x0 + 14, y1 - 4, x1 - 14, y1 + 34),
        fill=(0, 0, 0, 90),
    )

    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    scene.alpha_composite(shadow)


def add_bubbles(scene: Image.Image, frame_idx: int):
    bubbles = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(bubbles)
    rng = random.Random(1337)

    for i in range(14):
        base_x = 120 + (i * 23) % 220 + rng.randint(-10, 10)
        base_y = 355 + (i * 19) % 120
        float_up = (frame_idx * (5 + i % 3)) % 120

        x = base_x + int(math.sin((frame_idx + i) * 0.7) * 6)
        y = base_y - float_up
        r = 6 + (i % 4) * 2
        alpha = 110 + (i % 3) * 30

        draw.ellipse(
            (x - r, y - r, x + r, y + r),
            outline=(255, 255, 255, alpha),
            width=2,
        )

    bubbles = bubbles.filter(ImageFilter.GaussianBlur(0.5))
    scene.alpha_composite(bubbles)


def add_water(scene: Image.Image, frame_idx: int):
    water = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(water)

    for i in range(16):
        start_x = 234 + i * 4
        wobble = math.sin((frame_idx * 0.8) + i * 0.55) * 8
        start_y = 184 + (i % 2) * 3
        end_x = start_x + wobble + (i - 8) * 1.2
        end_y = 365 + (i % 4) * 10
        width = 2 + (i % 3)
        alpha = 105 + (i % 5) * 18

        draw.line(
            (start_x, start_y, end_x, end_y),
            fill=(133, 197, 255, int(alpha)),
            width=width,
        )

        mid_x = start_x + (end_x - start_x) * 0.55
        mid_y = start_y + (end_y - start_y) * 0.55
        draw.ellipse(
            (mid_x - 2, mid_y - 6, mid_x + 2, mid_y + 6),
            fill=(172, 223, 255, min(255, int(alpha) + 20)),
        )

        splash_x = end_x + math.sin(frame_idx + i) * 5
        splash_y = end_y + (frame_idx * 2 + i) % 12
        draw.ellipse(
            (splash_x - 3, splash_y - 3, splash_x + 3, splash_y + 3),
            fill=(180, 228, 255, 190),
        )

    water = water.filter(ImageFilter.GaussianBlur(0.6))
    scene.alpha_composite(water)


def build_frame(avatar: Image.Image, frame_idx: int) -> Image.Image:
    scene = create_background()
    draw = ImageDraw.Draw(scene)

    draw_shower_hardware(draw)

    avatar_x = (CANVAS_W - AVATAR_SIZE) // 2
    avatar_y = 190
    avatar_box = (avatar_x, avatar_y, avatar_x + AVATAR_SIZE, avatar_y + AVATAR_SIZE)

    add_shadow(scene, avatar_box)
    scene.alpha_composite(avatar, (avatar_x, avatar_y))
    add_water(scene, frame_idx)
    add_bubbles(scene, frame_idx)

    return scene


def build_shower_gif(raw_bytes: bytes) -> io.BytesIO:
    avatar = crop_avatar_circle(raw_bytes, AVATAR_SIZE)
    frames = [build_frame(avatar, idx) for idx in range(FRAME_COUNT)]

    output = io.BytesIO()
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_DURATION_MS,
        loop=0,
        disposal=2,
        optimize=False,
        transparency=0,
    )
    output.seek(0)

    return output


class Shower(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="sprcha",
        description="Udela shower gif z profilovky vybraneho uzivatele."
    )
    @app_commands.guild_only()
    async def sprcha(self, interaction: discord.Interaction, uzivatel: discord.Member):
        await interaction.response.defer()

        try:
            avatar_asset = uzivatel.display_avatar.replace(format="png", size=512)
            raw_bytes = await avatar_asset.read()
            gif_buffer = build_shower_gif(raw_bytes)
        except Exception as error:
            await interaction.followup.send(
                f"Nepodarilo se pripravit shower gif: {error}",
                ephemeral=True,
            )
            return

        file = discord.File(fp=gif_buffer, filename="sprcha.gif")
        await interaction.followup.send(file=file)


async def setup(bot: commands.Bot):
    await bot.add_cog(Shower(bot))
