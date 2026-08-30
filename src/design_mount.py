#!/usr/bin/env python3
# SPDX-License-Identifier: CERN-OHL-W-2.0
"""Generate fixed-down-angle D405 mounts for the reBot B601 wrist.

Both the green-bracket interface and the complete D405 cradle are retained
from Seeed's official ``D405_305_Mount.step``. The complete cradle is moved as
one rigid body, so its side/top wrap, bottom shelf, backplate, and screw holes
always share the same lateral shift and pitch. A thick lofted adapter reconnects
the transformed cradle to the stock wrist interface.

Coordinate convention inherited from the Seeed STEP (millimetres):
  * X: left/right across the gripper
  * Y: from the wrist toward the camera
  * Z: forward along the gripper

Positive pitch points the camera optical axis toward -Y (the tabletop).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cadquery as cq


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_STEP = (
    REPOSITORY_ROOT
    / "hardware/vendor/seeed-rebot-devarm"
    / "D405_305_Mount.step"
)
OUTPUT_DIR = REPOSITORY_ROOT / "build"

# Overlapping cuts create a strong lap-jointed transition. The base retains
# official material through Y=42, the transformed cradle retains official
# material down to Y=38, and one complete loft runs from the Y=39 stock
# cross-section to that same section after the cradle rigid transform. Using
# one closed profile for the whole transition fills the formerly visible side
# notch while retaining substantial overlap with both original-derived solids.
BASE_KEEP_Y = 42.0
CRADLE_KEEP_Y = 38.0
CONNECTOR_BASE_SECTION_Y = 39.0
CONNECTOR_CRADLE_SECTION_Y = 39.0
BASE_HOLE_X = (-11.208, 10.792)
BASE_HOLE_Y = 29.999
BASE_HOLE_DIAMETER = 2.7

# D405 geometry and rear threaded-hole pattern. The conservative collision
# envelope uses the official 42 x 42 x 23 mm overall dimensions. A 4.5 mm
# corner radius models the rounded aluminium housing for assembly inspection;
# collision tests additionally use the full sharp-corner box.
D405_WIDTH = 42.0
D405_HEIGHT = 42.0
D405_DEPTH = 23.0
D405_CORNER_RADIUS = 4.5
D405_HALF_HEIGHT = D405_HEIGHT / 2.0
CAMERA_HOLE_SPACING = 20.0
# RealSense's mechanical drawing centres the two M3 holes on the 42 mm D405
# body.  The pinned Seeed STEP instead centres the pair 1.000 mm to +X of its
# own 46 mm cradle envelope.  Keep the source datum explicit so the inherited
# holes can be filled before cutting the corrected pattern.
OFFICIAL_CRADLE_CENTER_X = 0.0014555241296942967
SEEED_CAMERA_HOLE_PATTERN_CENTER_X = OFFICIAL_CRADLE_CENTER_X + 1.0
SEEED_CAMERA_HOLE_PATTERN_OFFSET_X = (
    SEEED_CAMERA_HOLE_PATTERN_CENTER_X - OFFICIAL_CRADLE_CENTER_X
)
CAMERA_HOLE_PATTERN_CORRECTION_X = -SEEED_CAMERA_HOLE_PATTERN_OFFSET_X
SEEED_CAMERA_THROUGH_DIAMETER = 3.2
SEEED_CAMERA_COUNTERBORE_DIAMETER = 5.6
# Seeed's source STEP uses 3.2 mm through holes and 5.6 mm counterbores.
# Slightly larger print clearances tolerate MJF/SLS shrink and positional error
# while preserving the exact 20 mm nominal axes.
PRINT_CAMERA_THROUGH_DIAMETER = 3.6
PRINT_CAMERA_COUNTERBORE_DIAMETER = 6.0
PRINT_CAMERA_THROUGH_START = -4.1
PRINT_CAMERA_THROUGH_END = 0.1
PRINT_CAMERA_COUNTERBORE_START = -7.1
PRINT_CAMERA_COUNTERBORE_END = -3.9

# The 9 mm optical-centering shift exposes one stock-base corner in top view.
# Trim only the non-interface transition zone, then round the two new vertical
# edges so it cannot become a cable/hand snag. Both B601 screw axes lie well
# outside this cutter.
TIP_RELIEF_X = 17.5
TIP_RELIEF_Y_MIN = 36.0
TIP_RELIEF_Y_MAX = 48.0
TIP_RELIEF_RADIUS = 0.5

# The stock mount's front contact-plane hole centre and 15-degree hole axis
# were measured directly from the Seeed STEP. Rotating the camera about the
# stock housing's lower rear edge preserves a meaningful mechanical datum.
OFFICIAL_ANGLE_DEG = 15.0
OFFICIAL_SCREW_CENTER_Y = 68.9724
OFFICIAL_SCREW_CENTER_Z = -10.6118

# D405 RGB/depth coordinates are referenced to the left imager, which is on
# the observer's right when looking into the camera front. With the Seeed
# cradle's original handedness preserved, that is +X in this CAD frame, 9 mm
# from the housing centre. Shift the complete camera -9 mm so that the optical
# origin, rather than the aluminium housing centre, lies on the gripper
# centreline.
D405_LEFT_IMAGER_OFFSET_X = 9.0
OPTICAL_CENTERING_SHIFT_X = -D405_LEFT_IMAGER_OFFSET_X
CAMERA_PATTERN_CENTER_X = OFFICIAL_CRADLE_CENTER_X + OPTICAL_CENTERING_SHIFT_X

# At larger pitch the front/lower D405 corner would swing toward the green
# bracket. Raising the lower-rear rotation datum by 6 mm makes the 30-degree
# front/lower corner nearly coincide with the stock 15-degree corner. The
# MuJoCo green-part distance is checked independently after export.
CAMERA_LIFT_MM = 6.0

# The physical Seeed mount that was previously printed and successfully used is
# the handedness reference. Its cradle already exposes the D405 USB-C connector
# on the correct side. Do not infer handedness from a CAD viewer's default
# front/back view and do not mirror this asymmetric cradle.
CAMERA_CRADLE_MIRRORED = False
USB_OPENING_MATCHES_SEEED_REFERENCE = True



def scaled(vector: tuple[float, float, float], scale: float) -> cq.Vector:
    return cq.Vector(*(component * scale for component in vector))


def added(*vectors: cq.Vector) -> cq.Vector:
    result = cq.Vector(0.0, 0.0, 0.0)
    for vector in vectors:
        result = result.add(vector)
    return result


def orientation(
    angle_degrees: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    angle = math.radians(angle_degrees)
    # local +Y is camera-up; local +Z is optical-forward.
    up = (0.0, math.cos(angle), math.sin(angle))
    optical = (0.0, -math.sin(angle), math.cos(angle))
    return up, optical


def camera_frame(
    angle_degrees: float,
) -> tuple[cq.Vector, tuple[float, float, float], tuple[float, float, float]]:
    """Return D405 rear screw centre, camera-up, and optical-forward."""
    stock_up, _ = orientation(OFFICIAL_ANGLE_DEG)
    stock_center = cq.Vector(
        OFFICIAL_CRADLE_CENTER_X,
        OFFICIAL_SCREW_CENTER_Y,
        OFFICIAL_SCREW_CENTER_Z,
    )
    stock_lower_rear = added(stock_center, scaled(stock_up, -D405_HALF_HEIGHT))

    up, optical = orientation(angle_degrees)
    screw_center = added(
        cq.Vector(CAMERA_PATTERN_CENTER_X, stock_lower_rear.y, stock_lower_rear.z),
        scaled(up, D405_HALF_HEIGHT + CAMERA_LIFT_MM),
    )
    return screw_center, up, optical


def make_base(reference: cq.Shape) -> cq.Shape:
    """Retain only the official B601/green-bracket mating interface."""
    cutter = (
        cq.Workplane("XY")
        .box(120.0, BASE_KEEP_Y + 60.0, 120.0, centered=(True, False, True))
        .translate((0.0, -60.0, 0.0))
        .val()
    )
    base = reference.intersect(cutter)
    if len(base.Solids()) != 1 or not base.isValid():
        raise RuntimeError("Could not extract one valid official wrist interface")
    return base


def lower_y_cutter(y_limit: float) -> cq.Shape:
    return (
        cq.Workplane("XY")
        .box(120.0, y_limit + 60.0, 120.0, centered=(True, False, True))
        .translate((0.0, -60.0, 0.0))
        .val()
    )


def stock_to_target(shape: cq.Shape, angle_degrees: float) -> cq.Shape:
    """Rigidly move an official 15-degree cradle entity to the target pose."""
    stock_up, _ = orientation(OFFICIAL_ANGLE_DEG)
    target_up, _ = orientation(angle_degrees)
    stock_center = cq.Vector(
        OFFICIAL_CRADLE_CENTER_X,
        OFFICIAL_SCREW_CENTER_Y,
        OFFICIAL_SCREW_CENTER_Z,
    )
    stock_lower_rear = added(
        stock_center,
        scaled(stock_up, -D405_HALF_HEIGHT),
    )
    target_lower_rear = added(
        cq.Vector(
            stock_lower_rear.x + OPTICAL_CENTERING_SHIFT_X,
            stock_lower_rear.y,
            stock_lower_rear.z,
        ),
        scaled(target_up, CAMERA_LIFT_MM),
    )
    translation = target_lower_rear.sub(stock_lower_rear)
    return shape.rotate(
        stock_lower_rear,
        stock_lower_rear.add(cq.Vector(1.0, 0.0, 0.0)),
        angle_degrees - OFFICIAL_ANGLE_DEG,
    ).translate(translation)


def preserve_official_camera_cradle(shape: cq.Shape) -> cq.Shape:
    """Keep the successfully printed Seeed cradle's original handedness."""
    return shape


def fill_seeed_camera_hole_offset(shape: cq.Shape) -> tuple[cq.Shape, float]:
    """Fill Seeed's 1 mm-offset M3 passages before cutting centred holes."""
    _stock_up, stock_optical = orientation(OFFICIAL_ANGLE_DEG)
    optical_vector = cq.Vector(*stock_optical)
    filled = shape
    for local_x in (-CAMERA_HOLE_SPACING / 2.0, CAMERA_HOLE_SPACING / 2.0):
        center = cq.Vector(
            SEEED_CAMERA_HOLE_PATTERN_CENTER_X + local_x,
            OFFICIAL_SCREW_CENTER_Y,
            OFFICIAL_SCREW_CENTER_Z,
        )
        # The source counterbores span -7..-4 mm and the through holes span
        # -4..0 mm along the optical axis.  A 0.05 mm radial overlap makes the
        # repair boolean robust while the axial ends stay flush with the
        # original backplate surfaces.
        counterbore_fill = cq.Solid.makeCylinder(
            SEEED_CAMERA_COUNTERBORE_DIAMETER / 2.0 + 0.50,
            3.1,
            added(center, scaled(stock_optical, -7.0)),
            optical_vector,
        )
        through_fill = cq.Solid.makeCylinder(
            SEEED_CAMERA_THROUGH_DIAMETER / 2.0 + 0.50,
            4.1,
            added(center, scaled(stock_optical, -4.1)),
            optical_vector,
        )
        filled = filled.fuse(counterbore_fill, through_fill).clean()
    if len(filled.Solids()) != 1 or not filled.isValid():
        raise RuntimeError("Seeed camera-hole correction did not produce one valid solid")
    added_volume = filled.cut(shape).Volume()
    if not 150.0 <= added_volume <= 260.0:
        raise RuntimeError(
            "Unexpected Seeed camera-hole repair volume: "
            f"{added_volume:.3f} mm^3"
        )
    return filled, added_volume


def stock_cross_section_wire(reference: cq.Shape, y: float) -> cq.Wire:
    upper = reference.cut(lower_y_cutter(y))
    candidates = [face for face in upper.Faces() if abs(face.Center().y - y) < 0.05]
    if len(candidates) != 1 or len(candidates[0].Wires()) != 1:
        raise RuntimeError(f"Could not isolate official cradle section at Y={y:g}")
    return candidates[0].outerWire()


def make_tip_relief_cutter() -> cq.Shape:
    width = 100.0
    cutter_center_x = TIP_RELIEF_X + math.copysign(
        width / 2.0,
        TIP_RELIEF_X,
    )
    return (
        cq.Workplane("XY")
        .box(width, TIP_RELIEF_Y_MAX - TIP_RELIEF_Y_MIN, 100.0)
        .translate(
            (
                cutter_center_x,
                (TIP_RELIEF_Y_MIN + TIP_RELIEF_Y_MAX) / 2.0,
                0.0,
            )
        )
        .val()
    )


def apply_tip_relief(mount: cq.Shape) -> cq.Shape:
    relieved = mount.cut(make_tip_relief_cutter()).clean()
    fillet_edges = []
    for edge in relieved.Edges():
        bounds = edge.BoundingBox()
        lies_on_trim_plane = (
            abs(bounds.xmin - TIP_RELIEF_X) < 0.01
            and abs(bounds.xmax - TIP_RELIEF_X) < 0.01
        )
        is_vertical_trim_end = (
            abs(bounds.ymax - bounds.ymin) < 0.01 and edge.Length() > 10.0
        )
        if lies_on_trim_plane and is_vertical_trim_end:
            fillet_edges.append(edge)
    if len(fillet_edges) != 2:
        raise RuntimeError(
            f"Expected two exposed tip-relief edges, found {len(fillet_edges)}"
        )
    rounded = (
        cq.Workplane(obj=relieved)
        .newObject(fillet_edges)
        .fillet(TIP_RELIEF_RADIUS)
        .val()
        .clean()
    )
    if len(rounded.Solids()) != 1 or not rounded.isValid():
        raise RuntimeError("Tip-relieved mount is not one valid solid")
    return rounded


def open_camera_print_clearances(
    mount: cq.Shape,
    screw_center: cq.Vector,
    optical: tuple[float, float, float],
) -> cq.Shape:
    optical_vector = cq.Vector(*optical)
    opened = mount
    for local_x in (-CAMERA_HOLE_SPACING / 2.0, CAMERA_HOLE_SPACING / 2.0):
        center = added(screw_center, cq.Vector(local_x, 0.0, 0.0))
        through = cq.Solid.makeCylinder(
            PRINT_CAMERA_THROUGH_DIAMETER / 2.0,
            PRINT_CAMERA_THROUGH_END - PRINT_CAMERA_THROUGH_START,
            added(center, scaled(optical, PRINT_CAMERA_THROUGH_START)),
            optical_vector,
        )
        counterbore = cq.Solid.makeCylinder(
            PRINT_CAMERA_COUNTERBORE_DIAMETER / 2.0,
            PRINT_CAMERA_COUNTERBORE_END - PRINT_CAMERA_COUNTERBORE_START,
            added(center, scaled(optical, PRINT_CAMERA_COUNTERBORE_START)),
            optical_vector,
        )
        opened = opened.cut(through, counterbore)
    opened = opened.clean()
    if len(opened.Solids()) != 1 or not opened.isValid():
        raise RuntimeError("Camera print-clearance operation made an invalid mount")
    return opened


def oriented_box(
    center: cq.Vector,
    up: tuple[float, float, float],
    optical: tuple[float, float, float],
    width: float,
    height: float,
    depth: float,
) -> cq.Shape:
    plane = cq.Plane(
        origin=center,
        xDir=(1.0, 0.0, 0.0),
        normal=optical,
    )
    return cq.Workplane(plane).box(width, height, depth).val()


def round_outline_edges(
    shape: cq.Shape,
    optical: tuple[float, float, float],
    radius: float,
) -> cq.Shape:
    selector = cq.selectors.ParallelDirSelector(cq.Vector(*optical), 1e-5)
    rounded = cq.Workplane(obj=shape).edges(selector).fillet(radius).val()
    if not rounded.isValid():
        raise RuntimeError("Rounded rectangular prism is invalid")
    return rounded


def make_camera_envelopes(
    screw_center: cq.Vector,
    up: tuple[float, float, float],
    optical: tuple[float, float, float],
) -> tuple[cq.Shape, cq.Shape]:
    """Return conservative collision box and rounded visual D405 housing."""
    camera_center = added(screw_center, scaled(optical, D405_DEPTH / 2.0))
    conservative = oriented_box(
        camera_center,
        up,
        optical,
        D405_WIDTH,
        D405_HEIGHT,
        D405_DEPTH,
    )
    visual = round_outline_edges(conservative, optical, D405_CORNER_RADIUS)
    return conservative, visual


def make_mount(
    reference: cq.Shape,
    angle_degrees: float,
) -> tuple[cq.Shape, cq.Shape, dict[str, float]]:
    base = make_base(reference)
    seeed_stock_cradle = reference.cut(lower_y_cutter(CRADLE_KEEP_Y))
    stock_cradle = preserve_official_camera_cradle(seeed_stock_cradle)
    cradle_handedness_delta = (
        stock_cradle.cut(seeed_stock_cradle).Volume()
        + seeed_stock_cradle.cut(stock_cradle).Volume()
    )
    if cradle_handedness_delta > 0.01:
        raise RuntimeError(
            "Camera cradle handedness differs from the successfully printed "
            f"Seeed reference by {cradle_handedness_delta:.4f} mm^3"
        )
    corrected_stock_cradle, source_hole_fill_volume = (
        fill_seeed_camera_hole_offset(stock_cradle)
    )
    cradle = stock_to_target(corrected_stock_cradle, angle_degrees)
    uncorrected_cradle_for_fit = stock_to_target(stock_cradle, angle_degrees)
    base_wire = stock_cross_section_wire(reference, CONNECTOR_BASE_SECTION_Y)
    cradle_wire = stock_to_target(
        preserve_official_camera_cradle(
            stock_cross_section_wire(reference, CONNECTOR_CRADLE_SECTION_Y)
        ),
        angle_degrees,
    )
    connector = cq.Solid.makeLoft([base_wire, cradle_wire], True)
    if not connector.isValid() or len(connector.Solids()) != 1:
        raise RuntimeError("Original-profile transition adapter is invalid")

    tip_relief_cutter = make_tip_relief_cutter()
    base_load_path_overlap = (
        base.intersect(connector).cut(tip_relief_cutter).Volume()
    )
    cradle_load_path_overlap = (
        cradle.intersect(connector).cut(tip_relief_cutter).Volume()
    )
    if base_load_path_overlap < 100.0 or cradle_load_path_overlap < 100.0:
        raise RuntimeError(
            "Original-profile adapter load path is incomplete: "
            f"base={base_load_path_overlap:.2f}mm^3 "
            f"cradle={cradle_load_path_overlap:.2f}mm^3"
        )
    # Unify coincident seam faces before meshing. This preserves one B-rep
    # solid and prevents angle-specific open/non-manifold STL tessellation.
    mount = apply_tip_relief(base.fuse(connector, cradle).clean())
    if len(mount.Solids()) != 1 or not mount.isValid():
        raise RuntimeError(f"{angle_degrees:g} degree mount is not one valid solid")

    screw_center, up, optical = camera_frame(angle_degrees)
    mount = open_camera_print_clearances(mount, screw_center, optical)
    optical_vector = cq.Vector(*optical)
    for index, local_x in enumerate(
        (-CAMERA_HOLE_SPACING / 2.0, CAMERA_HOLE_SPACING / 2.0),
        start=1,
    ):
        center = added(screw_center, cq.Vector(local_x, 0.0, 0.0))
        passage = cq.Solid.makeCylinder(
            PRINT_CAMERA_THROUGH_DIAMETER / 2.0 - 0.05,
            12.0,
            added(center, scaled(optical, -8.0)),
            optical_vector,
        )
        obstruction = mount.intersect(passage).Volume()
        if obstruction > 0.02:
            raise RuntimeError(
                f"Camera screw passage {index} is obstructed by "
                f"{obstruction:.3f} mm^3"
            )
        counterbore_probe = cq.Solid.makeCylinder(
            PRINT_CAMERA_COUNTERBORE_DIAMETER / 2.0 - 0.05,
            PRINT_CAMERA_COUNTERBORE_END - PRINT_CAMERA_COUNTERBORE_START,
            added(center, scaled(optical, PRINT_CAMERA_COUNTERBORE_START)),
            optical_vector,
        )
        counterbore_obstruction = mount.intersect(counterbore_probe).Volume()
        if counterbore_obstruction > 0.02:
            raise RuntimeError(
                f"Camera counterbore {index} is obstructed by "
                f"{counterbore_obstruction:.3f} mm^3"
            )

    for index, x in enumerate(BASE_HOLE_X, start=1):
        probe = cq.Solid.makeCylinder(
            BASE_HOLE_DIAMETER / 2.0 - 0.10,
            30.0,
            cq.Vector(x, BASE_HOLE_Y, -25.0),
            cq.Vector(0.0, 0.0, 1.0),
        )
        obstruction = mount.intersect(probe).Volume()
        if obstruction > 0.01:
            raise RuntimeError(
                f"Official base hole {index} is obstructed by "
                f"{obstruction:.3f} mm^3"
            )

    _conservative, visual = make_camera_envelopes(screw_center, up, optical)
    stock_center = cq.Vector(
        OFFICIAL_CRADLE_CENTER_X,
        OFFICIAL_SCREW_CENTER_Y,
        OFFICIAL_SCREW_CENTER_Z,
    )
    stock_up, stock_optical = orientation(OFFICIAL_ANGLE_DEG)
    _stock_box, stock_visual = make_camera_envelopes(
        stock_center,
        stock_up,
        stock_optical,
    )
    official_overlap = reference.intersect(stock_visual).Volume()
    transformed_overlap = uncorrected_cradle_for_fit.intersect(visual).Volume()
    added_collision = base.fuse(connector).intersect(visual).Volume()
    if abs(transformed_overlap - official_overlap) > 0.05:
        raise RuntimeError(
            "Rigid cradle transform changed the official camera fit: "
            f"official={official_overlap:.3f}mm^3 "
            f"transformed={transformed_overlap:.3f}mm^3"
        )
    if added_collision > 0.05:
        raise RuntimeError(
            f"New base/adapter enters D405 envelope by {added_collision:.3f} mm^3"
        )
    diagnostics = {
        "screw_center_x": screw_center.x,
        "screw_center_y": screw_center.y,
        "screw_center_z": screw_center.z,
        "back_gap": 0.0,
        "bottom_gap": 0.0,
        "official_camera_overlap": official_overlap,
        "transformed_camera_overlap": transformed_overlap,
        "added_collision_volume": added_collision,
        "base_load_path_overlap": base_load_path_overlap,
        "cradle_load_path_overlap": cradle_load_path_overlap,
        "lateral_shift": OPTICAL_CENTERING_SHIFT_X,
        "left_imager_x": screw_center.x + D405_LEFT_IMAGER_OFFSET_X,
        "source_cradle_center_x": OFFICIAL_CRADLE_CENTER_X,
        "seeed_hole_pattern_center_x": SEEED_CAMERA_HOLE_PATTERN_CENTER_X,
        "seeed_hole_pattern_offset_x": SEEED_CAMERA_HOLE_PATTERN_OFFSET_X,
        "hole_pattern_correction_x": CAMERA_HOLE_PATTERN_CORRECTION_X,
        "source_hole_fill_volume": source_hole_fill_volume,
        "camera_through_diameter": PRINT_CAMERA_THROUGH_DIAMETER,
        "camera_counterbore_diameter": PRINT_CAMERA_COUNTERBORE_DIAMETER,
        "tip_relief_x": TIP_RELIEF_X,
        "tip_relief_radius": TIP_RELIEF_RADIUS,
        "camera_cradle_mirrored": float(CAMERA_CRADLE_MIRRORED),
        "cradle_vs_seeed_symmetric_difference": cradle_handedness_delta,
        "usb_opening_matches_seeed_reference": float(
            USB_OPENING_MATCHES_SEEED_REFERENCE
        ),
    }
    diagnostics["mount_solids"] = float(len(mount.Solids()))
    return mount, visual, diagnostics


def export_and_recheck(
    shape: cq.Shape,
    stem: str,
    output_dir: Path,
) -> tuple[Path, Path]:
    step_path = output_dir / f"{stem}.step"
    stl_path = output_dir / f"{stem}.stl"
    cq.exporters.export(shape, str(step_path))
    cq.exporters.export(shape, str(stl_path), tolerance=0.02, angularTolerance=0.1)

    reloaded = cq.importers.importStep(str(step_path)).val()
    if len(reloaded.Solids()) != 1 or not reloaded.isValid():
        raise RuntimeError(f"Exported STEP failed round-trip validation: {step_path}")
    relative_volume_error = abs(reloaded.Volume() - shape.Volume()) / shape.Volume()
    if relative_volume_error > 1e-6:
        raise RuntimeError(f"STEP round-trip volume error is {relative_volume_error:.3e}")
    return step_path, stl_path


def export_debug_assembly(
    mount: cq.Shape,
    camera_visual: cq.Shape,
    stem: str,
    output_dir: Path,
) -> tuple[Path, Path]:
    camera_path = output_dir / f"{stem}_d405_proxy.stl"
    assembly_path = output_dir / f"{stem}_assembly_debug.step"
    cq.exporters.export(
        camera_visual,
        str(camera_path),
        tolerance=0.02,
        angularTolerance=0.1,
    )
    assembly = cq.Compound.makeCompound([mount, camera_visual])
    cq.exporters.export(assembly, str(assembly_path))
    return camera_path, assembly_path


def export_geometry_metadata(
    angle_degrees: float,
    diagnostics: dict[str, float],
    stem: str,
    output_dir: Path,
) -> Path:
    screw_center, up, optical = camera_frame(angle_degrees)
    metadata_path = output_dir / f"{stem}_geometry.json"
    metadata_path.write_text(
        json.dumps(
            {
                "angle_deg": angle_degrees,
                "screw_center_mm": [
                    screw_center.x,
                    screw_center.y,
                    screw_center.z,
                ],
                "camera_up": list(up),
                "optical_forward": list(optical),
                "d405_dimensions_mm": [D405_WIDTH, D405_HEIGHT, D405_DEPTH],
                "d405_corner_radius_mm": D405_CORNER_RADIUS,
                "camera_hole_spacing_mm": CAMERA_HOLE_SPACING,
                "camera_lateral_shift_mm": diagnostics["lateral_shift"],
                "left_imager_x_mm": diagnostics["left_imager_x"],
                "source_cradle_center_x_mm": diagnostics[
                    "source_cradle_center_x"
                ],
                "seeed_camera_hole_pattern_center_x_mm": diagnostics[
                    "seeed_hole_pattern_center_x"
                ],
                "seeed_camera_hole_pattern_offset_x_mm": diagnostics[
                    "seeed_hole_pattern_offset_x"
                ],
                "camera_hole_pattern_correction_x_mm": diagnostics[
                    "hole_pattern_correction_x"
                ],
                "source_hole_fill_volume_mm3": diagnostics[
                    "source_hole_fill_volume"
                ],
                "camera_through_clearance_diameter_mm": diagnostics[
                    "camera_through_diameter"
                ],
                "camera_counterbore_diameter_mm": diagnostics[
                    "camera_counterbore_diameter"
                ],
                "tip_relief_x_mm": diagnostics["tip_relief_x"],
                "tip_relief_radius_mm": diagnostics["tip_relief_radius"],
                "camera_cradle_mirrored": bool(
                    diagnostics["camera_cradle_mirrored"]
                ),
                "cradle_vs_seeed_symmetric_difference_mm3": diagnostics[
                    "cradle_vs_seeed_symmetric_difference"
                ],
                "usb_opening_matches_seeed_reference": bool(
                    diagnostics["usb_opening_matches_seeed_reference"]
                ),
                "transition_gap_filled": (
                    CONNECTOR_BASE_SECTION_Y == CONNECTOR_CRADLE_SECTION_Y
                ),
                "camera_back_gap_mm": diagnostics["back_gap"],
                "bottom_ledge_gap_mm": diagnostics["bottom_gap"],
                "official_cradle_camera_overlap_mm3": diagnostics[
                    "official_camera_overlap"
                ],
                "transformed_cradle_camera_overlap_mm3": diagnostics[
                    "transformed_camera_overlap"
                ],
                "new_adapter_camera_collision_volume_mm3": diagnostics[
                    "added_collision_volume"
                ],
                "adapter_to_base_overlap_mm3": diagnostics[
                    "base_load_path_overlap"
                ],
                "adapter_to_cradle_overlap_mm3": diagnostics[
                    "cradle_load_path_overlap"
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return metadata_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--angles",
        type=float,
        nargs="+",
        default=(30.0,),
        help="fixed downward camera angles in degrees",
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    if not REFERENCE_STEP.exists():
        raise FileNotFoundError(f"Missing official Seeed reference: {REFERENCE_STEP}")
    reference = cq.importers.importStep(str(REFERENCE_STEP)).val()
    if len(reference.Solids()) != 1 or not reference.isValid():
        raise RuntimeError("Official Seeed reference is not one valid solid")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for angle in args.angles:
        if not 20.0 <= angle <= 50.0:
            raise ValueError("Supported fixed angles are 20 to 50 degrees")
        mount, camera_visual, diagnostics = make_mount(reference, angle)
        stem = f"rebot_b601_d405_down_{angle:g}deg".replace(".", "p")
        step_path, stl_path = export_and_recheck(mount, stem, args.output_dir)
        camera_path, assembly_path = export_debug_assembly(
            mount,
            camera_visual,
            stem,
            args.output_dir,
        )
        metadata_path = export_geometry_metadata(
            angle,
            diagnostics,
            stem,
            args.output_dir,
        )
        # Report the manufacturing STEP after the export/re-import check.  The
        # pre-export compound can retain intermediate bounding information even
        # though Open CASCADE writes the correct single-solid result.
        exported_mount = cq.importers.importStep(str(step_path)).val()
        bounds = exported_mount.BoundingBox()
        print(
            f"PASS angle={angle:g}deg solid=1 valid=True "
            f"added_collision={diagnostics['added_collision_volume']:.4f}mm^3 "
            f"official_fit_delta="
            f"{diagnostics['transformed_camera_overlap'] - diagnostics['official_camera_overlap']:+.4f}mm^3 "
            f"load_path=({diagnostics['base_load_path_overlap']:.1f},"
            f"{diagnostics['cradle_load_path_overlap']:.1f})mm^3 "
            f"camera_center=({diagnostics['screw_center_x']:.3f},"
            f"{diagnostics['screw_center_y']:.3f},"
            f"{diagnostics['screw_center_z']:.3f})mm "
            f"bbox={bounds.xlen:.2f}x{bounds.ylen:.2f}x{bounds.zlen:.2f}mm "
            f"volume={exported_mount.Volume():.1f}mm^3"
        )
        print(f"  STEP     {step_path}")
        print(f"  STL      {stl_path}")
        print(f"  D405     {camera_path}")
        print(f"  ASSEMBLY {assembly_path}")
        print(f"  GEOMETRY {metadata_path}")


if __name__ == "__main__":
    main()
