"""Build a blue-background size and alpha inspection sheet."""
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ("idle_0", "wave_0", "jump_0", "jump_3", "feed_0", "dance_000")


def main() -> None:
    output = Image.new("RGB", (1200, 500), (64, 92, 120))
    draw = ImageDraw.Draw(output)
    for index, name in enumerate(SAMPLES):
        frame = Image.open(ROOT / "assets" / "actions" / f"{name}.png").convert("RGBA")
        frame = frame.resize((200, 250), Image.Resampling.LANCZOS)
        background = Image.new("RGBA", frame.size, (64, 92, 120, 255))
        background.alpha_composite(frame)
        x = index * 200
        output.paste(background.convert("RGB"), (x, 0))
        draw.text((x + 6, 6), name, fill="white")
    destination = ROOT / "qa" / "action_size_alpha_check.png"
    destination.parent.mkdir(parents=True, exist_ok=True)
    output.save(destination)

    actions = ("idle", "wave", "jump", "feed")
    all_frames = Image.new("RGB", (1200, 752), (64, 92, 120))
    all_draw = ImageDraw.Draw(all_frames)
    for row, action in enumerate(actions):
        for column in range(8):
            frame = Image.open(
                ROOT / "assets" / "actions" / f"{action}_{column}.png"
            ).convert("RGBA")
            frame = frame.resize((150, 188), Image.Resampling.LANCZOS)
            background = Image.new("RGBA", frame.size, (64, 92, 120, 255))
            background.alpha_composite(frame)
            x, y = column * 150, row * 188
            all_frames.paste(background.convert("RGB"), (x, y))
            all_draw.text((x + 4, y + 4), f"{action}_{column}", fill="white")
    all_frames.save(ROOT / "qa" / "all_main_keyframes_on_blue.png")


if __name__ == "__main__":
    main()
