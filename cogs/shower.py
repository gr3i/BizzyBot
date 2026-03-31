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

    points = [
        (175, 330, 9),
        (290, 346, 7),
        (205, 372, 6),
    ]

    for i, (x, y, r) in enumerate(points):
        yy = y - ((frame_idx * (2 + i)) % 18)
        xx = x + int(math.sin(frame_idx * 0.5 + i) * 2)

        draw.ellipse(
            (xx - r, yy - r, xx + r, yy + r),
            outline=(255, 255, 255, 120),
            width=2,
        )

    scene.alpha_composite(bubbles)


def add_water(scene: Image.Image, frame_idx: int):
    water = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(water)

    xs = [150, 164, 178, 192, 206, 220, 234, 248, 262]
    lengths = [122, 138, 130, 145, 156, 143, 132, 140, 124]

    for i, x in enumerate(xs):
        phase = frame_idx * 0.75 + i * 0.45
        sway = math.sin(phase) * 2.2
        extra = math.cos(phase * 0.9) * 4

        y1 = 127
        y2 = y1 + lengths[i] + extra

        draw.line(
            (x, y1, x + sway, y2),
            fill=(120, 200, 255, 190),
            width=2,
        )

    # jemna druha vrstva mezi proudy
    xs2 = [157, 171, 185, 199, 213, 227, 241, 255]
    lengths2 = [110, 126, 121, 135, 146, 132, 124, 116]

    for i, x in enumerate(xs2):
        phase = frame_idx * 0.95 + i * 0.38
        sway = math.sin(phase) * 1.6
        extra = math.cos(phase) * 3

        y1 = 129
        y2 = y1 + lengths2[i] + extra

        draw.line(
            (x, y1, x + sway, y2),
            fill=(180, 228, 255, 120),
            width=1,
        )

    scene.alpha_composite(water)


def build_frame(avatar: Image.Image, frame_idx: int) -> Image.Image:
    scene = create_background()
    draw = ImageDraw.Draw(scene)

    draw_shower_hardware(draw)

    avatar_x = 155
    avatar_y = 195
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
