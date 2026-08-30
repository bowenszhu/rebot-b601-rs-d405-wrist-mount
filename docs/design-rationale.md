# Design rationale

[简体中文](design-rationale.zh-CN.md)

## 1. Problem statement

The pinned Seeed [`D405_305_Mount.step`](https://github.com/Seeed-Projects/reBot-DevArm/blob/590ff16c51099a15a34abb339c6364355fde9235/hardware/reBot_B601_DM/3D_Printed_Parts/D405_305_Mount.step) for D405/Gemini 305 was a useful physical and licensing baseline, but its approximately 15° pose did not provide the desired near-field wrist view. A replacement had to improve eye-in-hand visibility without inventing a new camera retention system or sacrificing physical fit.

The source STEP is pinned at Seeed commit [`590ff16c51099a15a34abb339c6364355fde9235`](https://github.com/Seeed-Projects/reBot-DevArm/tree/590ff16c51099a15a34abb339c6364355fde9235) and is located in the B601-DM directory. The compatible interface and derivative described here were physically fitted on a B601-RS; this project deliberately limits its support claim to B601-RS.

The design objectives were therefore separated into independent questions:

1. **Compatibility:** does it use the actual B601 wrist interface and D405 envelope?
2. **Optical reference:** which point should align with the gripper centerline?
3. **Pitch:** how much downward view can be gained before violating clearance or useful range?
4. **Strength:** can the transformed cradle reconnect to the original base through a robust printable load path?
5. **Reproducibility:** can every geometric claim be regenerated and checked?

## 2. Coordinate convention

The design inherits the Seeed STEP coordinates, in millimetres:

- `X`: left/right across the gripper;
- `Y`: from the wrist toward the camera;
- `Z`: forward along the gripper.

Positive pitch points the camera optical axis toward `−Y`, down toward the tabletop. The Seeed cradle's handedness is retained. Camera, wrap, USB opening, backplate, and camera holes are always transformed as one rigid body.

## 3. Why align the left imager

The D405 product page sections [“Small features, high impact → RGB without a dedicated RGB” and “Tech Specs → RGB → Technology”](https://www.realsenseai.com/products/stereo-depth-camera-d405/) explain that the global-shutter D405 has no separate RGB sensor and uses **left-imager RGB with ISP**. The [D400 Calibration Tools User Guide, §2.1 “Calibration Parameters”](https://dev.realsenseai.com/docs/calibration-tools-user-guide-for-intel-realsense-d400-series/) states: “The left camera is the reference camera and is located at world origin.” The [Depth Post-Processing guide, “2. Edge-preserving filtering”, occlusion paragraph](https://dev.realsenseai.com/docs/depth-post-processing-for-intel-realsense-depth-camera-d400-series/) adds: “Since we reference everything to the left imager...”

The [D405 mechanical drawing, PDF page 146](https://realsenseai.com/wp-content/uploads/2025/09/Intel-RealSense-D400-Series-Datasheet-October-2025.pdf#page=146) gives an 18 mm stereo baseline. With the stereo midpoint aligned to the 42 mm housing center, the left imager is 9 mm from that midpoint. Centering the aluminium box would therefore leave the optical reference offset from the gripper centerline.

In the preserved Seeed handedness, the left-imager offset is `+9 mm` in CAD X. The required rigid translation is:

```text
desired left-imager X = 0 mm
original left-imager X = +9 mm
cradle translation X = 0 − 9 = −9 mm
```

The factory 640×480 color profile was also read from the physical camera and used in the visibility rendering: vertical FOV `62.82°`, principal point approximately `(323.24, 235.99)` pixels. MuJoCo uses a centered principal point, so the residual few-pixel offset and lens distortion remain outside this first-order model.

## 4. Why not move only the backplate

The camera is retained by a connected system: lower shelf, side wraps, top wrap, backplate, two camera holes, and the USB opening. Moving only the plate would detach screw axes from the seat and side supports.

The generator therefore extracts the **complete original cradle**, applies a single rigid transform, and checks that its symmetric-difference volume relative to the original is `0 mm³` before transformation. This proves that tilt and lateral centering do not silently deform or mirror the inherited fit geometry.

## 5. Why add a 6 mm lift

Pitching about the lower-rear datum swings the D405's lower-front corner down and back toward the green wrist structure. Pitch alone would consume the original clearance.

The cradle is raised 6 mm before reconnection. This places the 30° lower-front camera corner near the conservative position of the stock 15° installation. The choice is then checked against the complete D405 envelope and green-part mesh in MuJoCo rather than accepted from CAD appearance alone.

## 6. How the 30° pitch was selected

### 6.1 What was scanned

- coarse rendered comparison: 15°, 25°, 30°, 35° (and a 45° stress case);
- fine sweep: 20°–36°, 1° increments;
- full-size D405 envelope placed at the left optical reference;
- actual B601-RS MuJoCo scene and green gripper mesh;
- factory-derived D405 640×480 color intrinsics for view rendering.

Task objects and proxy pick/place poses were rendered to understand visibility, but **task-object pixel area was not used to choose the general-purpose angle**.

### 6.2 Task-independent constraints

Two constraints define the upper pitch boundary at this fixed mount location:

1. **Mechanical clearance:** retain approximately the conservative stock margin. The stock 15° design measured roughly 10 mm physically; the conservative mesh model reports 9.17 mm. A ~9 mm simulation floor is therefore a reasoned baseline, not a manufacturing tolerance certificate.
2. **Near working distance:** keep the optical reference at least 70 mm from the TCP proxy. RealSense publishes 7 cm as the D405 ideal-range near boundary at the relevant 480p class of operation.

Fine-sweep results around the boundary:

| Angle | D405–green clearance | Optical-to-TCP proxy | Decision |
| ---: | ---: | ---: | --- |
| 29° | 9.53 mm | >70 mm | feasible |
| **30°** | **9.12 mm** | **70.2 mm** | selected |
| 31° | 8.71 mm | 69.6 mm | rejected |

The two constraints cross near 30°. Linear interpolation produces about 30.3°, but print, screw, seating, mesh, and camera-model uncertainty are much larger than 0.3°. The defensible output is the integer 30°, not a false-precision decimal.

### 6.3 Why not 35° or 45°

35° improves near-field visibility but reduces conservative D405–green clearance to about 7.06 mm and pushes some targets inside the D405's ideal near range. At 45°, the camera becomes conspicuously forward/downward and the fixed-location assumption is no longer a sensible general-purpose compromise.

If a future task requires more gripper/TCP visibility, the correct redesign is to move the camera farther back/up while recomputing visibility and clearance—not simply to keep increasing pitch.

## 7. Why the transition is solid

The original base is retained through CAD `Y=42 mm`; transformed cradle material is retained down to `Y=38 mm`. A single closed profile from the original `Y=39 mm` section is lofted between the two poses.

This produces a filled transition rather than two touching walls or a cosmetic skin. Validation requires substantial solid overlap with both sides:

- adapter-to-base overlap: about `2.00 cm³`;
- adapter-to-cradle overlap: about `0.75 cm³`;
- new adapter collision with the D405 engineering envelope: `0.0000 mm³`.

The redesigned 30° solid volume is approximately `32.48 cm³`, about `3.43 cm³` above the original. The increase is intentional material for the filled notch and load path.

## 8. Why the published design corrects the camera holes by 1 mm

The [RealSense D405 mechanical drawing, PDF page 146](https://realsenseai.com/wp-content/uploads/2025/09/Intel-RealSense-D400-Series-Datasheet-October-2025.pdf#page=146) specifies two rear `M3×0.5` holes at 20.00 mm spacing, centered on the 42 mm body. Direct measurement of the pinned Seeed STEP found:

- cradle X envelope: `−22.9985446 .. +23.0014556 mm`, center `+0.0014555 mm`;
- rear hole axes: `−8.9985445` and `+11.0014555 mm`, pair center `+1.0014555 mm`;
- source pair offset relative to cradle: **+1.0000000 mm**.

The manufactured 30° design inherited that offset. Its 3.6 mm clearance holes allowed the physical camera to assemble, but clearance should not be used to hide a known source error.

The published geometry therefore fills the source 3.2 mm through holes and 5.6 mm counterbores (~212.1 mm³ restored material), then recuts a centered pair at:

- 3.6 mm through diameter;
- 6.0 mm counterbore diameter;
- exact 20.000 mm axis spacing;
- **−1.000 mm correction** relative to the Seeed source pair.

The camera itself contains the M3 threads; the printed plate is a clearance/clamping component, not a threaded nut. The widened print passages still tolerate FDM/MJF/SLS shrink, while the corrected axes now agree with the D405 drawing. The correction is included in the release and is covered by export-level axis checks.

## 9. Handedness and USB access

Facing the camera front, the left imager appears on the observer's right. Viewer default viewpoints can make the asymmetric part appear mirrored. The authoritative handedness reference is the previously printed Seeed part and the physical USB side—not a CAD viewer screenshot.

The source cradle is not mirrored, and the D405 must not be installed upside-down or rotated 180°. The USB opening moves with the cradle and remains on the physical connector side.

## 10. What this design does not prove

- exact camera extrinsics after printing and screw tightening;
- collision-free powered motion throughout the entire robot workspace;
- long-duration thermal behavior under every D405 stream configuration;
- structural fatigue life or impact certification;
- optimality for a different camera, gripper, mounting block, or task distribution.

For RGB-D research, calibrate the installed camera extrinsics. Treat CAD pose as an initialization, not ground truth.

Primary references are collected in [references.md](references.md). Raw sweep tables are in [`data/`](../data/).
