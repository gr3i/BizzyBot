from io import BytesIO
from pathlib import Path

import discord
from discord import Interaction, app_commands
from discord.ext import commands
from PIL import Image


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
        "description": "Patro po vejítí zezadu od Technologického parku.",
    },
    2: {
        "label": "2. patro Fakulty podnikatelské",
        "description": "Patro s učebnami uprostřed budovy.",
    },
    3: {
        "label": "3. patro Fakulty podnikatelské",
        "description": "Patro hned po vstupu z velkého parkoviště u FP.",
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


def build_room_preview_image(room_code: str) -> BytesIO:
    room_data = ROOMS[room_code]
    floor_number = room_data["floor"]

    map_image = Image.open(FLOOR_IMAGE_PATHS[floor_number]).convert("RGBA")
    arrow_image = Image.open(ARROW_IMAGE_PATH).convert("RGBA")

    target_map_width = 1400
    map_scale_ratio = target_map_width / map_image.width
    target_map_height = int(map_image.height * map_scale_ratio)

    resized_map_image = map_image.resize(
        (target_map_width, target_map_height),
        Image.LANCZOS,
    )

    marker_center_x = int((room_data["x"] / 100) * target_map_width)
    marker_center_y = int(((100 - room_data["y"]) / 100) * target_map_height)

    arrow_target_width = max(60, target_map_width // 22)
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

    output_buffer = BytesIO()
    composed_map_image.save(output_buffer, format="PNG")
    output_buffer.seek(0)
    return output_buffer


class Room(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="room",
        description="Ukáže místnost na mapě.",
    )
    @app_commands.describe(
        code="Zadej zkratku místnosti, např. P165 nebo P287",
    )
    async def room(self, interaction: Interaction, code: str):
        room_code = code.strip().lower()

        if room_code not in ROOMS:
            await interaction.response.send_message(
                f"Místnost **{room_code.upper()}** nemám v seznamu. Zkontroluj prosím zápis.",
                ephemeral=True,
            )
            return

        room_data = ROOMS[room_code]
        floor_number = room_data["floor"]
        floor_config = FLOOR_CONFIG[floor_number]

        room_url = f"{BASE_URL}?room={room_code}"
        preview_image_buffer = build_room_preview_image(room_code)
        preview_filename = f"room_{room_code}.png"

        preview_discord_file = discord.File(
            fp=preview_image_buffer,
            filename=preview_filename,
        )

        embed = discord.Embed(
            title=f"Místnost: {room_code.upper()}",
            description=f"[Odkaz na plánek]({room_url})",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Patro", value=floor_config["label"], inline=False)
        embed.add_field(name="Popis", value=floor_config["description"], inline=False)
        embed.set_image(url=f"attachment://{preview_filename}")
        embed.set_footer(text="BizzyBot • /room")

        await interaction.response.send_message(
            embed=embed,
            file=preview_discord_file,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Room(bot))
