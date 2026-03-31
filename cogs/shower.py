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
    draw.rounded_rectangle((210, 22, 412, 40), radius=10, fill=fill, outline=line, width=3)

    # 2) prava svisla trubka dolu
    draw.rounded_rectangle((396, 40, 414, 100), radius=10, fill=fill, outline=line, width=3)

    # 3) kratka leva spojka do hlavice
    draw.rounded_rectangle((204, 38, 248, 54), radius=16, fill=fill, outline=line, width=3)

    # hlavice - vrsek
    draw.ellipse((138, 52, 306, 80), fill=fill, outline=line, width=3)

    # hlavice - spodek
    draw.ellipse((112, 66, 332, 122), fill=fill, outline=line, width=3)

    # vnitrni linka na hlavici
    draw.arc((124, 72, 310, 112), start=198, end=342, fill=line, width=2)

    # trysky
    for x in [144, 158, 172, 186, 200, 214, 228, 242, 256, 270, 284]:
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
        (148, 98), (162, 98), (176, 98), (190, 98), (204, 98),
        (218, 98), (232, 98), (246, 98), (260, 98), (274, 98), (288, 98),
    ]

    flow_top = 98
    flow_bottom = 255
    cycle = 36
    offset = (frame_idx * 10) % cycle

    # globalni pohyb sprchy do stran
    sweep = math.sin(frame_idx * 0.25 - 1.0) * 12

    # lehke "otaceni" kolem stredu hlavice
    center_x = sum(x for x, _ in nozzle_points) / len(nozzle_points)

    for i, (start_x, start_y) in enumerate(nozzle_points):
        phase = frame_idx * 0.55 + i * 0.45

        # jak dal je tryska od stredu hlavice
        rel = (start_x - center_x) / 70.0

        # horni bod se lehce pohybuje do stran
        origin_x = start_x + sweep * 0.35

        # dole se proud rozhodi vic, aby to pusobilo jako kyvani sprchy
        side_bias = sweep * (1.0 + abs(rel) * 0.35)

        # kazdy proud ma lehce jine vlnění
        sway = math.sin(phase) * 2.2
        twist = math.cos(frame_idx * 0.35 + rel * 2.4) * 3.0

        # jemny podkladovy proud
        draw.line(
            (origin_x, flow_top, origin_x + side_bias * 0.55 + sway, flow_bottom),
            fill=(150, 212, 255, 65),
            width=1,
        )

        # segmenty, ktere se hybou dolu
        seg_len = 16 + (i % 3) * 2
        gap = 14 + (i % 2) * 2

        y = flow_top - cycle + offset + (i * 2)
        while y < flow_bottom:
            y1 = max(flow_top, y)
            y2 = min(flow_bottom, y + seg_len)

            if y2 > flow_top:
                # cim niz je voda, tim vic se vychyli do strany
                fall_ratio_1 = (y1 - flow_top) / max(flow_bottom - flow_top, 1)
                fall_ratio_2 = (y2 - flow_top) / max(flow_bottom - flow_top, 1)

                x1 = origin_x + side_bias * fall_ratio_1 * 0.75 + math.sin((y1 * 0.05) + phase) * 1.6
                x2 = origin_x + side_bias * fall_ratio_2 + math.sin((y2 * 0.05) + phase) * 2.1 + sway + twist

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

        # kapka nekde v proudu
        droplet_y = flow_top + ((frame_idx * 9 + i * 13) % (flow_bottom - flow_top))
        droplet_ratio = (droplet_y - flow_top) / max(flow_bottom - flow_top, 1)
        droplet_x = origin_x + side_bias * droplet_ratio + math.sin(phase + droplet_y * 0.04) * 2.5

        draw.ellipse(
            (droplet_x - 2, droplet_y - 4, droplet_x + 2, droplet_y + 4),
            fill=(195, 235, 255, 185),
        )

        # splash dole
        splash_x = origin_x + side_bias + math.sin(frame_idx + i) * 3
        splash_y = flow_bottom + ((frame_idx * 3 + i) % 10)

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
