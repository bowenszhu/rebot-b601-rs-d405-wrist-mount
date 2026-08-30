#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fine-angle D405 FOV and clearance sweep for the B601 task geometry.

This intentionally omits the mount mesh: the exact design camera datum and a
full-size conservative D405 box are sufficient for visibility, minimum-range
and D405-to-green clearance checks. Printable angles are still generated
and validated by design_mount.py.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import mujoco
import numpy as np

import simulate_fov as sim


def border_contact(segmentation: np.ndarray, ids: set[int]) -> bool:
    geom_type = int(mujoco.mjtObj.mjOBJ_GEOM)
    mask = np.isin(segmentation[..., 0], list(ids)) & (
        segmentation[..., 1] == geom_type
    )
    return bool(
        mask[0, :].any()
        or mask[-1, :].any()
        or mask[:, 0].any()
        or mask[:, -1].any()
    )


def camera_to_target_mm(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera_name: str,
    target: np.ndarray,
) -> float:
    camera_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, camera_name)
    return float(np.linalg.norm(data.cam_xpos[camera_id] - target) * 1000.0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=float, default=20.0)
    parser.add_argument("--end", type=float, default=36.0)
    parser.add_argument("--step", type=float, default=1.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=sim.OUTPUT_DIR / "wrist_rgb_angle_sweep_1deg.csv",
    )
    args = parser.parse_args()
    angles = np.arange(args.start, args.end + 0.5 * args.step, args.step)

    # Solve robot poses once; changing only camera pitch does not change arm IK.
    reference_model, _, _, _ = sim.build_model(30.0, include_mount=False)
    reference_solver = sim.IKSolver(reference_model)
    q = np.zeros(6)
    solutions = []
    for stage, target in sim.STAGES:
        q, pos_error, rot_error = reference_solver.solve(target, q)
        if pos_error > 0.006 or rot_error > 0.06:
            raise RuntimeError(f"IK failed at {stage}")
        solutions.append((stage, target, q.copy()))

    rows: list[dict[str, float | int | str | bool]] = []
    for angle in angles:
        model, camera_name, _, tray_names = sim.build_model(
            float(angle), include_mount=False
        )
        solver = sim.IKSolver(model)
        renderer = mujoco.Renderer(
            model, height=sim.RENDER_HEIGHT, width=sim.RENDER_WIDTH
        )
        option = mujoco.MjvOption()
        option.geomgroup[4] = 0
        option.geomgroup[5] = 0
        solver.set_q(np.zeros(6))
        clearance = sim.d405_green_clearance_mm(model, solver.data)
        try:
            for stage, target, stage_q in solutions:
                solver.set_q(stage_q)
                blue_ids = sim.geom_ids(model, ["blue_block_geom"])
                tray_ids = sim.geom_ids(model, tray_names)
                left_ids = sim.body_geom_ids(model, "gripper_left")
                right_ids = sim.body_geom_ids(model, "gripper_right")
                renderer.enable_segmentation_rendering()
                renderer.update_scene(
                    solver.data, camera=camera_name, scene_option=option
                )
                seg = renderer.render().copy()
                blue = sim.segmentation_stats(seg, blue_ids)
                tray = sim.segmentation_stats(seg, tray_ids)
                left = sim.segmentation_stats(seg, left_ids)
                right = sim.segmentation_stats(seg, right_ids)
                rows.append(
                    {
                        "angle_deg": float(angle),
                        "stage": stage,
                        "d405_green_clearance_mm": clearance,
                        "camera_to_tcp_target_mm": camera_to_target_mm(
                            model, solver.data, camera_name, target
                        ),
                        "blue_px": blue[0],
                        "blue_cx": blue[1],
                        "blue_cy": blue[2],
                        "blue_touches_border": border_contact(seg, blue_ids),
                        "tray_px": tray[0],
                        "tray_cx": tray[1],
                        "tray_cy": tray[2],
                        "tray_touches_border": border_contact(seg, tray_ids),
                        "left_finger_px": left[0],
                        "right_finger_px": right[0],
                    }
                )
        finally:
            renderer.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"PASS angles={len(angles)} views={len(rows)} output={args.output}")
    print("angle clearance min_range high_blue grasp_blue place_tray border")
    for angle in angles:
        selected = [row for row in rows if row["angle_deg"] == float(angle)]
        by_stage = {str(row["stage"]): row for row in selected}
        border = any(
            bool(row["blue_touches_border"] or row["tray_touches_border"])
            for row in selected
        )
        print(
            f"{angle:5.1f} "
            f"{selected[0]['d405_green_clearance_mm']:9.2f} "
            f"{min(float(row['camera_to_tcp_target_mm']) for row in selected):9.1f} "
            f"{int(by_stage['high_align']['blue_px']):9d} "
            f"{int(by_stage['grasp']['blue_px']):10d} "
            f"{int(by_stage['place']['tray_px']):10d} "
            f"{str(border):>6s}"
        )


if __name__ == "__main__":
    main()
