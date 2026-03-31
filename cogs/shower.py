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
    pipe_main = (196, 200, 208, 255)
    pipe_shadow = (126, 132, 140, 255)
    metal_dark = (88, 94, 102, 255)
    metal_mid = (120, 126, 134, 255)
    metal_light = (166, 172, 180, 255)
    nozzle = (48, 52, 58, 255)

    # svisla trubka
    draw.rounded_rectangle((372, 42, 396, 150), radius=12, fill=pipe_main)

    # jemny stin na trubce
    draw.rounded_rectangle((388, 42, 396, 150), radius=8, fill=pipe_shadow)

    # vodorovne rameno
    draw.rounded_rectangle((286, 126, 388, 148), radius=11, fill=pipe_main)
    draw.rounded_rectangle((286, 140, 388, 148), radius=7, fill=pipe_shadow)

    # koleno
    draw.ellipse((366, 120, 398, 152), fill=pipe_main)

    # krk hlavice
    draw.rounded_rectangle((270, 132, 30 + 270, 146), radius=7, fill=metal_mid)

    # hlavice sprchy z boku
    draw.rounded_rectangle((206, 118, 284, 170), radius=24, fill=metal_dark)

    # predni kulata cast
    draw.ellipse((192, 118, 236, 170), fill=metal_dark)

    # kovovy highlight
    draw.rounded_rectangle((214, 126, 274, 138), radius=6, fill=metal_light)
    draw.ellipse((200, 125, 224, 139), fill=metal_light)

    # spodni hrana hlavice
    draw.rounded_rectangle((206, 160, 284, 170), radius=5, fill=metal_mid)

    # trysky
    nozzle_positions = [
        (218, 160), (231, 162), (244, 163), (257, 162), (270, 160),
        (224, 168), (237, 169), (250, 169), (263, 168),
    ]

    for x, y in nozzle_positions:
        draw.ellipse((x - 2, y - 1, x + 2, y + 3), fill=nozzle)


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

    for i in range(9):
        base_x = 145 + (i * 26) + rng.randint(-8, 8)
        base_y = 360 + (i * 17) % 95
        float_up = (frame_idx * (4 + i % 2)) % 90

        x = base_x + int(math.sin((frame_idx + i) * 0.65) * 5)
        y = base_y - float_up
        r = 6 + (i % 3) * 3
        alpha = 105 + (i % 3) * 28

        draw.ellipse(
            (x - r, y - r, x + r, y + r),
            outline=(255, 255, 255, alpha),
            width=2,
        )

    bubbles = bubbles.filter(ImageFilter.GaussianBlur(0.35))
    scene.alpha_composite(bubbles)


def add_water(scene: Image.Image, frame_idx: int):
    water = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(water)

    base_points = [
        (218, 164), (231, 166), (244, 167), (257, 166), (270, 164),
        (224, 171), (237, 172), (250, 172), (263, 171),
    ]

    for i, (start_x, start_y) in enumerate(base_points):
        phase = frame_idx * 0.85 + i * 0.55
        length = 150 + (i % 3) * 16
        spread = (i - (len(base_points) - 1) / 2.0) * 5.2
        wobble = math.sin(phase) * 7
        drift = math.cos(phase * 0.9) * 2

        end_x = start_x + spread + wobble + drift
        end_y = start_y + length

        width = 2 + (i % 2)
        alpha = 118 + (i % 4) * 18

        draw.line(
            (start_x, start_y, end_x, end_y),
            fill=(145, 208, 255, alpha),
            width=width,
        )

        # sekundarni slabejsi proud vedle
        draw.line(
            (start_x + 1, start_y, end_x + 3, end_y - 8),
            fill=(190, 232, 255, max(70, alpha - 35)),
            width=1,
        )

        # kapka uprostred
        mid_x = start_x + (end_x - start_x) * 0.52
        mid_y = start_y + (end_y - start_y) * 0.52
        draw.ellipse(
            (mid_x - 2, mid_y - 5, mid_x + 2, mid_y + 5),
            fill=(188, 232, 255, min(255, alpha + 18)),
        )

        # splash dole
        splash_x = end_x + math.sin(frame_idx + i * 0.7) * 5
        splash_y = end_y + ((frame_idx * 2 + i) % 9)
        draw.ellipse(
            (splash_x - 3, splash_y - 3, splash_x + 3, splash_y + 3),
            fill=(198, 236, 255, 185),
        )

    # jemna mlha vody pod hlavici
    mist = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    mist_draw = ImageDraw.Draw(mist)
    mist_draw.ellipse((205, 162, 292, 208), fill=(170, 220, 255, 28))
    mist = mist.filter(ImageFilter.GaussianBlur(6))
    water = Image.alpha_composite(water, mist)

    water = water.filter(ImageFilter.GaussianBlur(0.45))
    scene.alpha_composite(water)


def build_frame(avatar: Image.Image, frame_idx: int) -> Image.Image:
    scene = create_background()
    draw = ImageDraw.Draw(scene)

    draw_shower_hardware(draw)

    avatar_x = (CANVAS_W - AVATAR_SIZE) // 2
    avatar_y = 205
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
