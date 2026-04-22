from io import BytesIO

import discord
from discord.ext import commands
from discord import app_commands, Interaction
from PIL import Image


BASE_URL = "https://gr3i.github.io/room"

FLOOR_IMAGE_PATHS = {
    1: "assets/room_maps/patro1.png",
    2: "assets/room_maps/patro2.png",
    3: "assets/room_maps/patro3.png",
}

ARROW_IMAGE_PATH = "assets/room_maps/arrow.png"

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


def build_room_preview(room_code: str) -> BytesIO:
    room_data = ROOMS[room_code]
    floor_number = room_data["floor"]

    base_floor_image = Image.open(FLOOR_IMAGE_PATHS[floor_number]).convert("RGBA")
    arrow_image = Image.open(ARROW_IMAGE_PATH).convert("RGBA")

    floor_image_width, floor_image_height = base_floor_image.size

    marker_center_x = int((room_data["x"] / 100) * floor_image_width)
    marker_center_y = int(((100 - room_data["y"]) / 100) * floor_image_height)

    arrow_target_width = max(36, floor_image_width // 18)
    arrow_aspect_ratio = arrow_image.height / arrow_image.width
    arrow_target_height = int(arrow_target_width * arrow_aspect_ratio)

    resized_arrow_image = arrow_image.resize(
        (arrow_target_width, arrow_target_height),
        Image.LANCZOS,
    )

    paste_x = marker_center_x - resized_arrow_image.width // 2
    paste_y = marker_center_y - resized_arrow_image.height // 2

    composed_preview = base_floor_image.copy()
    composed_preview.paste(
        resized_arrow_image,
        (paste_x, paste_y),
        resized_arrow_image,
    )

    output_buffer = BytesIO()
    composed_preview.save(output_buffer, format="PNG")
    output_buffer.seek(0)
    return output_buffer


class Room(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="room",
        description="Ukaze mistnost na mape.",
    )
    @app_commands.describe(
        code="Zadej zkratku mistnosti, napr. P384 nebo P287",
    )
    async def room(self, interaction: Interaction, code: str):
        room_code = code.strip().lower()

        if room_code not in ROOMS:
            await interaction.response.send_message(
                f'Mistnost **{room_code.upper()}** nemam v seznamu. '
                "Zkontroluj prosim zapis.",
                ephemeral=True,
            )
            return

        room_url = f"{BASE_URL}?room={room_code}"
        preview_image_buffer = build_room_preview(room_code)

        preview_discord_file = discord.File(
            fp=preview_image_buffer,
            filename=f"room_{room_code}.png",
        )

        room_data = ROOMS[room_code]

        embed = discord.Embed(
            title=f"Mistnost: {room_code.upper()}",
            description=f"[Odkaz na planek]({room_url})",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Patro", value=str(room_data["floor"]), inline=True)
        embed.set_image(url=f"attachment://room_{room_code}.png")

        await interaction.response.send_message(
            embed=embed,
            file=preview_discord_file,
            ephemeral=False,
        )


async def setup(bot):
    await bot.add_cog(Room(bot))
