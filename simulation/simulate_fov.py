#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare D405 wrist-camera pitch angles in the existing B601 MuJoCo scene.

This is a first-order visibility and mechanical-clearance simulation, not an
extrinsic calibration.  It loads the actual mount STL and a full-size D405
housing envelope into the B601-RS MuJoCo model.  The camera pinhole is placed
at the left imager (the RGB and depth origin), not at the housing centre.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = Path(
    os.environ.get(
        "REBOT_MUJOCO_MODEL",
        REPOSITORY_ROOT
        / "external/ReBot_Arm_web_RS/rebotarm_ros2/src/"
        "rebotarm_mujoco_rs/models/rs_grasp_scene.xml",
    )
)
OUTPUT_DIR = REPOSITORY_ROOT / "build"
SIMULATION_ASSET_DIR = REPOSITORY_ROOT / "simulation/assets"

ANGLES_DEG = (15.0, 25.0, 30.0, 35.0)
MOUNT_STL_BY_ANGLE = {
    15.0: SIMULATION_ASSET_DIR / "seeed_original_d405_15deg.stl",
    25.0: OUTPUT_DIR / "rebot_b601_d405_down_25deg.stl",
    30.0: OUTPUT_DIR / "rebot_b601_d405_down_30deg.stl",
    35.0: OUTPUT_DIR / "rebot_b601_d405_down_35deg.stl",
    45.0: OUTPUT_DIR / "rebot_b601_d405_down_45deg.stl",
}
D405_PROXY_STL_BY_ANGLE = {
    angle: OUTPUT_DIR / f"rebot_b601_d405_down_{angle:g}deg_d405_proxy.stl"
    for angle in (25.0, 30.0, 35.0, 45.0)
}
GEOMETRY_JSON_BY_ANGLE = {
    angle: OUTPUT_DIR / f"rebot_b601_d405_down_{angle:g}deg_geometry.json"
    for angle in (25.0, 30.0, 35.0, 45.0)
}
RENDER_WIDTH = 640
RENDER_HEIGHT = 480
# Factory calibration read from D405 serial 260522274196 at 640x480 RGB:
# FOV 78.22 x 62.82 deg, principal point (323.24, 235.99).  MuJoCo's camera
# model has a centred principal point, so the residual 3-4 pixel offset and
# lens distortion are intentionally outside this first-order screen.
D405_RGB_VERTICAL_FOV_DEG = 62.82

# Seeed STEP coordinates, mm.  The original mount has a 15-degree pitch.
BASE_REFERENCE_Y = 29.999
BASE_REFERENCE_Z = -22.0
D405_DEPTH = 23.0
D405_DEPTH_ORIGIN_BEHIND_FRONT_GLASS = 3.7
D405_OPTICAL_FROM_REAR = D405_DEPTH - D405_DEPTH_ORIGIN_BEHIND_FRONT_GLASS
D405_LEFT_IMAGER_OFFSET_X = 9.0
OPTICAL_CENTERING_SHIFT_X = -9.0
OFFICIAL_CRADLE_CENTER_X = 0.0014555241296942967

# The green bracket rear face is x=-103.209 mm.  At the screw centreline the
# official mount base spans CAD Z=-22.0..-16.9 mm, i.e. it is 5.1 mm thick.
# Place the base front face on the green rear face, leaving the base itself
# behind the green block rather than embedding that thickness into it.
GREEN_BRACKET_REAR_X = -0.103209
MOUNT_BASE_THICKNESS = 0.0051
GRIPPER_BASE_X = GREEN_BRACKET_REAR_X - MOUNT_BASE_THICKNESS
# The upper camera-mount hole pair in the official green rail-bracket STEP is
# centred at gripper z=+30.0 mm (STEP Z=-114.5 mm plus the 144.5 mm mesh
# offset).  The previous top-surface alignment incorrectly raised the mount by
# 11.937 mm instead of aligning the actual screw axes.
GRIPPER_BASE_Z = 0.030

# Rigid transform from the Seeed/CadQuery mount frame (millimetres) into the
# MuJoCo gripper_end frame (metres): CAD +X -> gripper +Y, CAD +Y -> gripper
# +Z, CAD +Z -> gripper +X.  The lateral datum is the official mount's original
# housing centreline; its two base holes have a small intentional asymmetry.
MOUNT_REFERENCE_CAD = np.array(
    [OFFICIAL_CRADLE_CENTER_X, BASE_REFERENCE_Y, BASE_REFERENCE_Z],
    dtype=np.float64,
)
MOUNT_REFERENCE_GRIPPER = np.array(
    [GRIPPER_BASE_X, 0.0, GRIPPER_BASE_Z], dtype=np.float64
)
MOUNT_ROTATION = np.array(
    [[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
    dtype=np.float64,
)
MOUNT_QUAT_WXYZ = [0.5, 0.5, 0.5, 0.5]
MOUNT_TRANSLATION = MOUNT_REFERENCE_GRIPPER - (
    MOUNT_ROTATION @ MOUNT_REFERENCE_CAD
) / 1000.0

ARM_JOINTS = tuple(f"joint{i}" for i in range(1, 7))
TCP_OFFSET = np.array([-0.04, 0.0, 0.0], dtype=np.float64)

STAGES = (
    ("high_align", np.array([0.32, 0.08, 0.185])),
    ("pregrasp", np.array([0.32, 0.08, 0.160])),
    ("grasp", np.array([0.32, 0.08, 0.140])),
    ("preplace", np.array([0.32, -0.09, 0.185])),
    ("place", np.array([0.32, -0.09, 0.145])),
)


def cad_to_gripper(point_mm: np.ndarray) -> np.ndarray:
    return MOUNT_TRANSLATION + MOUNT_ROTATION @ point_mm / 1000.0


def camera_geometry_in_cad(
    angle_deg: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    angle = math.radians(angle_deg)
    up = np.array([0.0, math.cos(angle), math.sin(angle)])
    forward = np.array([0.0, -math.sin(angle), math.cos(angle)])

    if math.isclose(angle_deg, 15.0):
        # Housing center and plate normal measured from the Seeed cradle.
        screw_y = 68.972
        screw_z = -10.612
        optical_offset = D405_OPTICAL_FROM_REAR
        screw_center = np.array(
            [OFFICIAL_CRADLE_CENTER_X, screw_y, screw_z]
        )
        # Seeed centres the D405 housing.  RGB/depth originate at the left
        # imager, 9 mm to +CAD-X, so the stock image is laterally off-centre.
        optical_x = OFFICIAL_CRADLE_CENTER_X + D405_LEFT_IMAGER_OFFSET_X
    else:
        geometry_path = GEOMETRY_JSON_BY_ANGLE.get(angle_deg)
        if geometry_path is not None and geometry_path.exists():
            geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
            screw_center = np.asarray(geometry["screw_center_mm"], dtype=np.float64)
            up = np.asarray(geometry["camera_up"], dtype=np.float64)
            forward = np.asarray(geometry["optical_forward"], dtype=np.float64)
        else:
            # Analytic equivalent of design_mount.camera_frame().  This lets
            # fine-angle visibility sweeps use the exact design datum without
            # generating a throwaway STEP/STL for every candidate angle.
            stock_angle = math.radians(15.0)
            stock_up = np.array([0.0, math.cos(stock_angle), math.sin(stock_angle)])
            stock_center = np.array(
                [
                    OFFICIAL_CRADLE_CENTER_X,
                    68.9724,
                    -10.6118,
                ],
                dtype=np.float64,
            )
            stock_lower_rear = stock_center - stock_up * 21.0
            screw_center = np.array(
                [
                    OFFICIAL_CRADLE_CENTER_X + OPTICAL_CENTERING_SHIFT_X,
                    stock_lower_rear[1],
                    stock_lower_rear[2],
                ],
                dtype=np.float64,
            ) + up * 27.0
        optical_offset = D405_OPTICAL_FROM_REAR
        # The new mount moves the housing 9 mm in -CAD-X. This cancels the
        # +9 mm left-imager offset and returns the effective pinhole to the
        # original gripper/camera centreline.
        optical_x = (
            OFFICIAL_CRADLE_CENTER_X
            + OPTICAL_CENTERING_SHIFT_X
            + D405_LEFT_IMAGER_OFFSET_X
        )

    optical_point = screw_center + optical_offset * forward
    optical_point[0] = optical_x
    return screw_center, optical_point, up, forward


def camera_pose_in_gripper(angle_deg: float) -> tuple[list[float], list[float]]:
    _, optical_point, up_cad, _ = camera_geometry_in_cad(angle_deg)
    position = cad_to_gripper(optical_point)
    image_up = MOUNT_ROTATION @ up_cad

    # MuJoCo camera looks along local -Z. x-axis spans the gripper width and
    # y-axis is image-up; x cross y therefore equals -optical_direction.
    image_x = [0.0, -1.0, 0.0]
    xyaxes = image_x + image_up.tolist()
    return position.tolist(), xyaxes


def d405_housing_pose_in_gripper(
    angle_deg: float,
) -> tuple[list[float], list[float]]:
    screw_center, _, up_cad, forward_cad = camera_geometry_in_cad(angle_deg)
    # The metadata screw centre lies on the D405 rear housing plane.
    center_cad = screw_center + forward_cad * (D405_DEPTH / 2.0)
    center = cad_to_gripper(center_cad)
    width_axis = MOUNT_ROTATION @ np.array([1.0, 0.0, 0.0])
    height_axis = MOUNT_ROTATION @ up_cad
    return center.tolist(), width_axis.tolist() + height_axis.tolist()


def build_model(
    angle: float,
    include_mount: bool = True,
) -> tuple[mujoco.MjModel, str, str, list[str]]:
    spec = mujoco.MjSpec.from_file(str(MODEL_PATH))
    spec.visual.global_.offwidth = RENDER_WIDTH
    spec.visual.global_.offheight = RENDER_HEIGHT
    gripper = spec.body("gripper_end")
    if include_mount:
        mount_path = MOUNT_STL_BY_ANGLE.get(angle)
        if mount_path is None or not mount_path.exists():
            raise FileNotFoundError(f"No generated mount STL for {angle:g} degrees")
        mount_mesh_name = f"d405_mount_mesh_{angle:g}"
        spec.add_mesh(
            name=mount_mesh_name,
            file=str(mount_path),
            scale=[0.001, 0.001, 0.001],
        )
        gripper.add_geom(
            name=f"d405_mount_{angle:g}",
            type=mujoco.mjtGeom.mjGEOM_MESH,
            meshname=mount_mesh_name,
            pos=MOUNT_TRANSLATION.tolist(),
            quat=MOUNT_QUAT_WXYZ,
            group=1,
            contype=0,
            conaffinity=0,
            # High-contrast diagnostic colour; the printed part remains black.
            rgba=[1.0, 0.32, 0.02, 1.0],
        )

    housing_position, housing_xyaxes = d405_housing_pose_in_gripper(angle)
    if include_mount and angle in D405_PROXY_STL_BY_ANGLE:
        proxy_path = D405_PROXY_STL_BY_ANGLE[angle]
        if not proxy_path.exists():
            raise FileNotFoundError(proxy_path)
        proxy_mesh_name = f"d405_proxy_mesh_{angle:g}"
        spec.add_mesh(
            name=proxy_mesh_name,
            file=str(proxy_path),
            scale=[0.001, 0.001, 0.001],
        )
        gripper.add_geom(
            name="d405_housing_visual",
            type=mujoco.mjtGeom.mjGEOM_MESH,
            meshname=proxy_mesh_name,
            pos=MOUNT_TRANSLATION.tolist(),
            quat=MOUNT_QUAT_WXYZ,
            group=4,
            contype=0,
            conaffinity=0,
            rgba=[0.05, 0.72, 0.95, 1.0],
        )
    else:
        gripper.add_geom(
            name="d405_housing_visual",
            type=mujoco.mjtGeom.mjGEOM_BOX,
            pos=housing_position,
            xyaxes=housing_xyaxes,
            size=[0.021, 0.021, D405_DEPTH / 2000.0],
            group=4,
            contype=0,
            conaffinity=0,
            rgba=[0.05, 0.72, 0.95, 1.0],
        )
    # Keep a sharp-corner box for conservative green-part clearance. It is
    # hidden from both first-person and external images.
    gripper.add_geom(
        name="d405_collision_envelope",
        type=mujoco.mjtGeom.mjGEOM_BOX,
        pos=housing_position,
        xyaxes=housing_xyaxes,
        size=[0.021, 0.021, D405_DEPTH / 2000.0],
        group=5,
        contype=0,
        conaffinity=0,
        rgba=[0.0, 0.0, 0.0, 0.0],
    )

    camera_name = f"wrist_{angle:g}deg"
    position, xyaxes = camera_pose_in_gripper(angle)
    gripper.add_camera(
        name=camera_name,
        pos=position,
        xyaxes=xyaxes,
        fovy=D405_RGB_VERTICAL_FOV_DEG,
    )
    gripper.add_geom(
        name="d405_optical_origin",
        type=mujoco.mjtGeom.mjGEOM_SPHERE,
        pos=position,
        size=[0.002],
        group=4,
        contype=0,
        conaffinity=0,
        rgba=[1.0, 0.0, 1.0, 1.0],
    )
    side_camera_name = f"assembly_side_{angle:g}deg"
    gripper.add_camera(
        name=side_camera_name,
        pos=[-0.100, -0.30, 0.075],
        xyaxes=[1.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        fovy=28.0,
    )

    # A simple white tray proxy at the scene's red-object location.  Its size
    # approximates the user's physical tray and is used only for visibility.
    tray = spec.worldbody.add_body(name="white_tray", pos=[0.32, -0.09, 0.103])
    tray_geoms = []
    tray_geoms.append(
        tray.add_geom(
            name="tray_base",
            type=mujoco.mjtGeom.mjGEOM_BOX,
            size=[0.065, 0.050, 0.003],
            rgba=[0.92, 0.92, 0.92, 1.0],
        ).name
    )
    for name, pos, size in (
        ("tray_front", [0.0, -0.047, 0.010], [0.065, 0.003, 0.010]),
        ("tray_back", [0.0, 0.047, 0.010], [0.065, 0.003, 0.010]),
        ("tray_left", [-0.062, 0.0, 0.010], [0.003, 0.047, 0.010]),
        ("tray_right", [0.062, 0.0, 0.010], [0.003, 0.047, 0.010]),
    ):
        tray_geoms.append(
            tray.add_geom(
                name=name,
                type=mujoco.mjtGeom.mjGEOM_BOX,
                pos=pos,
                size=size,
                rgba=[0.96, 0.96, 0.96, 1.0],
            ).name
        )
    return spec.compile(), camera_name, side_camera_name, tray_geoms


class IKSolver:
    def __init__(self, model: mujoco.MjModel):
        self.model = model
        self.data = mujoco.MjData(model)
        mujoco.mj_forward(model, self.data)
        self.base_qpos = self.data.qpos.copy()
        self.qpos_addr = []
        lower = []
        upper = []
        for name in ARM_JOINTS:
            joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
            self.qpos_addr.append(int(model.jnt_qposadr[joint_id]))
            lower.append(float(model.jnt_range[joint_id, 0]))
            upper.append(float(model.jnt_range[joint_id, 1]))
        self.lower = np.asarray(lower)
        self.upper = np.asarray(upper)
        self.body_id = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_BODY, "gripper_end"
        )
        quat = np.array([math.sqrt(0.5), 0.0, math.sqrt(0.5), 0.0])
        matrix = np.zeros(9)
        mujoco.mju_quat2Mat(matrix, quat)
        self.target_rotation = matrix.reshape(3, 3)

    def set_q(self, q: np.ndarray) -> None:
        self.data.qpos[:] = self.base_qpos
        self.data.qvel[:] = 0.0
        for addr, value in zip(self.qpos_addr, q):
            self.data.qpos[addr] = value
        mujoco.mj_forward(self.model, self.data)

    def fk(self, q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        self.set_q(q)
        rotation = self.data.xmat[self.body_id].reshape(3, 3).copy()
        position = self.data.xpos[self.body_id].copy() + rotation @ TCP_OFFSET
        return position, rotation

    @staticmethod
    def orientation_error(current: np.ndarray, target: np.ndarray) -> np.ndarray:
        return Rotation.from_matrix(target @ current.T).as_rotvec()

    def residual(self, q: np.ndarray, target: np.ndarray) -> np.ndarray:
        position, rotation = self.fk(q)
        return np.concatenate(
            [target - position, 0.6 * self.orientation_error(rotation, self.target_rotation)]
        )

    def solve(self, target: np.ndarray, start: np.ndarray) -> tuple[np.ndarray, float, float]:
        seeds = [
            start,
            np.array([0.0, 1.6, 1.2, -0.8, 0.0, 0.0]),
            np.array([0.2, 1.2, 0.5, 0.0, 0.5, -2.5]),
            np.array([-0.2, 1.2, 0.5, 0.0, -0.5, 2.5]),
            np.array([0.0, 2.0, 1.7, -1.3, 0.0, 0.0]),
        ]
        best = None
        for seed in seeds:
            solved = least_squares(
                self.residual,
                np.clip(seed, self.lower + 1e-5, self.upper - 1e-5),
                args=(target,),
                bounds=(self.lower, self.upper),
                max_nfev=600,
                xtol=1e-9,
                ftol=1e-9,
                gtol=1e-9,
            )
            q = np.clip(solved.x, self.lower, self.upper)
            position, rotation = self.fk(q)
            pos_error = float(np.linalg.norm(target - position))
            rot_error = float(np.linalg.norm(self.orientation_error(rotation, self.target_rotation)))
            score = pos_error + 0.25 * rot_error
            if best is None or score < best[0]:
                best = (score, q.copy(), pos_error, rot_error)
        assert best is not None
        return best[1], best[2], best[3]


def body_geom_ids(model: mujoco.MjModel, body_name: str) -> set[int]:
    body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
    start = int(model.body_geomadr[body_id])
    count = int(model.body_geomnum[body_id])
    return set(range(start, start + count))


def geom_ids(model: mujoco.MjModel, names: list[str]) -> set[int]:
    return {
        mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, name)
        for name in names
    }


def segmentation_pixels(segmentation: np.ndarray, ids: set[int]) -> int:
    # MuJoCo returns (object id, object type) per pixel.
    geom_type = int(mujoco.mjtObj.mjOBJ_GEOM)
    return int(
        np.count_nonzero(
            np.isin(segmentation[..., 0], list(ids))
            & (segmentation[..., 1] == geom_type)
        )
    )


def segmentation_stats(
    segmentation: np.ndarray, ids: set[int]
) -> tuple[int, float, float]:
    geom_type = int(mujoco.mjtObj.mjOBJ_GEOM)
    mask = np.isin(segmentation[..., 0], list(ids)) & (
        segmentation[..., 1] == geom_type
    )
    y, x = np.nonzero(mask)
    if x.size == 0:
        return 0, math.nan, math.nan
    return int(x.size), float(x.mean()), float(y.mean())


def mesh_geom_id(model: mujoco.MjModel, mesh_name: str) -> int:
    mesh_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_MESH, mesh_name)
    matches = np.flatnonzero(
        (model.geom_type == int(mujoco.mjtGeom.mjGEOM_MESH))
        & (model.geom_dataid == mesh_id)
    )
    if matches.size != 1:
        raise RuntimeError(
            f"Expected one geom for mesh {mesh_name!r}, found {matches.tolist()}"
        )
    return int(matches[0])


def d405_green_clearance_mm(model: mujoco.MjModel, data: mujoco.MjData) -> float:
    green_id = mesh_geom_id(model, "pla7_green")
    d405_id = mujoco.mj_name2id(
        model, mujoco.mjtObj.mjOBJ_GEOM, "d405_collision_envelope"
    )
    fromto = np.zeros(6, dtype=np.float64)
    distance = mujoco.mj_geomDistance(
        model, data, green_id, d405_id, 1.0, fromto
    )
    return float(distance * 1000.0)


def depth_visualization(depth_m: np.ndarray) -> np.ndarray:
    """Colorize the near manipulation volume over 0.04–0.15 m."""
    valid = np.isfinite(depth_m) & (depth_m > 0.0)
    normalized = np.clip((depth_m - 0.04) / (0.15 - 0.04), 0.0, 1.0)
    red = 255.0 * (1.0 - normalized)
    green = 255.0 * (1.0 - np.abs(2.0 * normalized - 1.0))
    blue = 255.0 * normalized
    rgb = np.stack([red, green, blue], axis=-1).astype(np.uint8)
    rgb[~valid] = 0
    return rgb


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    bundles = {}
    for angle in ANGLES_DEG:
        model, camera_name, side_camera_name, tray_names = build_model(angle)
        solver = IKSolver(model)
        solver.set_q(np.zeros(6))
        first_person_option = mujoco.MjvOption()
        # The box is a collision/third-person proxy.  Hide it from the pinhole
        # view because the real lens is 3.7 mm behind an optical opening rather
        # than embedded in an opaque box.
        first_person_option.geomgroup[4] = 0
        first_person_option.geomgroup[5] = 0
        side_option = mujoco.MjvOption()
        side_option.geomgroup[4] = 1
        side_option.geomgroup[5] = 0
        bundles[angle] = {
            "model": model,
            "camera": camera_name,
            "side_camera": side_camera_name,
            "tray_names": tray_names,
            "solver": solver,
            "renderer": mujoco.Renderer(
                model, height=RENDER_HEIGHT, width=RENDER_WIDTH
            ),
            "first_person_option": first_person_option,
            "side_option": side_option,
            "clearance_mm": d405_green_clearance_mm(model, solver.data),
        }

    # Added mount and housing geoms do not change the robot kinematics, so one
    # set of IK solutions is reused across all angle-specific models.
    reference_solver = bundles[ANGLES_DEG[0]]["solver"]
    q = np.zeros(6)
    solutions = []
    for stage, target in STAGES:
        q, pos_error, rot_error = reference_solver.solve(target, q)
        if pos_error > 0.006 or rot_error > 0.06:
            raise RuntimeError(
                f"IK failed for {stage}: position={pos_error:.4f}m rotation={rot_error:.4f}rad"
            )
        solutions.append((stage, q.copy(), pos_error, rot_error))

    rows = []
    tiles = []
    try:
        for stage, q, pos_error, rot_error in solutions:
            row_tiles = []
            for angle in ANGLES_DEG:
                bundle = bundles[angle]
                model = bundle["model"]
                solver = bundle["solver"]
                renderer = bundle["renderer"]
                solver.set_q(q)
                blue_ids = geom_ids(model, ["blue_block_geom"])
                tray_ids = geom_ids(model, bundle["tray_names"])
                left_ids = body_geom_ids(model, "gripper_left")
                right_ids = body_geom_ids(model, "gripper_right")
                renderer.disable_segmentation_rendering()
                renderer.update_scene(
                    solver.data,
                    camera=bundle["camera"],
                    scene_option=bundle["first_person_option"],
                )
                rgb = renderer.render().copy()
                renderer.enable_segmentation_rendering()
                renderer.update_scene(
                    solver.data,
                    camera=bundle["camera"],
                    scene_option=bundle["first_person_option"],
                )
                seg = renderer.render().copy()
                blue_px, blue_cx, blue_cy = segmentation_stats(seg, blue_ids)
                tray_px, tray_cx, tray_cy = segmentation_stats(seg, tray_ids)
                left_px, left_cx, left_cy = segmentation_stats(seg, left_ids)
                right_px, right_cx, right_cy = segmentation_stats(seg, right_ids)
                counts = {
                    "blue_px": blue_px,
                    "blue_cx": blue_cx,
                    "blue_cy": blue_cy,
                    "tray_px": tray_px,
                    "tray_cx": tray_cx,
                    "tray_cy": tray_cy,
                    "left_finger_px": left_px,
                    "left_finger_cx": left_cx,
                    "left_finger_cy": left_cy,
                    "right_finger_px": right_px,
                    "right_finger_cx": right_cx,
                    "right_finger_cy": right_cy,
                }
                rows.append(
                    {
                        "stage": stage,
                        "angle_deg": angle,
                        "d405_green_clearance_mm": bundle["clearance_mm"],
                        "ik_position_error_mm": pos_error * 1000.0,
                        "ik_rotation_error_deg": math.degrees(rot_error),
                        **counts,
                    }
                )
                tile = Image.fromarray(rgb).resize((424, 240))
                draw = ImageDraw.Draw(tile)
                draw.line((212, 38, 212, 240), fill=(255, 80, 80), width=1)
                draw.line((0, 120, 424, 120), fill=(255, 80, 80), width=1)
                label = (
                    f"{stage} | {angle:g} deg\n"
                    f"blue {counts['blue_px']}  tray {counts['tray_px']}  "
                    f"fingers {counts['left_finger_px']}/{counts['right_finger_px']}"
                )
                draw.rectangle((0, 0, 424, 38), fill=(0, 0, 0))
                draw.text((7, 4), label, fill=(255, 255, 255), font=ImageFont.load_default())
                row_tiles.append(tile)
            tiles.append(row_tiles)
    finally:
        for bundle in bundles.values():
            bundle["renderer"].disable_segmentation_rendering()

    comparison = Image.new("RGB", (424 * len(ANGLES_DEG), 240 * len(STAGES)), "white")
    for row_index, row_tiles in enumerate(tiles):
        for col_index, tile in enumerate(row_tiles):
            comparison.paste(tile, (424 * col_index, 240 * row_index))
    image_path = args.output_dir / "wrist_rgb_factory_calibrated_comparison.png"
    comparison.save(image_path)

    # Controlled before/after visual: the same MuJoCo grasp pose, rendered as
    # synthetic RGB and metric depth for the stock 15° and corrected 30° mount.
    # This is intentionally labelled synthetic because no old-mount raw depth
    # capture exists under matched physical conditions.
    rgb_depth_tiles: list[tuple[Image.Image, Image.Image, str, str]] = []
    compare_q = next(q for stage, q, _, _ in solutions if stage == "grasp")
    for angle, label in ((15.0, "Stock 15 deg"), (30.0, "Redesigned 30 deg")):
        bundle = bundles[angle]
        bundle["solver"].set_q(compare_q)
        renderer = bundle["renderer"]
        renderer.disable_segmentation_rendering()
        renderer.update_scene(
            bundle["solver"].data,
            camera=bundle["camera"],
            scene_option=bundle["first_person_option"],
        )
        rgb = renderer.render().copy()
        renderer.enable_depth_rendering()
        renderer.update_scene(
            bundle["solver"].data,
            camera=bundle["camera"],
            scene_option=bundle["first_person_option"],
        )
        depth = renderer.render().copy()
        renderer.disable_depth_rendering()
        valid_depth = depth[np.isfinite(depth) & (depth > 0.0)]
        depth_stats = (
            f"min={valid_depth.min():.3f}m "
            f"median={np.median(valid_depth):.3f}m"
        )
        rgb_depth_tiles.append(
            (
                Image.fromarray(rgb),
                Image.fromarray(depth_visualization(depth)),
                label,
                depth_stats,
            )
        )

    rgb_depth_comparison = Image.new("RGB", (1280, 960), "black")
    for column, (rgb_tile, depth_tile, label, depth_stats) in enumerate(
        rgb_depth_tiles
    ):
        x = column * 640
        rgb_depth_comparison.paste(rgb_tile, (x, 0))
        rgb_depth_comparison.paste(depth_tile, (x, 480))
        draw = ImageDraw.Draw(rgb_depth_comparison)
        draw.rectangle((x, 0, x + 640, 30), fill=(0, 0, 0))
        draw.text(
            (x + 8, 7),
            f"MuJoCo synthetic RGB | {label} | same grasp pose",
            fill=(255, 255, 255),
            font=ImageFont.load_default(),
        )
        draw.rectangle((x, 480, x + 640, 510), fill=(0, 0, 0))
        draw.text(
            (x + 8, 487),
            f"MuJoCo synthetic depth | {label} | {depth_stats} | scale=0.04-0.15m; ideal near=0.07m",
            fill=(255, 255, 255),
            font=ImageFont.load_default(),
        )
    rgb_depth_path = (
        args.output_dir / "wrist_rgb_depth_stock15_vs_redesigned30.png"
    )
    rgb_depth_comparison.save(rgb_depth_path)

    # External side view with the actual mount mesh and complete D405 envelope
    # visible.  This is the geometry sanity check that the earlier simulation
    # lacked.
    side_tiles = []
    debug_q = next(q for stage, q, _, _ in solutions if stage == "grasp")
    for angle in ANGLES_DEG:
        bundle = bundles[angle]
        bundle["solver"].set_q(debug_q)
        renderer = bundle["renderer"]
        renderer.update_scene(
            bundle["solver"].data,
            camera=bundle["side_camera"],
            scene_option=bundle["side_option"],
        )
        tile = Image.fromarray(renderer.render().copy()).resize((424, 320))
        draw = ImageDraw.Draw(tile)
        label = (
            f"{angle:g} deg | D405-green conservative clearance "
            f"{bundle['clearance_mm']:.1f} mm"
        )
        draw.rectangle((0, 0, 424, 24), fill=(0, 0, 0))
        draw.text((7, 5), label, fill=(255, 255, 255), font=ImageFont.load_default())
        side_tiles.append(tile)
    side_comparison = Image.new("RGB", (424 * len(side_tiles), 320), "white")
    for index, tile in enumerate(side_tiles):
        side_comparison.paste(tile, (424 * index, 0))
    side_path = args.output_dir / "wrist_mount_assembly_side_comparison.png"
    side_comparison.save(side_path)

    csv_path = args.output_dir / "wrist_rgb_factory_calibrated_metrics.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    for bundle in bundles.values():
        bundle["renderer"].close()

    print(
        f"PASS rendered={len(rows)} views image={image_path} "
        f"rgb_depth={rgb_depth_path} side={side_path} metrics={csv_path}"
    )
    print(
        "D405-to-green conservative clearances: "
        + ", ".join(
            f"{angle:g}deg={bundles[angle]['clearance_mm']:.2f}mm"
            for angle in ANGLES_DEG
        )
    )
    for row in rows:
        print(
            f"{row['stage']:10s} {row['angle_deg']:>4g}deg "
            f"blue={row['blue_px']:6d} tray={row['tray_px']:6d} "
            f"fingers={row['left_finger_px']:5d}/{row['right_finger_px']:5d}"
        )


if __name__ == "__main__":
    main()
