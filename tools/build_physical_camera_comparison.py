#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the documented physical D405 output comparison from source frames."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets/camera"
OUTPUT = ASSETS / "d405-physical-output-comparison.png"
PANEL_SIZE = (640, 480)
HEADER_HEIGHT = 48
FOOTER_HEIGHT = 62
GAP = 8


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stock-rgb",
        type=Path,
        default=ASSETS / "d405-stock15-rgb.png",
    )
    parser.add_argument(
        "--redesigned-rgb",
        type=Path,
        default=ASSETS / "d405-redesigned30-rgb.png",
    )
    parser.add_argument(
        "--redesigned-depth-colorized",
        type=Path,
        default=ASSETS / "d405-redesigned30-depth-colorized.png",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    return parser.parse_args()


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    filename = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(filename, size)
    except OSError:
        return ImageFont.load_default()


def panel(path: Path, label: str) -> Image.Image:
    image = Image.open(path).convert("RGB")
    if image.size != PANEL_SIZE:
        raise ValueError(f"{path} is {image.size}; expected {PANEL_SIZE}")
    result = Image.new("RGB", (PANEL_SIZE[0], PANEL_SIZE[1] + HEADER_HEIGHT), "white")
    result.paste(image, (0, HEADER_HEIGHT))
    draw = ImageDraw.Draw(result)
    draw.text((16, 11), label, fill="#111111", font=load_font(22, bold=True))
    return result


def unavailable_panel(label: str, message: str) -> Image.Image:
    result = Image.new("RGB", (PANEL_SIZE[0], PANEL_SIZE[1] + HEADER_HEIGHT), "white")
    draw = ImageDraw.Draw(result)
    draw.text((16, 11), label, fill="#111111", font=load_font(22, bold=True))
    draw.rectangle(
        (0, HEADER_HEIGHT, PANEL_SIZE[0], PANEL_SIZE[1] + HEADER_HEIGHT),
        fill="#eceff1",
    )
    bbox = draw.multiline_textbbox((0, 0), message, font=load_font(27, bold=True), align="center")
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    draw.multiline_text(
        ((PANEL_SIZE[0] - width) / 2, HEADER_HEIGHT + (PANEL_SIZE[1] - height) / 2),
        message,
        fill="#455a64",
        font=load_font(27, bold=True),
        align="center",
        spacing=8,
    )
    return result


def main() -> None:
    args = parse_args()
    panels = [
        panel(args.stock_rgb, "Seeed-derived stock ~15° | RGB"),
        panel(args.redesigned_rgb, "Redesigned 30° | RGB"),
        unavailable_panel(
            "Seeed-derived stock ~15° | Depth",
            "Depth was not recorded\nin the historical run",
        ),
        panel(
            args.redesigned_depth_colorized,
            "Redesigned 30° | aligned depth, 0.04–0.50 m",
        ),
    ]
    width = PANEL_SIZE[0] * 2 + GAP
    height = (PANEL_SIZE[1] + HEADER_HEIGHT) * 2 + GAP + FOOTER_HEIGHT
    canvas = Image.new("RGB", (width, height), "#cfd8dc")
    canvas.paste(panels[0], (0, 0))
    canvas.paste(panels[1], (PANEL_SIZE[0] + GAP, 0))
    canvas.paste(panels[2], (0, PANEL_SIZE[1] + HEADER_HEIGHT + GAP))
    canvas.paste(
        panels[3],
        (PANEL_SIZE[0] + GAP, PANEL_SIZE[1] + HEADER_HEIGHT + GAP),
    )
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (16, height - FOOTER_HEIGHT + 15),
        "Physical D405 frames. Qualitative only: dates, illumination, and robot poses were not controlled.",
        fill="#263238",
        font=load_font(20),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output, optimize=True)
    print(args.output)


if __name__ == "__main__":
    main()
