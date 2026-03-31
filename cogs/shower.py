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
    line = (20, 20, 20, 255)
    fill = (245, 245, 245, 255)

    # svisla leva trubka
    draw.rounded_rectangle((145, 70, 161, 210), radius=8, fill=fill, outline=line, width=4)

    # horni vodorovna cast
    draw.rounded_rectangle((152, 70, 300, 86), radius=8, fill=fill, outline=line, width=4)

    # kratka sikma spojka
    draw.polygon(
        [(292, 70), (312, 70), (302, 96), (282, 96)],
        fill=fill,
        outline=line,
    )

    # kratky krk k hlavici
    draw.rounded_rectangle((286, 92, 320, 106), radius=6, fill=fill, outline=line, width=4)

    # hlavice sprchy
    draw.polygon(
        [(250, 125), (275, 102), (345, 102), (370, 125), (356, 138), (264, 138)],
        fill=fill,
        outline=line,
    )

    # spodni hrana hlavice
    draw.line((264, 138, 356, 138), fill=line, width=4)

    # kolecko/ventil vlevo
    draw.rounded_rectangle((130, 185, 172, 225), radius=8, fill=fill, outline=line, width=4)

    cx, cy = 151, 205
    r = 10
    for angle in [0, 45, 90, 135]:
        dx = int(math.cos(math.radians(angle)) * r)
        dy = int(math.sin(math.radians(angle)) * r)
        draw.line((cx - dx, cy - dy, cx + dx, cy + dy), fill=line, width=3)

    draw.ellipse((145, 199, 157, 211), outline=line, width=3)

    # spodni zahnuty konec trubky
    draw.arc((120, 210, 160, 250), start=90, end=180, fill=line, width=4)
    draw.line((120, 230, 120, 255), fill=line, width=4)
    draw.arc((108, 245, 132, 269), start=90, end=270, fill=line, width=4)


def add_shadow(scene: Image.Image, avatar_box: tuple[int, int, int, int]):
    return


def add_bubbles(scene: Image.Image, frame_idx: int):
    bubbles = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(bubbles)
    rng = random.Random(1337)

    for i in range(6):
        base_x = 175 + i * 28 + rng.randint(-6, 6)
        base_y = 345 + (i * 14) % 65
        float_up = (frame_idx * (3 + i % 2)) % 65

        x = base_x + int(math.sin((frame_idx + i) * 0.6) * 4)
        y = base_y - float_up
        r = 7 + (i % 2) * 3

        draw.ellipse(
            (x - r, y - r, x + r, y + r),
            outline=(255, 255, 255, 150),
            width=2,
        )

    scene.alpha_composite(bubbles)


def add_water(scene: Image.Image, frame_idx: int):
    water = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(water)

    base_lines = [
        ((270, 142), (262, 170)),
        ((284, 142), (278, 178)),
        ((298, 142), (296, 186)),
        ((312, 142), (314, 180)),
        ((326, 142), (332, 172)),
        ((340, 142), (350, 166)),
    ]

    for i, ((x1, y1), (x2, y2)) in enumerate(base_lines):
        phase = frame_idx * 0.8 + i * 0.6
        sway = math.sin(phase) * 3
        extra = int((math.cos(phase) + 1) * 4)

        draw.line(
            (x1, y1, x2 + sway, y2 + extra),
            fill=(120, 200, 255, 210),
            width=3,
        )

    # druha rada slabsich proudu
    extra_lines = [
        ((276, 146), (270, 162)),
        ((292, 146), (289, 167)),
        ((306, 146), (306, 171)),
        ((320, 146), (323, 168)),
        ((334, 146), (340, 161)),
    ]

    for i, ((x1, y1), (x2, y2)) in enumerate(extra_lines):
        phase = frame_idx * 0.9 + i * 0.5
        sway = math.sin(phase) * 2
        extra = int((math.cos(phase) + 1) * 3)

        draw.line(
            (x1, y1, x2 + sway, y2 + extra),
            fill=(170, 225, 255, 170),
            width=2,
        )

    scene.alpha_composite(water)


def build_frame(avatar: Image.Image, frame_idx: int) -> Image.Image:
    scene = create_background()
    draw = ImageDraw.Draw(scene)

    draw_shower_hardware(draw)

    avatar_x = (CANVAS_W - AVATAR_SIZE) // 2
    avatar_y = 210
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
