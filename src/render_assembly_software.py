#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Render mount and rounded D405 proxy together in four CAD views."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from render_stl_software import VIEWS, font, read_binary_stl, unit


OBJECTS = (
    ("mount", (225, 92, 28)),
    ("D405 envelope", (25, 181, 220)),
)


def draw_view(
    image: Image.Image,
    meshes: list[np.ndarray],
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

    triangles = np.concatenate(meshes, axis=0)
    object_ids = np.concatenate(
        [np.full(len(mesh), index, dtype=np.int32) for index, mesh in enumerate(meshes)]
    )
    vertices = triangles.reshape(-1, 3)
    center = 0.5 * (vertices.min(axis=0) + vertices.max(axis=0))
    relative = triangles - center
    projected_x = relative @ right
    projected_y = relative @ up
    all_x = projected_x.reshape(-1)
    all_y = projected_y.reshape(-1)
    width = max(float(np.ptp(all_x)), 1e-9)
    height = max(float(np.ptp(all_y)), 1e-9)

    content_left = panel_x + 48 * supersample
    content_right = panel_x + panel_width - 48 * supersample
    content_top = panel_y + 42 * supersample
    content_bottom = panel_y + panel_height - 80 * supersample
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
    visible = valid & ((normals @ camera_axis) > 1e-7)
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
        base = np.asarray(OBJECTS[int(object_ids[index])][1], dtype=np.float64)
        illumination = 0.62 + 0.38 * max(0.0, float(normals[index] @ light))
        colour = tuple(np.clip(np.rint(base * illumination), 0, 255).astype(int))
        draw.polygon(points, fill=colour, outline=(28, 28, 28))

    draw.text(
        (panel_x + 18 * supersample, panel_y + panel_height - 55 * supersample),
        label,
        fill=(20, 20, 20),
        font=font(26 * supersample),
    )
    legend_x = panel_x + 18 * supersample
    legend_y = panel_y + 12 * supersample
    for object_label, colour in OBJECTS:
        draw.rectangle(
            (
                legend_x,
                legend_y,
                legend_x + 18 * supersample,
                legend_y + 14 * supersample,
            ),
            fill=colour,
            outline=(25, 25, 25),
        )
        draw.text(
            (legend_x + 25 * supersample, legend_y - 4 * supersample),
            object_label,
            fill=(20, 20, 20),
            font=font(14 * supersample),
        )
        legend_y += 21 * supersample


def render(mount_path: Path, camera_path: Path, output_path: Path) -> None:
    meshes = [read_binary_stl(mount_path), read_binary_stl(camera_path)]
    supersample = 2
    output_size = (1600, 1200)
    image = Image.new(
        "RGB",
        (output_size[0] * supersample, output_size[1] * supersample),
        (247, 247, 247),
    )
    panel_size = (800 * supersample, 600 * supersample)
    for index, (label, direction, view_up) in enumerate(VIEWS):
        draw_view(
            image,
            meshes,
            label,
            direction,
            view_up,
            ((index % 2) * panel_size[0], (index // 2) * panel_size[1]),
            panel_size,
            supersample,
        )
    image = image.resize(output_size, Image.Resampling.LANCZOS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    print(
        f"PASS mount_triangles={len(meshes[0])} camera_triangles={len(meshes[1])} "
        f"output={output_path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mount", type=Path)
    parser.add_argument("camera", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    render(args.mount, args.camera, args.output)


if __name__ == "__main__":
    main()
