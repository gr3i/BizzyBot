import io
import math
import random

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFilter, ImageOps


CANVAS_W = 520
CANVAS_H = 520
AVATAR_SIZE = 205
FRAME_COUNT = 12
FRAME_DURATION_MS = 50


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

    # 1) dlouha horni trubka
    draw.rounded_rectangle((190, 26, 392, 38), radius=6, fill=fill, outline=line, width=3)

    # 2) prava svisla trubka dolu
    draw.rounded_rectangle((380, 26, 392, 98), radius=6, fill=fill, outline=line, width=3)

    # 3) kratka leva spojka do hlavice
    draw.rounded_rectangle((154, 34, 198, 50), radius=7, fill=fill, outline=line, width=3)

    # hlavice - vrsek
    draw.ellipse((78, 52, 246, 80), fill=fill, outline=line, width=3)

    # hlavice - spodek
    draw.ellipse((52, 66, 272, 122), fill=fill, outline=line, width=3)

    # vnitrni linka na hlavici
    draw.arc((74, 72, 250, 112), start=198, end=342, fill=line, width=2)

    # trysky
    for x in [84, 98, 112, 126, 140, 154, 168, 182, 196, 210, 224]:
        draw.ellipse((x, 94, x + 3, 98), fill=line)


def add_shadow(scene: Image.Image, avatar_box: tuple[int, int, int, int]):
    return


def add_bubbles(scene: Image.Image, frame_idx: int):
    bubbles = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(bubbles)

    bubble_points = [
        (132, 292, 7),
        (154, 320, 9),
        (188, 338, 6),
        (230, 346, 8),
        (256, 318, 7),
        (214, 362, 10),
    ]

    for i, (bx, by, r) in enumerate(bubble_points):
        lift = ((frame_idx * (3 + i % 2)) + i * 5) % 36
        x = bx + int(math.sin(frame_idx * 0.45 + i) * 3)
        y = by - lift

        draw.ellipse(
            (x - r, y - r, x + r, y + r),
            outline=(255, 255, 255, 135),
            width=2,
        )

    bubbles = bubbles.filter(ImageFilter.GaussianBlur(0.25))
    scene.alpha_composite(bubbles)


def add_water(scene: Image.Image, frame_idx: int):
    water = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(water)

    nozzle_points = [
    (86, 98), (100, 98), (114, 98), (128, 98), (142, 98),
    (156, 98), (170, 98), (184, 98), (198, 98), (212, 98), (226, 98),
    ]

    flow_top = 98
    flow_bottom = 250
    cycle = 36
    offset = (frame_idx * 10) % cycle

    for i, (start_x, start_y) in enumerate(nozzle_points):
        phase = frame_idx * 0.55 + i * 0.45
        spread = (i - (len(nozzle_points) - 1) / 2.0) * 2.8
        sway = math.sin(phase) * 2.2

        x = start_x + spread * 0.15

        # jemny hlavni proud jako podklad
        draw.line(
            (x, flow_top, x + sway, flow_bottom),
            fill=(150, 212, 255, 70),
            width=1,
        )

        # animovane segmenty, ktere vytvari dojem teceni dolu
        seg_len = 16 + (i % 3) * 2
        gap = 14 + (i % 2) * 2

        y = flow_top - cycle + offset + (i * 2)
        while y < flow_bottom:
            y1 = max(flow_top, y)
            y2 = min(flow_bottom, y + seg_len)

            if y2 > flow_top:
                x1 = x + math.sin((y1 * 0.05) + phase) * 1.8
                x2 = x + math.sin((y2 * 0.05) + phase) * 2.4 + sway

                draw.line(
                    (x1, y1, x2, y2),
                    fill=(145, 208, 255, 220),
                    width=2,
                )

                draw.line(
                    (x1 + 1, y1, x2 + 2, y2 - 2),
                    fill=(205, 238, 255, 120),
                    width=1,
                )

            y += seg_len + gap

        # mala kapka nekde v proudu
        droplet_y = flow_top + ((frame_idx * 9 + i * 13) % (flow_bottom - flow_top))
        droplet_x = x + math.sin(phase + droplet_y * 0.04) * 2.5
        draw.ellipse(
            (droplet_x - 2, droplet_y - 4, droplet_x + 2, droplet_y + 4),
            fill=(195, 235, 255, 185),
        )

        # splash dole
        splash_y = flow_bottom + ((frame_idx * 3 + i) % 10)
        splash_x = x + sway * 1.3 + math.sin(frame_idx + i) * 3
        draw.ellipse(
            (splash_x - 2.5, splash_y - 2.5, splash_x + 2.5, splash_y + 2.5),
            fill=(198, 236, 255, 175),
        )

    water = water.filter(ImageFilter.GaussianBlur(0.2))
    scene.alpha_composite(water)


def build_frame(avatar: Image.Image, frame_idx: int) -> Image.Image:
    scene = create_background()
    draw = ImageDraw.Draw(scene)

    draw_shower_hardware(draw)

    avatar_x = 110
    avatar_y = 150
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
