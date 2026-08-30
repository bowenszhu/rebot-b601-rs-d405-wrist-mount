#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Render a binary STL into four orthographic engineering views.

This software rasterizer is the headless fallback for hosts whose VTK build
requires an X11 OpenGL context.  It deliberately draws triangle edges so the
result has the same CAD-inspection character as ``render_cad.py``.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VIEWS = (
    ("isometric", (1.0, -1.0, 0.8), (0.0, 0.0, 1.0)),
    ("front", (0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    ("side", (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    ("top", (0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
)

REVIEW_VIEWS = (
    ("isometric front-left", (1.0, -1.0, 0.8), (0.0, 0.0, 1.0)),
    ("isometric front-right", (-1.0, -1.0, 0.8), (0.0, 0.0, 1.0)),
    ("isometric rear-left", (1.0, 1.0, 0.8), (0.0, 0.0, 1.0)),
    ("isometric rear-right", (-1.0, 1.0, 0.8), (0.0, 0.0, 1.0)),
    ("front", (0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    ("rear / screw heads", (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    ("left side", (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    ("right side", (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    ("top", (0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
    ("bottom / B601 holes", (0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
    # These two views look normal to the 30-degree camera backplate. They make
    # the D405 seat, side wrap and two screw passages easy to inspect without
    # adding a camera proxy that could hide the mount itself.
    ("D405 seat normal", (0.0, -0.5, 0.8660254), (0.0, 0.8660254, 0.5)),
    ("backplate outer normal", (0.0, 0.5, -0.8660254), (0.0, 0.8660254, 0.5)),
)


def unit(vector: np.ndarray) -> np.ndarray:
    length = float(np.linalg.norm(vector))
    if length < 1e-12:
        raise ValueError("Zero-length view vector")
    return vector / length


def read_binary_stl(path: Path) -> np.ndarray:
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError(f"STL is too small: {path}")
    triangle_count = struct.unpack_from("<I", data, 80)[0]
    expected_size = 84 + 50 * triangle_count
    if len(data) != expected_size:
        raise ValueError(
            f"Expected binary STL with {triangle_count} triangles and "
            f"{expected_size} bytes, found {len(data)} bytes"
        )
    record = np.dtype(
        [
            ("normal", "<f4", (3,)),
            ("vertices", "<f4", (3, 3)),
            ("attribute", "<u2"),
        ]
    )
    triangles = np.frombuffer(data, dtype=record, count=triangle_count, offset=84)
    return triangles["vertices"].astype(np.float64)


def font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def draw_view(
    image: Image.Image,
    triangles: np.ndarray,
    label: str,
    direction: tuple[float, float, float],
    view_up: tuple[float, float, float],
    panel_origin: tuple[int, int],
    panel_size: tuple[int, int],
    supersample: int,
) -> None:
    draw = ImageDraw.Draw(image)
    panel_x, panel_y = panel_origin
    panel_width, panel_height = panel_size

    camera_axis = unit(np.asarray(direction, dtype=np.float64))
    requested_up = unit(np.asarray(view_up, dtype=np.float64))
    right = unit(np.cross(camera_axis, requested_up))
    up = unit(np.cross(right, camera_axis))

    vertices = triangles.reshape(-1, 3)
    center = 0.5 * (vertices.min(axis=0) + vertices.max(axis=0))
    relative = triangles - center
    projected_x = relative @ right
    projected_y = relative @ up
    all_x = projected_x.reshape(-1)
    all_y = projected_y.reshape(-1)
    width = max(float(np.ptp(all_x)), 1e-9)
    height = max(float(np.ptp(all_y)), 1e-9)

    content_left = panel_x + 52 * supersample
    content_right = panel_x + panel_width - 52 * supersample
    content_top = panel_y + 35 * supersample
    content_bottom = panel_y + panel_height - 82 * supersample
    scale = min((content_right - content_left) / width, (content_bottom - content_top) / height)
    projected_mid_x = 0.5 * (float(all_x.min()) + float(all_x.max()))
    projected_mid_y = 0.5 * (float(all_y.min()) + float(all_y.max()))
    screen_mid_x = 0.5 * (content_left + content_right)
    screen_mid_y = 0.5 * (content_top + content_bottom)

    edges_a = relative[:, 1] - relative[:, 0]
    edges_b = relative[:, 2] - relative[:, 0]
    normals = np.cross(edges_a, edges_b)
    lengths = np.linalg.norm(normals, axis=1)
    valid = lengths > 1e-12
    normals[valid] /= lengths[valid, None]
    facing = normals @ camera_axis
    visible = valid & (facing > 1e-7)

    depth = np.mean(relative @ camera_axis, axis=1)
    order = np.argsort(depth)
    light = unit(camera_axis + 0.65 * up - 0.25 * right)

    for index in order:
        if not visible[index]:
            continue
        points = []
        for x, y in zip(projected_x[index], projected_y[index]):
            px = screen_mid_x + (float(x) - projected_mid_x) * scale
            py = screen_mid_y - (float(y) - projected_mid_y) * scale
            points.append((round(px), round(py)))
        illumination = max(0.0, float(normals[index] @ light))
        gray = int(round(178 + 50 * illumination))
        draw.polygon(points, fill=(gray, gray + 2, min(255, gray + 8)), outline=(31, 31, 31))

    draw.text(
        (panel_x + 18 * supersample, panel_y + panel_height - 55 * supersample),
        label,
        fill=(20, 20, 20),
        font=font(26 * supersample),
    )


def render(input_path: Path, output_path: Path, review: bool = False) -> None:
    triangles = read_binary_stl(input_path)
    supersample = 2
    views = REVIEW_VIEWS if review else VIEWS
    columns = 4 if review else 2
    rows = 3 if review else 2
    output_size = (2400, 1800) if review else (1600, 1200)
    image = Image.new(
        "RGB",
        (output_size[0] * supersample, output_size[1] * supersample),
        (247, 247, 247),
    )
    panel_size = (
        output_size[0] * supersample // columns,
        output_size[1] * supersample // rows,
    )
    for index, (label, direction, view_up) in enumerate(views):
        col = index % columns
        row = index // columns
        draw_view(
            image,
            triangles,
            label,
            direction,
            view_up,
            (col * panel_size[0], row * panel_size[1]),
            panel_size,
            supersample,
        )
    image = image.resize(output_size, Image.Resampling.LANCZOS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    print(
        f"PASS triangles={len(triangles)} size={output_size[0]}x{output_size[1]} "
        f"output={output_path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--review",
        action="store_true",
        help="render 12 mount-only inspection views instead of four views",
    )
    args = parser.parse_args()
    render(args.input, args.output, review=args.review)


if __name__ == "__main__":
    main()
