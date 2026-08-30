# Primary references

Accessed 2026-08-30 unless a pinned commit is shown.

## Seeed reBot B601-RS

1. **Seeed-Projects, reBot-DevArm** — official open-hardware repository and B601-DM/B601-RS project overview: <https://github.com/Seeed-Projects/reBot-DevArm>
2. **B601-RS hardware specification** — official RS hardware files, BOM, and print recommendations: <https://github.com/Seeed-Projects/reBot-DevArm/blob/main/hardware/reBot_B601_RS/README.md>
3. **reBot Arm B601-RS quick start** — official assembly/configuration entry point: <https://wiki.seeedstudio.com/rebot_b601_rs_getting_started/>
4. **Pinned Seeed source commit**: <https://github.com/Seeed-Projects/reBot-DevArm/tree/590ff16c51099a15a34abb339c6364355fde9235>
5. **Source D405 cradle at that commit**: <https://github.com/Seeed-Projects/reBot-DevArm/blob/590ff16c51099a15a34abb339c6364355fde9235/hardware/reBot_B601_DM/3D_Printed_Parts/D405_305_Mount.step>

The minimum vendored STEP and CERN-OHL-W-2.0 license are in [`hardware/vendor/seeed-rebot-devarm/`](../hardware/vendor/seeed-rebot-devarm/).

## RealSense D405

6. **RealSense D405 product page** — see “Small features, high impact → RGB without a dedicated RGB” and “Tech Specs → RGB → Technology” for 7–50 cm range, 87° × 58° depth FOV, global shutter, and “Left imager RGB with ISP”: <https://www.realsenseai.com/products/stereo-depth-camera-d405/>
7. **RealSense D400 Series Product Family Datasheet, Figure 10-13 on PDF page 146** — D405 dimensions, centered 20.00 mm M3 pair, 18 mm baseline, maximum insertion depth, Min-Z tables, and depth origin: <https://realsenseai.com/wp-content/uploads/2025/09/Intel-RealSense-D400-Series-Datasheet-October-2025.pdf#page=146>
8. **D400 Calibration Tools User Guide, §2.1 “Calibration Parameters”** — states that the left camera is the reference camera and is located at world origin: <https://dev.realsenseai.com/docs/calibration-tools-user-guide-for-intel-realsense-d400-series/>
9. **Projection in RealSense SDK 2.0** — per-stream pixel and 3D coordinate systems: <https://dev.realsenseai.com/docs/projection-in-realsense-sdk-2-0/>
10. **D400 Depth Post-Processing, “2. Edge-preserving filtering”, occlusion paragraph** — explains that the stereo depth map is referenced to the left imager: <https://dev.realsenseai.com/docs/depth-post-processing-for-intel-realsense-depth-camera-d400-series/>

## Simulation

11. **ReBot_Arm_web_RS**, pinned local validation commit `d289fa7202ad7da9595a480b29397d70efacc4c1`: <https://github.com/Yang-Ci/ReBot_Arm_web_RS/tree/d289fa7202ad7da9595a480b29397d70efacc4c1>
12. **MuJoCo Python documentation**: <https://mujoco.readthedocs.io/en/stable/python.html>

The external robot project's pinned commit did not expose a repository-level license, so its model assets are not redistributed here. See [ATTRIBUTION.md](../ATTRIBUTION.md).

## Licensing

13. **CERN Open Hardware Licence Version 2 — Weakly Reciprocal**: <https://ohwr.org/cern_ohl_w_v2.txt>
14. **Creative Commons Attribution 4.0 International**: <https://creativecommons.org/licenses/by/4.0/>
15. **MIT License**: <https://opensource.org/license/mit>

## Local measured and generated evidence

Claims such as the exact 62.82° profile FOV, `(323.24, 235.99)` principal point, angle-sweep distances, mesh overlap volumes, and physical fit are local measurements or generated validation outputs—not claims copied from the linked sources. They are published in [`data/`](../data/), the release geometry JSON, and [validation.md](validation.md).
