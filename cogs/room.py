from io import BytesIO
from pathlib import Path

import discord
from discord.ext import commands
from discord import app_commands, Interaction
from PIL import Image, ImageDraw, ImageFont


BASE_URL = "https://gr3i.github.io/room"

ASSETS_DIRECTORY = Path(__file__).resolve().parent.parent / "assets" / "room_maps"

FLOOR_IMAGE_PATHS = {
    1: ASSETS_DIRECTORY / "patro1.png",
    2: ASSETS_DIRECTORY / "patro2.png",
    3: ASSETS_DIRECTORY / "patro3.png",
}

ARROW_IMAGE_PATH = ASSETS_DIRECTORY / "arrow.png"

FLOOR_CONFIG = {
    1: {
        "label": "1. patro Fakulty podnikatelské",
        "footer": "Patro po vejítí ze zadu od Technologického parku.",
    },
    2: {
        "label": "2. patro Fakulty podnikatelské",
        "footer": "Patro s učebnami uprostřed budovy.",
    },
    3: {
        "label": "3. patro Fakulty podnikatelské",
        "footer": "Patro hned po vstupu z velkého parkoviště u FP.",
    },
}

ROOMS = {
    "p381": {"x": 78, "y": 86, "floor": 3},
    "p384": {"x": 91, "y": 80, "floor": 3},
    "e337": {"x": 30, "y": 86, "floor": 3},
    "e339": {"x": 20, "y": 86, "floor": 3},
    "e341": {"x": 11, "y": 86, "floor": 3},
    "e342": {"x": 3, "y": 86, "floor": 3},

    "p283": {"x": 96, "y": 1, "floor": 2},
    "p284": {"x": 83, "y": 5, "floor": 2},
    "p285": {"x": 80, "y": 5, "floor": 2},
    "p286": {"x": 77, "y": 9, "floor": 2},
    "p287": {"x": 74, "y": 5, "floor": 2},
    "p288": {"x": 70, "y": 5, "floor": 2},
    "p292": {"x": 62, "y": 11, "floor": 2},
    "p289": {"x": 62, "y": 19, "floor": 2},
    "p254": {"x": 73, "y": 39, "floor": 2},
    "p257": {"x": 79, "y": 39, "floor": 2},
    "p259": {"x": 87, "y": 38, "floor": 2},
    "p262": {"x": 84, "y": 76, "floor": 2},
    "p256": {"x": 77, "y": 51, "floor": 2},
    "p255": {"x": 71, "y": 51, "floor": 2},
    "e219": {"x": 5, "y": 67, "floor": 2},

    "e110": {"x": 9, "y": 77, "floor": 1},
    "e109": {"x": 19, "y": 77, "floor": 1},
    "e131": {"x": 12, "y": 36, "floor": 1},
    "e135": {"x": 19, "y": 36, "floor": 1},
    "p165": {"x": 73, "y": 62, "floor": 1},
    "p164": {"x": 85, "y": 62, "floor": 1},
    "p163": {"x": 91, "y": 62, "floor": 1},
    "p160": {"x": 91, "y": 19, "floor": 1},
    "p159": {"x": 84, "y": 19, "floor": 1},
    "p158": {"x": 77, "y": 19, "floor": 1},
    "p157": {"x": 70, "y": 19, "floor": 1},
}


def load_font(font_size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_candidates = []

    if bold:
        font_candidates.extend(
            [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            ]
        )
    else:
        font_candidates.extend(
            [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            ]
        )

    for font_path in font_candidates:
        try:
            return ImageFont.truetype(font_path, font_size)
        except OSError:
            continue

    return ImageFont.load_default()


def get_text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left, bottom - top


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    canvas_width: int,
    top_y: int,
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> int:
    text_width, text_height = get_text_size(draw, text, font)
    text_x = (canvas_width - text_width) // 2
    draw.text((text_x, top_y), text, font=font, fill=fill)
    return top_y + text_height


def draw_left_aligned_text(
    draw: ImageDraw.ImageDraw,
    left_x: int,
    top_y: int,
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> int:
    draw.text((left_x, top_y), text, font=font, fill=fill)
    _, text_height = get_text_size(draw, text, font)
    return top_y + text_height


def draw_code_badge(
    draw: ImageDraw.ImageDraw,
    left_x: int,
    center_y: int,
    text: str,
    font: ImageFont.ImageFont,
) -> int:
    badge_padding_x = 14
    badge_padding_y = 8

    text_width, text_height = get_text_size(draw, text, font)
    badge_width = text_width + badge_padding_x * 2
    badge_height = text_height + badge_padding_y * 2

    badge_left = left_x
    badge_top = center_y - badge_height // 2
    badge_right = badge_left + badge_width
    badge_bottom = badge_top + badge_height

    draw.rounded_rectangle(
        (badge_left, badge_top, badge_right, badge_bottom),
        radius=10,
        fill=(30, 30, 30),
    )
    draw.text(
        (badge_left + badge_padding_x, badge_top + badge_padding_y - 1),
        text,
        font=font,
        fill=(111, 231, 111),
    )

    return badge_width


def build_room_preview_image(room_code: str) -> BytesIO:
    room_data = ROOMS[room_code]
    floor_number = room_data["floor"]
    floor_config = FLOOR_CONFIG[floor_number]

    map_image = Image.open(FLOOR_IMAGE_PATHS[floor_number]).convert("RGBA")
    arrow_image = Image.open(ARROW_IMAGE_PATH).convert("RGBA")

    target_map_width = 1280
    map_scale_ratio = target_map_width / map_image.width
    target_map_height = int(map_image.height * map_scale_ratio)
    resized_map_image = map_image.resize((target_map_width, target_map_height), Image.LANCZOS)

    marker_center_x = int((room_data["x"] / 100) * target_map_width)
    marker_center_y = int(((100 - room_data["y"]) / 100) * target_map_height)

    arrow_target_width = max(56, target_map_width // 22)
    arrow_aspect_ratio = arrow_image.height / arrow_image.width
    arrow_target_height = int(arrow_target_width * arrow_aspect_ratio)
    resized_arrow_image = arrow_image.resize(
        (arrow_target_width, arrow_target_height),
        Image.LANCZOS,
    )

    arrow_paste_x = marker_center_x - resized_arrow_image.width // 2
    arrow_paste_y = marker_center_y - resized_arrow_image.height // 2

    composed_map_image = resized_map_image.copy()
    composed_map_image.paste(
        resized_arrow_image,
        (arrow_paste_x, arrow_paste_y),
        resized_arrow_image,
    )

    canvas_width = 1536
    canvas_height = 1152
    canvas_image = Image.new("RGB", (canvas_width, canvas_height), (15, 15, 15))
    draw = ImageDraw.Draw(canvas_image)

    title_font = load_font(56, bold=True)
    subtitle_font = load_font(28, bold=False)
    info_font = load_font(24, bold=True)
    badge_font = load_font(24, bold=False)
    footer_font = load_font(22, bold=False)

    current_y = 56
    current_y = draw_centered_text(
        draw=draw,
        canvas_width=canvas_width,
        top_y=current_y,
        text="Mapa místností",
        font=title_font,
        fill=(245, 245, 245),
    )

    current_y += 28
    current_y = draw_centered_text(
        draw=draw,
        canvas_width=canvas_width,
        top_y=current_y,
        text=floor_config["label"],
        font=subtitle_font,
        fill=(180, 180, 180),
    )

    panel_margin_x = 90
    panel_top_y = current_y + 48
    panel_width = canvas_width - panel_margin_x * 2
    panel_height = canvas_height - panel_top_y - 44
    panel_left = panel_margin_x
    panel_top = panel_top_y
    panel_right = panel_left + panel_width
    panel_bottom = panel_top + panel_height

    draw.rounded_rectangle(
        (panel_left, panel_top, panel_right, panel_bottom),
        radius=22,
        fill=(18, 18, 18),
    )

    inner_padding_x = 28
    inner_padding_top = 24

    map_left = panel_left + inner_padding_x
    map_top = panel_top + inner_padding_top
    map_right = map_left + composed_map_image.width
    map_bottom = map_top + composed_map_image.height

    map_mask = Image.new("L", composed_map_image.size, 0)
    map_mask_draw = ImageDraw.Draw(map_mask)
    map_mask_draw.rounded_rectangle(
        (0, 0, composed_map_image.width, composed_map_image.height),
        radius=16,
        fill=255,
    )

    canvas_image.paste(composed_map_image.convert("RGB"), (map_left, map_top), map_mask)

    info_text_top = map_bottom + 28
    info_left = map_left

    info_prefix = "Zobrazuji místnost "
    info_suffix = f" (patro {floor_number})."

    prefix_width, prefix_height = get_text_size(draw, info_prefix, info_font)

    draw.text(
        (info_left, info_text_top),
        info_prefix,
        font=info_font,
        fill=(111, 231, 111),
    )

    badge_center_y = info_text_top + prefix_height // 2
    badge_left = info_left + prefix_width + 10
    badge_width = draw_code_badge(
        draw=draw,
        left_x=badge_left,
        center_y=badge_center_y,
        text=room_code.upper(),
        font=badge_font,
    )

    suffix_left = badge_left + badge_width + 10
    draw.text(
        (suffix_left, info_text_top),
        info_suffix,
        font=info_font,
        fill=(111, 231, 111),
    )

    footer_text_width, footer_text_height = get_text_size(draw, floor_config["footer"], footer_font)
    footer_x = (canvas_width - footer_text_width) // 2
    footer_y = panel_bottom - footer_text_height - 26

    draw.text(
        (footer_x, footer_y),
        floor_config["footer"],
        font=footer_font,
        fill=(135, 135, 135),
    )

    output_buffer = BytesIO()
    canvas_image.save(output_buffer, format="PNG")
    output_buffer.seek(0)
    return output_buffer


class Room(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="room",
        description="Ukáže místnost na mapě.",
    )
    @app_commands.describe(
        code="Zadej zkratku místnosti, např. P384 nebo P287",
    )
    async def room(self, interaction: Interaction, code: str):
        room_code = code.strip().lower()

        if room_code not in ROOMS:
            await interaction.response.send_message(
                f"Místnost **{room_code.upper()}** nemám v seznamu. "
                "Zkontroluj prosím, jestli jsi ji napsal správně.",
                ephemeral=True,
            )
            return

        room_url = f"{BASE_URL}?room={room_code}"
        preview_image_buffer = build_room_preview_image(room_code)
        preview_filename = f"room_{room_code}.png"

        preview_discord_file = discord.File(
            fp=preview_image_buffer,
            filename=preview_filename,
        )

        floor_number = ROOMS[room_code]["floor"]
        floor_footer = FLOOR_CONFIG[floor_number]["footer"]

        embed = discord.Embed(
            title=f"Místnost: {room_code.upper()}",
            description=f"[Otevřít plánek na webu]({room_url})",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Patro", value=str(floor_number), inline=True)
        embed.add_field(name="Popis", value=floor_footer, inline=False)
        embed.set_image(url=f"attachment://{preview_filename}")

        await interaction.response.send_message(
            embed=embed,
            file=preview_discord_file,
            ephemeral=False,
        )


async def setup(bot):
    await bot.add_cog(Room(bot))
