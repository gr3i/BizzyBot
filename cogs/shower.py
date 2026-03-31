import io
import math

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFilter, ImageOps


SINGLE_CANVAS_W = 520
COMBO_CANVAS_W = 720
CANVAS_H = 520
SINGLE_AVATAR_SIZE = 205
COMBO_AVATAR_SIZE = 170
FRAME_COUNT = 12
FRAME_DURATION_MS = 50


ALLOWED_USER_IDS = {
    685958402442133515
}

ALLOWED_ROLE_IDS = {
    1358898283782602932, 1358911329737642014, 1466036385017233636, 1358905374500982995
}


def user_is_allowed(interaction: discord.Interaction) -> bool:
    if interaction.user.id in ALLOWED_USER_IDS:
        return True

    member = interaction.user if isinstance(interaction.user, discord.Member) else None
    if member is not None:
        return any(role.id in ALLOWED_ROLE_IDS for role in member.roles)

    return False


def crop_avatar_circle(raw_bytes: bytes, size: int) -> Image.Image:
    avatar = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
    avatar = ImageOps.fit(avatar, (size, size), method=Image.Resampling.LANCZOS)

    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size - 1, size - 1), fill=255)
    avatar.putalpha(mask)

    return avatar


def create_background(width: int) -> Image.Image:
    return Image.new("RGBA", (width, CANVAS_H), (0, 0, 0, 0))


def draw_single_shower_hardware(draw: ImageDraw.ImageDraw):
    line = (25, 25, 25, 255)
    fill = (245, 245, 245, 255)

    draw.rounded_rectangle((210, 22, 412, 40), radius=10, fill=fill, outline=line, width=3)
    draw.rounded_rectangle((396, 40, 414, 100), radius=10, fill=fill, outline=line, width=3)
    draw.rounded_rectangle((204, 38, 248, 54), radius=16, fill=fill, outline=line, width=3)
    draw.ellipse((138, 52, 306, 80), fill=fill, outline=line, width=3)
    draw.ellipse((112, 66, 332, 122), fill=fill, outline=line, width=3)
    draw.arc((124, 72, 310, 112), start=198, end=342, fill=line, width=2)

    nozzle_points = []
    for x in [144, 158, 172, 186, 200, 214, 228, 242, 256, 270, 284]:
        draw.ellipse((x, 94, x + 3, 98), fill=line)
        nozzle_points.append((x + 1, 98))

    return nozzle_points


def draw_combo_shower_hardware(draw: ImageDraw.ImageDraw, avatar_centers: list[int]):
    line = (25, 25, 25, 255)
    fill = (245, 245, 245, 255)

    left = min(avatar_centers) - 70
    right = max(avatar_centers) + 70
    head_left = left - 20
    head_right = right + 20

    head_center_x = (head_left + head_right) // 2

    # jen jedna svisla trubka nad hlavici
    pipe_w = 28
    pipe_h = 42
    pipe_x1 = head_center_x - pipe_w // 2
    pipe_x2 = head_center_x + pipe_w // 2
    pipe_y1 = 18
    pipe_y2 = 60

    draw.rounded_rectangle(
        (pipe_x1, pipe_y1, pipe_x2, pipe_y2),
        radius=10,
        fill=fill,
        outline=line,
        width=3,
    )

    # hlavice - vrsek
    draw.ellipse((head_left + 46, 52, head_right - 46, 80), fill=fill, outline=line, width=3)

    # hlavice - spodek
    draw.ellipse((head_left, 66, head_right, 122), fill=fill, outline=line, width=3)

    # vnitrni linka
    draw.arc((head_left + 12, 72, head_right - 22, 112), start=198, end=342, fill=line, width=2)

    # trysky po cele sirce
    nozzle_start = head_left + 32
    nozzle_end = head_right - 32
    count = max(11, int((nozzle_end - nozzle_start) / 16))
    step = (nozzle_end - nozzle_start) / max(count - 1, 1)

    nozzle_points = []
    for i in range(count):
        x = int(nozzle_start + i * step)
        draw.ellipse((x, 94, x + 3, 98), fill=line)
        nozzle_points.append((x + 1, 98))

    return nozzle_points


def add_shadow(scene: Image.Image, avatar_box: tuple[int, int, int, int]):
    return


def add_single_bubbles(scene: Image.Image, frame_idx: int):
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


def add_combo_bubbles(scene: Image.Image, frame_idx: int, avatar_boxes: list[tuple[int, int, int, int]]):
    bubbles = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(bubbles)

    for idx, (x0, y0, x1, y1) in enumerate(avatar_boxes):
        cx = (x0 + x1) // 2
        base_points = [
            (cx - 42, y1 - 30, 7),
            (cx - 18, y1 - 8, 9),
            (cx + 12, y1 + 8, 6),
            (cx + 36, y1 - 18, 8),
        ]

        for i, (bx, by, r) in enumerate(base_points):
            lift = ((frame_idx * (3 + i % 2)) + i * 5 + idx * 4) % 34
            x = bx + int(math.sin(frame_idx * 0.35 + i + idx) * 2)
            y = by - lift

            draw.ellipse(
                (x - r, y - r, x + r, y + r),
                outline=(255, 255, 255, 125),
                width=2,
            )

    bubbles = bubbles.filter(ImageFilter.GaussianBlur(0.2))
    scene.alpha_composite(bubbles)


def add_water(scene: Image.Image, frame_idx: int, nozzle_points: list[tuple[int, int]], flow_bottom: int):
    water = Image.new("RGBA", scene.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(water)

    flow_top = 98
    cycle = 36
    offset = (frame_idx * 6) % cycle

    sweep = math.sin(frame_idx * 0.08 - 1.1) * 6
    center_x = sum(x for x, _ in nozzle_points) / len(nozzle_points)

    for i, (start_x, start_y) in enumerate(nozzle_points):
        phase = frame_idx * 0.20 + i * 0.32
        rel = (start_x - center_x) / max(len(nozzle_points) * 6, 1)

        origin_x = start_x + sweep * 0.35
        side_bias = sweep * (0.45 + abs(rel) * 0.10)
        sway = math.sin(phase) * 0.6
        twist = math.cos(frame_idx * 0.10 + rel * 1.6) * 0.6

        draw.line(
            (origin_x, flow_top, origin_x + side_bias * 0.55 + sway, flow_bottom),
            fill=(150, 212, 255, 65),
            width=1,
        )

        seg_len = 16 + (i % 3) * 2
        gap = 14 + (i % 2) * 2

        y = flow_top - cycle + offset + (i * 2)
        while y < flow_bottom:
            y1 = max(flow_top, y)
            y2 = min(flow_bottom, y + seg_len)

            if y2 > flow_top:
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

        droplet_y = flow_top + ((frame_idx * 9 + i * 13) % max(flow_bottom - flow_top, 1))
        droplet_ratio = (droplet_y - flow_top) / max(flow_bottom - flow_top, 1)
        droplet_x = origin_x + side_bias * droplet_ratio + math.sin(phase + droplet_y * 0.04) * 2.5

        draw.ellipse(
            (droplet_x - 2, droplet_y - 4, droplet_x + 2, droplet_y + 4),
            fill=(195, 235, 255, 185),
        )

        splash_x = origin_x + side_bias + math.sin(frame_idx + i) * 3
        splash_y = flow_bottom + ((frame_idx * 3 + i) % 10)

        draw.ellipse(
            (splash_x - 2.5, splash_y - 2.5, splash_x + 2.5, splash_y + 2.5),
            fill=(198, 236, 255, 175),
        )

    water = water.filter(ImageFilter.GaussianBlur(0.2))
    scene.alpha_composite(water)


def get_combo_avatar_layout(count: int) -> list[tuple[int, int]]:
    y = 185

    if count == 2:
        return [(170, y), (375, y)]
    if count == 3:
        return [(95, y), (275, y), (455, y)]
    return [(45, y), (205, y), (365, y), (525, y)]


def build_single_frame(avatar: Image.Image, frame_idx: int) -> Image.Image:
    scene = create_background(SINGLE_CANVAS_W)
    draw = ImageDraw.Draw(scene)

    nozzle_points = draw_single_shower_hardware(draw)

    avatar_x = 110
    avatar_y = 150
    avatar_box = (avatar_x, avatar_y, avatar_x + SINGLE_AVATAR_SIZE, avatar_y + SINGLE_AVATAR_SIZE)

    add_shadow(scene, avatar_box)
    scene.alpha_composite(avatar, (avatar_x, avatar_y))
    add_water(scene, frame_idx, nozzle_points, 235)
    add_single_bubbles(scene, frame_idx)

    return scene


def build_combo_frame(avatars: list[Image.Image], frame_idx: int) -> Image.Image:
    scene = create_background(COMBO_CANVAS_W)
    draw = ImageDraw.Draw(scene)

    positions = get_combo_avatar_layout(len(avatars))
    avatar_boxes = []
    avatar_centers = [x + COMBO_AVATAR_SIZE // 2 for x, _ in positions]
    nozzle_points = draw_combo_shower_hardware(draw, avatar_centers)

    for avatar, (avatar_x, avatar_y) in zip(avatars, positions):
        avatar_box = (avatar_x, avatar_y, avatar_x + COMBO_AVATAR_SIZE, avatar_y + COMBO_AVATAR_SIZE)
        avatar_boxes.append(avatar_box)
        add_shadow(scene, avatar_box)
        scene.alpha_composite(avatar, (avatar_x, avatar_y))

    flow_bottom = min(y for _, y in positions) + int(COMBO_AVATAR_SIZE * 0.72)

    add_water(scene, frame_idx, nozzle_points, flow_bottom)
    add_combo_bubbles(scene, frame_idx, avatar_boxes)

    return scene


def rgba_frames_to_gif_bytes(rgba_frames: list[Image.Image]) -> io.BytesIO:
    gif_frames = []
    transparent_index = 0

    for frame in rgba_frames:
        rgba = frame.convert("RGBA")

        alpha = rgba.getchannel("A")
        opaque = Image.new("RGBA", rgba.size, (255, 255, 255, 0))
        opaque.paste(rgba, mask=alpha)

        quant = opaque.convert("RGB").convert("P", palette=Image.Palette.ADAPTIVE, colors=255)

        out = Image.new("P", rgba.size, transparent_index)
        palette = quant.getpalette()
        if len(palette) < 256 * 3:
            palette += [0] * (256 * 3 - len(palette))
        out.putpalette(palette[:256 * 3])

        mask = alpha.point(lambda a: 255 if a > 0 else 0)
        out.paste(quant, mask=mask)

        out.info["transparency"] = transparent_index
        out.info["disposal"] = 2
        gif_frames.append(out)

    output = io.BytesIO()
    gif_frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=gif_frames[1:],
        duration=FRAME_DURATION_MS,
        loop=0,
        transparency=transparent_index,
        disposal=2,
        optimize=False,
    )
    output.seek(0)
    return output


def build_shower_gif(raw_bytes: bytes) -> io.BytesIO:
    avatar = crop_avatar_circle(raw_bytes, SINGLE_AVATAR_SIZE)
    frames = [build_single_frame(avatar, idx) for idx in range(FRAME_COUNT)]
    return rgba_frames_to_gif_bytes(frames)


def build_shower_combo_gif(raw_avatar_bytes_list: list[bytes]) -> io.BytesIO:
    avatars = [crop_avatar_circle(raw, COMBO_AVATAR_SIZE) for raw in raw_avatar_bytes_list]
    frames = [build_combo_frame(avatars, idx) for idx in range(FRAME_COUNT)]
    return rgba_frames_to_gif_bytes(frames)


class Shower(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="sprcha",
        description="Udělá shower gif z profilovky vybraného uživatele."
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
                f"Nepodařilo se připravit shower gif: {error}",
                ephemeral=True,
            )
            return

        file = discord.File(fp=gif_buffer, filename="sprcha.gif")
        await interaction.followup.send(file=file)

    @app_commands.command(
        name="sprchacombo",
        description="Udělá shower combo gif pro více uživatelů."
    )
    @app_commands.guild_only()
    async def sprchacombo(
        self,
        interaction: discord.Interaction,
        uzivatel1: discord.Member,
        uzivatel2: discord.Member,
        uzivatel3: discord.Member | None = None,
        uzivatel4: discord.Member | None = None,
    ):
        await interaction.response.defer()

        try:
            members = [uzivatel1, uzivatel2]
            if uzivatel3 is not None:
                members.append(uzivatel3)
            if uzivatel4 is not None:
                members.append(uzivatel4)

            raw_avatar_bytes_list = []
            for member in members:
                avatar_asset = member.display_avatar.replace(format="png", size=512)
                raw_avatar_bytes_list.append(await avatar_asset.read())

            gif_buffer = build_shower_combo_gif(raw_avatar_bytes_list)
        except Exception as error:
            await interaction.followup.send(
                f"Nepodařilo se připravit shower combo gif: {error}",
                ephemeral=True,
            )
            return

        file = discord.File(fp=gif_buffer, filename="sprchacombo.gif")
        await interaction.followup.send(file=file)


async def setup(bot: commands.Bot):
    await bot.add_cog(Shower(bot)) 
