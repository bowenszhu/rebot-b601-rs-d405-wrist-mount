#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Capture one warmed-up, aligned D405 RGB-D frameset without robot I/O."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import pyrealsense2 as rs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True, help="D405 serial number")
    parser.add_argument("--output-dir", type=Path, default=Path("capture-output"))
    parser.add_argument("--warmup-frames", type=int, default=120)
    parser.add_argument("--visual-near-m", type=float, default=0.04)
    parser.add_argument("--visual-far-m", type=float, default=0.50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.warmup_frames < 1:
        raise ValueError("--warmup-frames must be positive")
    if not 0 < args.visual_near_m < args.visual_far_m:
        raise ValueError("expected 0 < --visual-near-m < --visual-far-m")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_device(args.serial)
    config.enable_stream(rs.stream.color, 640, 480, rs.format.rgb8, 30)
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    profile = pipeline.start(config)
    align = rs.align(rs.stream.color)
    try:
        frames = None
        for _ in range(args.warmup_frames):
            frames = align.process(pipeline.wait_for_frames(3000))
        if frames is None:
            raise RuntimeError("No synchronized RGB-D frames received")

        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()
        if not color_frame or not depth_frame:
            raise RuntimeError("Final frameset is missing RGB or depth")

        rgb = np.asanyarray(color_frame.get_data())
        depth = np.asanyarray(depth_frame.get_data())
        depth_scale = profile.get_device().first_depth_sensor().get_depth_scale()
        valid = depth > 0
        depth_m = depth.astype(np.float32) * depth_scale
        normalized = np.clip(
            (depth_m - args.visual_near_m)
            / (args.visual_far_m - args.visual_near_m),
            0.0,
            1.0,
        )
        depth_u8 = np.round((1.0 - normalized) * 255.0).astype(np.uint8)
        depth_colorized = cv2.applyColorMap(depth_u8, cv2.COLORMAP_TURBO)
        depth_colorized[~valid] = 0

        cv2.imwrite(
            str(args.output_dir / "d405-rgb.png"),
            cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
        )
        cv2.imwrite(str(args.output_dir / "d405-depth-u16.png"), depth)
        cv2.imwrite(
            str(args.output_dir / "d405-depth-colorized.png"),
            depth_colorized,
        )

        intrinsics = color_frame.profile.as_video_stream_profile().intrinsics
        metadata = {
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "serial_number": args.serial,
            "warmup_frames": args.warmup_frames,
            "rgb_shape": list(rgb.shape),
            "depth_shape": list(depth.shape),
            "depth_dtype": str(depth.dtype),
            "depth_scale_m_per_unit": depth_scale,
            "valid_depth_fraction": float(valid.mean()),
            "depth_visualization_range_m": [
                args.visual_near_m,
                args.visual_far_m,
            ],
            "rgb_intrinsics": {
                "fx": intrinsics.fx,
                "fy": intrinsics.fy,
                "ppx": intrinsics.ppx,
                "ppy": intrinsics.ppy,
                "distortion_model": str(intrinsics.model),
                "coeffs": list(intrinsics.coeffs),
            },
        }
        (args.output_dir / "d405-capture.json").write_text(
            json.dumps(metadata, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(metadata, indent=2))
    finally:
        pipeline.stop()


if __name__ == "__main__":
    main()
