"""Build unified, soft-alpha frames for v10 non-dance actions."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from rembg import new_session, remove
from scipy.ndimage import distance_transform_edt, gaussian_filter


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
OUTPUT = ASSETS / "actions"
ACTIONS = ("idle", "wave", "jump", "feed")
CANVAS = (400, 500)
TARGET_REFERENCE_HEIGHT = 460
FOOTLINE = 494


def alpha_bbox(alpha: np.ndarray, threshold: int = 20) -> tuple[int, int, int, int]:
    ys, xs = np.where(alpha >= threshold)
    if not len(xs):
        raise RuntimeError("empty character mask")
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def extend_edge_color(rgba: np.ndarray, confidence: int = 220) -> np.ndarray:
    interior = rgba[..., 3] >= confidence
    if not interior.any():
        return rgba
    _, indices = distance_transform_edt(~interior, return_indices=True)
    outside = ~interior
    rgba[outside, :3] = rgba[indices[0][outside], indices[1][outside], :3]
    return rgba


def semantic_cutout(cell: Image.Image, session) -> Image.Image:
    result = remove(
        cell.convert("RGB"), session=session, post_process_mask=False
    ).convert("RGBA")
    rgba = np.array(result)
    alpha = rgba[..., 3].astype(np.float32)
    alpha[alpha < 5] = 0
    alpha = gaussian_filter(alpha, sigma=0.38)
    alpha[alpha < 2] = 0
    rgba[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    return Image.fromarray(extend_edge_color(rgba), "RGBA")


def keep_inside_canvas(rgba: np.ndarray, margin: int = 4) -> np.ndarray:
    ys, xs = np.where(rgba[..., 3] > 2)
    if not len(xs):
        return rgba
    dx = max(0, margin - int(xs.min())) + min(0, CANVAS[0] - margin - 1 - int(xs.max()))
    dy = max(0, margin - int(ys.min())) + min(0, CANVAS[1] - margin - 1 - int(ys.max()))
    if dx == 0 and dy == 0:
        return rgba
    shifted = np.zeros_like(rgba)
    sx0, sx1 = max(0, -dx), min(CANVAS[0], CANVAS[0] - dx)
    sy0, sy1 = max(0, -dy), min(CANVAS[1], CANVAS[1] - dy)
    shifted[sy0 + dy:sy1 + dy, sx0 + dx:sx1 + dx] = rgba[sy0:sy1, sx0:sx1]
    return shifted


def render_fixed(
    frame: Image.Image, scale: float, center_x: float, foot_y: float
) -> Image.Image:
    resized = frame.resize(
        (round(frame.width * scale), round(frame.height * scale)),
        Image.Resampling.LANCZOS,
    )
    x = round(CANVAS[0] / 2 - center_x * scale)
    y = round(FOOTLINE - foot_y * scale)
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    canvas.alpha_composite(resized, (x, y))
    return Image.fromarray(keep_inside_canvas(extend_edge_color(np.array(canvas))), "RGBA")


def build_action(action: str, session) -> None:
    sheet = Image.open(ASSETS / f"sheet_{action}.png")
    cell_width, cell_height = sheet.width // 4, sheet.height // 2
    cutouts = []
    for index in range(8):
        row, column = divmod(index, 4)
        cell = sheet.crop((
            column * cell_width,
            row * cell_height,
            (column + 1) * cell_width,
            (row + 1) * cell_height,
        ))
        cutouts.append(semantic_cutout(cell, session))
    reference_bbox = alpha_bbox(np.array(cutouts[0].getchannel("A")))
    _, ref_top, _, ref_foot = reference_bbox
    scale = TARGET_REFERENCE_HEIGHT / (ref_foot - ref_top)
    for index, frame in enumerate(cutouts):
        x0, _, x1, frame_foot = alpha_bbox(np.array(frame.getchannel("A")))
        center_x = (x0 + x1) / 2
        # Jump keeps source-sheet vertical displacement; all standing actions
        # share one foot baseline without changing character scale.
        foot_y = ref_foot if action == "jump" else frame_foot
        render_fixed(frame, scale, center_x, foot_y).save(
            OUTPUT / f"{action}_{index}.png", optimize=True
        )
    print(f"{action}: 8 frames, reference scale {scale:.4f}")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    session = new_session("isnet-anime")
    for action in ACTIONS:
        build_action(action, session)


if __name__ == "__main__":
    main()
