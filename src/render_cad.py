#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Render STEP/STL solids into a reproducible four-view PNG."""

from __future__ import annotations

import argparse
from pathlib import Path

import cadquery as cq
import vtk


VIEWS = (
    ("isometric", (1.0, -1.0, 0.8), (0.0, 0.0, 1.0)),
    ("front", (0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    ("side", (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    ("top", (0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
)


def load_shape(path: Path) -> cq.Shape:
    suffix = path.suffix.lower()
    if suffix in {".step", ".stp"}:
        return cq.importers.importStep(str(path)).val()
    raise ValueError(f"Only STEP input is supported, got: {path}")


def render(shape: cq.Shape, output: Path) -> None:
    temporary_stl = output.with_suffix(".render.stl")
    cq.exporters.export(shape, str(temporary_stl), tolerance=0.02, angularTolerance=0.1)

    bounds = shape.BoundingBox()
    center = (
        (bounds.xmin + bounds.xmax) / 2.0,
        (bounds.ymin + bounds.ymax) / 2.0,
        (bounds.zmin + bounds.zmax) / 2.0,
    )
    distance = max(bounds.xlen, bounds.ylen, bounds.zlen) * 2.4

    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetSize(1600, 1200)

    for index, (label, direction, view_up) in enumerate(VIEWS):
        reader = vtk.vtkSTLReader()
        reader.SetFileName(str(temporary_stl))
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(reader.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.78, 0.80, 0.84)
        actor.GetProperty().EdgeVisibilityOn()
        actor.GetProperty().SetEdgeColor(0.12, 0.12, 0.12)
        actor.GetProperty().SetLineWidth(1.0)

        renderer = vtk.vtkRenderer()
        col = index % 2
        row = 1 - index // 2
        renderer.SetViewport(col * 0.5, row * 0.5, (col + 1) * 0.5, (row + 1) * 0.5)
        renderer.SetBackground(0.97, 0.97, 0.97)
        renderer.AddActor(actor)

        camera = renderer.GetActiveCamera()
        camera.SetFocalPoint(*center)
        camera.SetPosition(
            center[0] + direction[0] * distance,
            center[1] + direction[1] * distance,
            center[2] + direction[2] * distance,
        )
        camera.SetViewUp(*view_up)
        camera.ParallelProjectionOn()
        renderer.ResetCamera()
        renderer.ResetCameraClippingRange()

        text = vtk.vtkTextActor()
        text.SetInput(label)
        text.SetPosition(18, 18)
        text.GetTextProperty().SetFontSize(26)
        text.GetTextProperty().SetColor(0.08, 0.08, 0.08)
        renderer.AddActor2D(text)
        window.AddRenderer(renderer)

    window.Render()
    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(window)
    capture.SetInputBufferTypeToRGB()
    capture.ReadFrontBufferOff()
    capture.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(output))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()
    temporary_stl.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    shape = load_shape(args.input)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise RuntimeError("Input must be one valid solid")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    render(shape, args.output)
    bounds = shape.BoundingBox()
    print(
        f"PASS solid=1 bbox={bounds.xlen:.3f}x{bounds.ylen:.3f}x{bounds.zlen:.3f}mm "
        f"output={args.output}"
    )


if __name__ == "__main__":
    main()
