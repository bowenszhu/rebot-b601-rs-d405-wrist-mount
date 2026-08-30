#!/usr/bin/env python3
# SPDX-License-Identifier: CERN-OHL-W-2.0
"""Validate exported D405 mount STEP solids and STL meshes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cadquery as cq
import vtk


def validate_step(path: Path) -> tuple[int, bool, float]:
    shape = cq.importers.importStep(str(path)).val()
    return len(shape.Solids()), shape.isValid(), shape.Volume()


def camera_axis_xs(path: Path, radius: float) -> list[float]:
    """Return rear camera-hole cylinder X axes from an exported STEP."""
    shape = cq.importers.importStep(str(path)).val()
    axes = []
    for face in shape.Faces():
        if face.geomType() != "CYLINDER":
            continue
        cylinder = face._geomAdaptor().Cylinder()
        if abs(cylinder.Radius() - radius) > 1e-4:
            continue
        location = cylinder.Axis().Location()
        if location.Y() > 50.0:
            axes.append(float(location.X()))
    return sorted(axes)


def edge_count(mesh: vtk.vtkPolyData, *, boundary: bool, nonmanifold: bool) -> int:
    edges = vtk.vtkFeatureEdges()
    edges.SetInputData(mesh)
    edges.SetBoundaryEdges(boundary)
    edges.SetNonManifoldEdges(nonmanifold)
    edges.FeatureEdgesOff()
    edges.ManifoldEdgesOff()
    edges.Update()
    return edges.GetOutput().GetNumberOfCells()


def validate_stl(path: Path) -> tuple[int, int, int, int]:
    reader = vtk.vtkSTLReader()
    reader.SetFileName(str(path))
    reader.Update()
    mesh = reader.GetOutput()

    connectivity = vtk.vtkConnectivityFilter()
    connectivity.SetInputData(mesh)
    connectivity.SetExtractionModeToAllRegions()
    connectivity.Update()
    return (
        mesh.GetNumberOfCells(),
        edge_count(mesh, boundary=True, nonmanifold=False),
        edge_count(mesh, boundary=False, nonmanifold=True),
        connectivity.GetNumberOfExtractedRegions(),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "output_dir",
        type=Path,
        nargs="?",
        default=Path(__file__).resolve().parents[1] / "build",
    )
    parser.add_argument(
        "--angles",
        type=float,
        nargs="+",
        help="validate only these generated angle stems",
    )
    args = parser.parse_args()

    if args.angles:
        step_files = [
            args.output_dir
            / f"rebot_b601_d405_down_{angle:g}deg".replace(".", "p")
            for angle in args.angles
        ]
        step_files = [path.with_suffix(".step") for path in step_files]
    else:
        step_files = sorted(args.output_dir.glob("rebot_b601_d405_down_*deg.step"))
    if not step_files:
        raise FileNotFoundError(f"No generated STEP files in {args.output_dir}")

    all_passed = True
    for step_path in step_files:
        stl_path = step_path.with_suffix(".stl")
        proxy_path = step_path.with_name(step_path.stem + "_d405_proxy.stl")
        assembly_path = step_path.with_name(step_path.stem + "_assembly_debug.step")
        geometry_path = step_path.with_name(step_path.stem + "_geometry.json")
        if not stl_path.exists():
            raise FileNotFoundError(stl_path)
        for required in (proxy_path, assembly_path, geometry_path):
            if not required.exists():
                raise FileNotFoundError(required)
        solids, valid, volume = validate_step(step_path)
        triangles, boundary_edges, nonmanifold_edges, regions = validate_stl(stl_path)
        proxy_triangles, proxy_boundary, proxy_nonmanifold, proxy_regions = (
            validate_stl(proxy_path)
        )
        assembly_solids, assembly_valid, _assembly_volume = validate_step(
            assembly_path
        )
        geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
        official_overlap = float(geometry["official_cradle_camera_overlap_mm3"])
        transformed_overlap = float(
            geometry["transformed_cradle_camera_overlap_mm3"]
        )
        added_collision = float(
            geometry["new_adapter_camera_collision_volume_mm3"]
        )
        base_load_path = float(geometry["adapter_to_base_overlap_mm3"])
        plate_load_path = float(geometry["adapter_to_cradle_overlap_mm3"])
        lateral_shift = float(geometry["camera_lateral_shift_mm"])
        left_imager_x = float(geometry["left_imager_x_mm"])
        source_cradle_center_x = float(geometry["source_cradle_center_x_mm"])
        seeed_hole_offset_x = float(
            geometry["seeed_camera_hole_pattern_offset_x_mm"]
        )
        hole_correction_x = float(
            geometry["camera_hole_pattern_correction_x_mm"]
        )
        source_hole_fill_volume = float(
            geometry["source_hole_fill_volume_mm3"]
        )
        screw_center_x = float(geometry["screw_center_mm"][0])
        expected_axes = [
            screw_center_x - float(geometry["camera_hole_spacing_mm"]) / 2.0,
            screw_center_x + float(geometry["camera_hole_spacing_mm"]) / 2.0,
        ]
        through_axes = camera_axis_xs(
            step_path,
            float(geometry["camera_through_clearance_diameter_mm"]) / 2.0,
        )
        counterbore_axes = camera_axis_xs(
            step_path,
            float(geometry["camera_counterbore_diameter_mm"]) / 2.0,
        )
        corrected_axes_only = (
            len(through_axes) == 2
            and len(counterbore_axes) == 2
            and all(
                abs(observed - expected) <= 1e-6
                for observed, expected in zip(through_axes, expected_axes)
            )
            and all(
                abs(observed - expected) <= 1e-6
                for observed, expected in zip(counterbore_axes, expected_axes)
            )
        )
        through_diameter = float(
            geometry["camera_through_clearance_diameter_mm"]
        )
        counterbore_diameter = float(geometry["camera_counterbore_diameter_mm"])
        tip_radius = float(geometry["tip_relief_radius_mm"])
        camera_cradle_mirrored = bool(
            geometry["camera_cradle_mirrored"]
        )
        cradle_handedness_delta = float(
            geometry["cradle_vs_seeed_symmetric_difference_mm3"]
        )
        usb_opening_matches_seeed_reference = bool(
            geometry["usb_opening_matches_seeed_reference"]
        )
        transition_gap_filled = bool(geometry["transition_gap_filled"])
        passed = (
            solids == 1
            and valid
            and boundary_edges == 0
            and nonmanifold_edges == 0
            and regions == 1
            and proxy_boundary == 0
            and proxy_nonmanifold == 0
            and proxy_regions == 1
            and assembly_solids == 2
            and assembly_valid
            and abs(transformed_overlap - official_overlap) <= 0.05
            and added_collision <= 0.05
            and base_load_path >= 100.0
            and plate_load_path >= 250.0
            and abs(lateral_shift + 9.0) <= 1e-6
            and abs(left_imager_x - source_cradle_center_x) <= 1e-6
            and abs(seeed_hole_offset_x - 1.0) <= 1e-6
            and abs(hole_correction_x + 1.0) <= 1e-6
            and 150.0 <= source_hole_fill_volume <= 260.0
            and corrected_axes_only
            and through_diameter >= 3.6
            and counterbore_diameter >= 6.0
            and tip_radius >= 0.5
            and not camera_cradle_mirrored
            and cradle_handedness_delta <= 0.01
            and usb_opening_matches_seeed_reference
            and transition_gap_filled
        )
        print(
            f"{'PASS' if passed else 'FAIL'} {step_path.stem}: "
            f"STEP solids={solids} valid={valid} volume={volume:.1f}mm^3; "
            f"STL triangles={triangles} boundary={boundary_edges} "
            f"nonmanifold={nonmanifold_edges} regions={regions}; "
            f"D405 triangles={proxy_triangles} boundary={proxy_boundary} "
            f"nonmanifold={proxy_nonmanifold} regions={proxy_regions}; "
            f"assembly solids={assembly_solids} valid={assembly_valid}; "
            f"official_fit_delta={transformed_overlap - official_overlap:+.4f}mm^3 "
            f"added_collision={added_collision:.4f}mm^3; "
            f"load_path=({base_load_path:.1f},{plate_load_path:.1f})mm^3; "
            f"shift={lateral_shift:.1f}mm holes={through_diameter:.1f}/"
            f"{counterbore_diameter:.1f}mm tip_r={tip_radius:.1f}mm"
            f" source_hole_offset={seeed_hole_offset_x:+.1f}mm"
            f" correction={hole_correction_x:+.1f}mm"
            f" fill={source_hole_fill_volume:.1f}mm^3"
            f" corrected_axes_only={corrected_axes_only}"
            f" cradle_mirrored={camera_cradle_mirrored}"
            f" cradle_ref_delta={cradle_handedness_delta:.4f}mm^3"
            f" usb_matches_reference={usb_opening_matches_seeed_reference}"
            f" gap_filled={transition_gap_filled}"
        )
        all_passed = all_passed and passed
    if not all_passed:
        raise RuntimeError("One or more outputs failed validation")


if __name__ == "__main__":
    main()
