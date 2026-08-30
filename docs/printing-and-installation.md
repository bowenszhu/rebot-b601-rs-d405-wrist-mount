# Printing and installation

[简体中文](printing-and-installation.zh-CN.md)

## Choose the file

Prefer the STEP file when the manufacturing service accepts it; it preserves analytic geometry better than STL tessellation. Use the reviewed files in [`hardware/release/`](../hardware/release/), not intermediate angle outputs.

Use the single STEP/STL in `hardware/release/`. The 30° geometry was physically manufactured and installed; the published file incorporates the measured 1 mm rear-hole correction discovered during that installation.

## Material

| Material | Suggested use | Notes |
| --- | --- | --- |
| PETG | first fit-check and durable general use | good layer adhesion and impact resistance; usually less warp than ABS |
| ABS | lighter/stiffer production option | Seeed uses ABS for many structural B601 printed parts; control warping |
| PA12 MJF/SLS | premium option | good isotropy and fit, but frequently much more expensive |
| PLA | dimension-only prototype | not preferred for long-term wrist use because of heat/creep/impact limits |

Physically manufactured examples used PETG/100% and ABS/60%. A camera mount does not automatically benefit from 100% infill: wall count, layer orientation, screw regions, and transition geometry matter more than blindly maximizing mass. For a normal local FDM print, ABS or PETG at roughly 40–80% is a reasonable starting range.

Suggested slicer baseline:

- 0.4 mm nozzle;
- 0.2 mm layer height;
- 4 or more perimeters around screw and transition regions;
- supports where the selected orientation creates unsupported overhangs;
- inspect the two M3 passages and two B601 base holes in preview.

The online service used for the physically shown prints selected its own orientation/support plan. Do not infer a universal optimal orientation from surface lines in the photographs.

## Hardware

- 1× RealSense D405;
- 1× Seeed reBot Arm B601-RS with the compatible green gripper camera interface;
- 2× camera screws, starting check: M3×6 mm;
- 2× original B601 mount-interface screws;
- flexible USB 3 cable with sufficient wrist sweep length.

The D405 documentation specifies `2× M3×0.5` rear holes and a maximum 4.0 mm thread engagement. Measure the printed backplate and screw under-head length. A screw that bottoms internally can damage the camera even when the mount appears loose.

## Fit-check before robot installation

1. Keep robot motor power disconnected.
2. Inspect the print for cracks, delamination, blocked holes, thin flakes, and warped seating surfaces.
3. Insert the D405 without screws. It should fully seat against the inherited bottom/side/top cradle without excessive force.
4. Verify that the USB connector can enter and leave without rubbing the printed opening.
5. Install the two camera screws loosely, seat the camera, then tighten alternately in small increments.
6. Confirm that screw heads clamp the backplate and do not bottom in the camera.
7. Lightly push the camera in multiple directions. There should be no rocking or clicking.

The 3.6 mm passages are clearance holes; they do not thread into the plastic. Camera registration comes from the full cradle surfaces plus screw clamping.

## Install on the B601-RS

1. Disconnect motor power and support the wrist/gripper.
2. Place the mount on the green interface with the USB opening on the physical D405 connector side.
3. Start both base screws before tightening either one fully.
4. Check that the base is flush and the filled transition does not touch moving gripper components.
5. Connect USB and establish a relaxed service loop. Do not allow the connector to carry cable tension.
6. Manually open and close the gripper and slowly sweep reachable wrist motion while unpowered, watching the USB lead and braided motor harnesses.
7. Capture a camera frame and verify orientation, gripper centering, vignetting, exposure, and focus.

## After installation

- For RGB research, freeze the mechanical mounting and record the mount version in dataset metadata.
- For metric RGB-D work, calibrate intrinsics/profile and the installed camera-to-tool/robot transform. Do not treat nominal CAD pose as measured extrinsics.
- Recheck screw preload and image stability after initial manipulation trials.
- Stop immediately if the camera shifts, the print cracks, a cable becomes taut, or the mount approaches another robot part.

## Physical photographs

See [photo gallery](photo-gallery.md). Use CAD, not photograph pixels, for dimensions.
