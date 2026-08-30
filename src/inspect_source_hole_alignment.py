#!/usr/bin/env python3
# SPDX-License-Identifier: CERN-OHL-W-2.0
"""Measure the inherited Seeed D405 cradle and rear through-hole axes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cadquery as cq


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STEP = ROOT / "hardware/vendor/seeed-rebot-devarm/D405_305_Mount.step"


def inspect(path: Path) -> dict[str, float | list[float] | str]:
    shape = cq.importers.importStep(str(path)).val()
    bounds = shape.BoundingBox()
    cradle_center_x = (bounds.xmin + bounds.xmax) / 2.0

    through_axes = []
    for face in shape.Faces():
        if face.geomType() != "CYLINDER":
            continue
        cylinder = face._geomAdaptor().Cylinder()
        if abs(cylinder.Radius() - 1.6) > 1e-4:
            continue
        location = cylinder.Axis().Location()
        if location.Y() < 60.0:
            continue
        through_axes.append(float(location.X()))

    through_axes = sorted(through_axes)
    if len(through_axes) != 2:
        raise RuntimeError(f"Expected two D405 through-hole axes, found {through_axes}")
    spacing = through_axes[1] - through_axes[0]
    pair_center = sum(through_axes) / 2.0
    offset = pair_center - cradle_center_x
    result: dict[str, float | list[float] | str] = {
        "source_step": str(path.relative_to(ROOT)),
        "cradle_x_min_mm": bounds.xmin,
        "cradle_x_max_mm": bounds.xmax,
        "cradle_center_x_mm": cradle_center_x,
        "through_hole_axes_x_mm": through_axes,
        "through_hole_spacing_mm": spacing,
        "through_hole_pair_center_x_mm": pair_center,
        "pair_offset_from_cradle_center_x_mm": offset,
        "required_correction_x_mm": -offset,
        "realsense_reference": (
            "https://realsenseai.com/wp-content/uploads/2025/09/"
            "Intel-RealSense-D400-Series-Datasheet-October-2025.pdf#page=146"
        ),
    }
    if abs(spacing - 20.0) > 1e-6 or abs(offset - 1.0) > 1e-6:
        raise RuntimeError(
            f"Unexpected source pattern spacing={spacing:.9f} offset={offset:.9f}"
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=Path, default=DEFAULT_STEP)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = inspect(args.step.resolve())
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
