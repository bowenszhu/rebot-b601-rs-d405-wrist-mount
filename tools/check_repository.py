#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fast, dependency-free integrity checks for the public repository."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_RELEASE_HASHES = {
    "hardware/release/rebot_b601_rs_d405_mount_30deg.step":
        "363c1e3f710760c0cd875668e1dd60884a66ba971799836d5476cf80ac8b4f50",
    "hardware/release/rebot_b601_rs_d405_mount_30deg.stl":
        "bf9ffe0eafc1c5f34afeac5485eced94ce3dc87977e3a995142e9cda287930d0",
    "hardware/release/rebot_b601_rs_d405_mount_30deg.geometry.json":
        "52606d9e267c3cf14d4a21f0ea51bb1cd08721ee84f32736ec62364912ff952b",
}
EXPECTED_CAMERA_HASHES = {
    "docs/assets/camera/d405-stock15-rgb.png":
        "4e33b896bbddda8feffaae3d20a5404d49cdafd18dd5382c95d12a74b8b48a92",
    "docs/assets/camera/d405-redesigned30-rgb.png":
        "a7580cecbb55d271d443de233310b65ba266fb66fb7abff70671871a6edb399f",
    "docs/assets/camera/d405-redesigned30-depth-u16.png":
        "1c01c2d4e6cc9f93710fe1bc8e2114177cf98a775d6806d168e34925e22b3aaf",
    "docs/assets/camera/d405-redesigned30-depth-colorized.png":
        "6edcba6bbd12313450800a6ab486394336d9364e57dbc7eb076523b64f6bfaf4",
    "docs/assets/camera/d405-physical-output-comparison.png":
        "1f5f5a3ec386a86e76f978a9aa404351f6230e68b59dcacbf4d4a0f24636f3d3",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_markdown_links(path: Path) -> list[str]:
    failures: list[str] = []
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        clean = target.split("#", 1)[0]
        if clean and not (path.parent / clean).resolve().exists():
            failures.append(f"{path.relative_to(ROOT)} -> {target}")
    return failures


def main() -> None:
    failures: list[str] = []
    for relative, expected in EXPECTED_RELEASE_HASHES.items():
        path = ROOT / relative
        if not path.exists():
            failures.append(f"missing {relative}")
        elif sha256(path) != expected:
            failures.append(f"hash mismatch {relative}")

    for relative, expected in EXPECTED_CAMERA_HASHES.items():
        path = ROOT / relative
        if not path.exists():
            failures.append(f"missing {relative}")
        elif sha256(path) != expected:
            failures.append(f"hash mismatch {relative}")

    raw_depth = ROOT / "docs/assets/camera/d405-redesigned30-depth-u16.png"
    raw_depth_header = raw_depth.read_bytes()[:26] if raw_depth.exists() else b""
    if (
        len(raw_depth_header) != 26
        or raw_depth_header[:8] != b"\x89PNG\r\n\x1a\n"
        or raw_depth_header[24] != 16
        or raw_depth_header[25] != 0
    ):
        failures.append("physical D405 raw depth is not a 16-bit grayscale PNG")

    physical_capture = json.loads(
        (ROOT / "data/physical_d405_capture_provenance.json").read_text(
            encoding="utf-8"
        )
    )
    if physical_capture["stock_15deg"]["depth_recorded"] is not False:
        failures.append("historical stock capture must not claim recorded depth")
    if float(physical_capture["redesigned_30deg"]["valid_depth_fraction"]) < 0.70:
        failures.append("redesigned physical depth valid fraction is unexpectedly low")
    stock_rgb = physical_capture["stock_15deg"]["published_rgb"]
    if sha256(ROOT / stock_rgb) != physical_capture["stock_15deg"]["published_rgb_sha256"]:
        failures.append(f"physical capture provenance mismatch: {stock_rgb}")
    for key, hash_key in (
        ("published_rgb", "published_rgb_sha256"),
        ("published_depth_u16", "published_depth_u16_sha256"),
        ("published_depth_colorized", "published_depth_colorized_sha256"),
    ):
        relative = physical_capture["redesigned_30deg"][key]
        expected = physical_capture["redesigned_30deg"][hash_key]
        if sha256(ROOT / relative) != expected:
            failures.append(f"physical capture provenance mismatch: {relative}")

    alignment = json.loads(
        (ROOT / "data/seeed_source_hole_alignment.json").read_text(
            encoding="utf-8"
        )
    )
    if abs(float(alignment["through_hole_spacing_mm"]) - 20.0) > 1e-6:
        failures.append("unexpected Seeed source through-hole spacing")
    if abs(float(alignment["pair_offset_from_cradle_center_x_mm"]) - 1.0) > 1e-6:
        failures.append("unexpected Seeed source +1 mm hole-pair offset")
    if abs(float(alignment["required_correction_x_mm"]) + 1.0) > 1e-6:
        failures.append("unexpected current -1 mm hole correction")

    current_geometry = json.loads(
        (
            ROOT
            / "hardware/release/rebot_b601_rs_d405_mount_30deg.geometry.json"
        ).read_text(encoding="utf-8")
    )
    if (
        abs(float(current_geometry["camera_hole_pattern_correction_x_mm"]) + 1.0)
        > 1e-6
    ):
        failures.append("current geometry metadata lacks the -1 mm correction")

    photos = sorted((ROOT / "docs/assets/photos").glob("*"))
    if len(photos) != 16:
        failures.append(f"expected 16 public photos, found {len(photos)}")
    for photo in photos:
        if photo.suffix.lower() != ".png" or "privacy-blurred" not in photo.name:
            failures.append(f"unexpected public photo asset: {photo.name}")

    for path in ROOT.rglob("*.md"):
        failures.extend(check_markdown_links(path))

    if failures:
        raise SystemExit("FAIL\n" + "\n".join(f"- {item}" for item in failures))
    print(
        "PASS release and physical-camera hashes, 16-bit raw depth, "
        "+1/-1 mm hole correction, 16 photographs, and local Markdown links"
    )


if __name__ == "__main__":
    main()
