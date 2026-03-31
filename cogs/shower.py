import io
import math
import random

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFilter, ImageOps


CANVAS_W = 520
CANVAS_H = 520
AVATAR_SIZE = 210
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
    line = (25, 25, 25, 255)
    fill = (245, 245, 245, 255)

    # horni trubka
    draw.rounded_rectangle((250, 58, 386, 72), radius=7, fill=fill, outline=line, width=3)

    # pravy svisly kus
    draw.rounded_rectangle((372, 58, 386, 128), radius=7, fill=fill, outline=line, width=3)

    # kratky spoj ke hlavici
    draw.rounded_rectangle((232, 70, 252, 84), radius=6, fill=fill, outline=line, width=3)

    # horni cast hlavice
    draw.ellipse((154, 78, 262, 112), fill=fill, outline=line, width=3)

    # spodni velka hlavice
    draw.ellipse((130, 92, 286, 142), fill=fill, outline=line, width=3)

    # tenka oddelovaci linka na hlavici
    draw.arc((142, 98, 274, 132), start=200, end=340, fill=line, width=2)

    # trysky
    nozzle_y1 = 118
    nozzle_y2 = 125
    for x in range(150, 267, 12):
        draw.ellipse((x, nozzle_y1, x + 2, nozzle_y2), fill=line)


def add_shadow(scene: Image.Image, avatar_box: tuple[int, int, int, int]):
    return


def add_bubbles(scene: Image.Image, frame_idx: int):
    bubbles = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(bubbles)
    rng = random.Random(1337)

    for i in range(9):
        base_x = 118 + (i * 21) + rng.randint(-6, 6)
        base_y = 300 + (i * 15) % 78
        float_up = (frame_idx * (4 + i % 2)) % 75

        x = base_x + int(math.sin((frame_idx + i) * 0.65) * 4)
        y = base_y - float_up
        r = 5 + (i % 3) * 3
        alpha = 105 + (i % 3) * 26

        draw.ellipse(
            (x - r, y - r, x + r, y + r),
            outline=(255, 255, 255, alpha),
            width=2,
        )

    bubbles = bubbles.filter(ImageFilter.GaussianBlur(0.3))
    scene.alpha_composite(bubbles)


def add_water(scene: Image.Image, frame_idx: int):
    water = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(water)

    # body zhruba pod spodkem hlavice
    base_points = [
    (109, 96), (119, 97), (129, 98), (139, 99), (149, 100),
    (159, 100), (169, 100), (179, 100), (189, 99), (199, 98),
    (209, 97), (219, 96), (229, 95),
    ]

    for i, (start_x, start_y) in enumerate(base_points):
        phase = frame_idx * 0.85 + i * 0.55
        length = 118 + (i % 3) * 14
        spread = (i - (len(base_points) - 1) / 2.0) * 3.8
        wobble = math.sin(phase) * 3.2
        drift = math.cos(phase * 0.9) * 1.5

        end_x = start_x + spread + wobble + drift
        end_y = start_y + length

        width = 2 + (i % 2)
        alpha = 120 + (i % 4) * 18

        draw.line(
            (start_x, start_y, end_x, end_y),
            fill=(145, 208, 255, alpha),
            width=width,
        )

        # vedlejsi slabsi proud
        draw.line(
            (start_x + 1, start_y, end_x + 2, end_y - 8),
            fill=(190, 232, 255, max(75, alpha - 38)),
            width=1,
        )

        # kapka uprostred proudu
        mid_x = start_x + (end_x - start_x) * 0.52
        mid_y = start_y + (end_y - start_y) * 0.52
        draw.ellipse(
            (mid_x - 2, mid_y - 5, mid_x + 2, mid_y + 5),
            fill=(188, 232, 255, min(255, alpha + 18)),
        )

        # mala kapka dole
        splash_x = end_x + math.sin(frame_idx + i * 0.7) * 4
        splash_y = end_y + ((frame_idx * 2 + i) % 8)
        draw.ellipse(
            (splash_x - 2.5, splash_y - 2.5, splash_x + 2.5, splash_y + 2.5),
            fill=(198, 236, 255, 180),
        )

    water = water.filter(ImageFilter.GaussianBlur(0.35))
    scene.alpha_composite(water)


def build_frame(avatar: Image.Image, frame_idx: int) -> Image.Image:
    scene = create_background()
    draw = ImageDraw.Draw(scene)

    draw_shower_hardware(draw)

    avatar_x = 115
    avatar_y = 165
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
