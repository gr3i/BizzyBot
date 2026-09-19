from pathlib import Path
import tkinter as tk

from PIL import Image, ImageTk


ROOT_DIR = Path(__file__).resolve().parent.parent

ASSETS_DIRECTORY = ROOT_DIR / "assets" / "room_maps"

FLOOR_IMAGE_PATHS = {
    1: ASSETS_DIRECTORY / "patro1.png",
    2: ASSETS_DIRECTORY / "patro2.png",
    3: ASSETS_DIRECTORY / "patro3.png",
}

ARROW_IMAGE_PATH = ASSETS_DIRECTORY / "arrow.png"


FLOOR = 1

START_X = 78
START_Y = 86


class RoomMapTuner:
    def __init__(self, root):
        self.root = root

        self.x = START_X
        self.y = START_Y

        self.original_map = Image.open(
            FLOOR_IMAGE_PATHS[FLOOR]
        ).convert("RGBA")

        self.original_arrow = Image.open(
            ARROW_IMAGE_PATH
        ).convert("RGBA")

        self.target_width = 1280

        scale_ratio = (
            self.target_width / self.original_map.width
        )

        self.target_height = int(
            self.original_map.height * scale_ratio
        )

        self.map_image = self.original_map.resize(
            (
                self.target_width,
                self.target_height,
            ),
            Image.LANCZOS,
        )

        arrow_width = max(
            56,
            self.target_width // 22,
        )

        arrow_ratio = (
            self.original_arrow.height
            / self.original_arrow.width
        )

        arrow_height = int(
            arrow_width * arrow_ratio
        )

        self.arrow_image = self.original_arrow.resize(
            (
                arrow_width,
                arrow_height,
            ),
            Image.LANCZOS,
        )

        self.canvas = tk.Canvas(
            root,
            width=self.target_width,
            height=self.target_height,
        )

        self.canvas.pack()

        self.info_label = tk.Label(
            root,
            font=("Arial", 14),
        )

        self.info_label.pack()

        self.canvas.bind(
            "<Button-1>",
            self.on_click,
        )

        root.bind(
            "<Left>",
            lambda event: self.move(-1, 0),
        )

        root.bind(
            "<Right>",
            lambda event: self.move(1, 0),
        )

        root.bind(
            "<Up>",
            lambda event: self.move(0, 1),
        )

        root.bind(
            "<Down>",
            lambda event: self.move(0, -1),
        )

        root.bind(
            "s",
            self.save_preview,
        )

        self.update_preview()

    def move(self, dx, dy):
        self.x = max(
            0,
            min(100, self.x + dx),
        )

        self.y = max(
            0,
            min(100, self.y + dy),
        )

        self.update_preview()

    def on_click(self, event):
        self.x = round(
            event.x
            / self.target_width
            * 100
        )

        self.y = round(
            (
                1
                - event.y
                / self.target_height
            )
            * 100
        )

        self.update_preview()

    def update_preview(self):
        composed = self.map_image.copy()

        marker_x = int(
            self.x
            / 100
            * self.target_width
        )

        marker_y = int(
            (
                100 - self.y
            )
            / 100
            * self.target_height
        )

        paste_x = (
            marker_x
            - self.arrow_image.width // 2
        )

        paste_y = (
            marker_y
            - self.arrow_image.height // 2
        )

        composed.paste(
            self.arrow_image,
            (
                paste_x,
                paste_y,
            ),
            self.arrow_image,
        )

        self.tk_image = ImageTk.PhotoImage(
            composed
        )

        self.canvas.delete("all")

        self.canvas.create_image(
            0,
            0,
            anchor="nw",
            image=self.tk_image,
        )

        self.info_label.config(
            text=(
                f"Floor {FLOOR}    "
                f"x {self.x}    "
                f"y {self.y}"
            )
        )

        print(
            f'x {self.x} y {self.y}'
        )

    def save_preview(self, event=None):
        composed = self.map_image.copy()

        marker_x = int(
            self.x
            / 100
            * self.target_width
        )

        marker_y = int(
            (
                100 - self.y
            )
            / 100
            * self.target_height
        )

        paste_x = (
            marker_x
            - self.arrow_image.width // 2
        )

        paste_y = (
            marker_y
            - self.arrow_image.height // 2
        )

        composed.paste(
            self.arrow_image,
            (
                paste_x,
                paste_y,
            ),
            self.arrow_image,
        )

        output_path = ROOT_DIR / "room_preview.png"

        composed.save(output_path)

        print()
        print("Saved")
        print(output_path)
        print()
        print(
            f'{{"x": {self.x}, "y": {self.y}, "floor": {FLOOR}}}'
        )


root = tk.Tk()

root.title("Room map tuner")

app = RoomMapTuner(root)

root.mainloop()