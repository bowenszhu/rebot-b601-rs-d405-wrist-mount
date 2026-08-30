# MuJoCo reproduction

[简体中文](simulation.zh-CN.md)

## Purpose and boundary

The MuJoCo model answers first-order questions:

- where does the full D405 envelope sit relative to the green gripper structure?
- how does pitch change near-field visibility and gripper occlusion?
- does the tested design remain outside the 7 cm ideal near-range boundary at the proxy TCP targets?

It does **not** certify powered collision-free motion, estimate print deformation, or replace measured camera extrinsics.

## Why the robot model is not vendored

Validation used [`ReBot_Arm_web_RS@d289fa7202ad7da9595a480b29397d70efacc4c1`](https://github.com/Yang-Ci/ReBot_Arm_web_RS/tree/d289fa7202ad7da9595a480b29397d70efacc4c1). That commit did not expose a repository-level license, so its XML/URDF/mesh assets are deliberately not copied into this repository. Clone it separately and point the simulation to the scene XML.

## Setup

Generate the tested angle meshes in the dedicated CAD environment:

```bash
conda env create -f environment-cad.yml
conda activate rebot-d405-cad
python src/design_mount.py --angles 25 30 35
python src/validate_outputs.py --angles 25 30 35
```

Obtain the pinned robot scene:

```bash
git clone https://github.com/Yang-Ci/ReBot_Arm_web_RS.git external/ReBot_Arm_web_RS
git -C external/ReBot_Arm_web_RS checkout d289fa7202ad7da9595a480b29397d70efacc4c1
```

Create a **separate** MuJoCo environment; do not mix it with LeRobot or ROS system Python:

```bash
python3 -m venv .venv-sim
.venv-sim/bin/pip install -r requirements-simulation.txt
```

Run the rendered comparison and the 1° sweep:

```bash
export REBOT_MUJOCO_MODEL="$PWD/external/ReBot_Arm_web_RS/rebotarm_ros2/src/rebotarm_mujoco_rs/models/rs_grasp_scene.xml"
MUJOCO_GL=egl .venv-sim/bin/python simulation/simulate_fov.py
MUJOCO_GL=egl .venv-sim/bin/python simulation/sweep_angles.py
```

Outputs are written to ignored `build/`.

## Camera model

- D405 body envelope: 42 × 42 × 23 mm with a rounded visual proxy and a sharp conservative collision box;
- optical reference: left imager, 9 mm from the housing/stereo midpoint;
- optical start point behind front glass: 3.7 mm in the model;
- physical 640×480 color vertical FOV: 62.82°;
- physical principal point: approximately `(323.24, 235.99)` pixels;
- MuJoCo principal point: centered, a documented approximation.

## Published outputs

Controlled synthetic RGB/depth at the same grasp pose:

![Stock 15 degree versus redesigned 30 degree synthetic RGB and depth](assets/simulation/wrist_rgb_depth_stock15_vs_redesigned30.png)

Historical camera-only stress screen (15°/25°/35°/45°; it intentionally omits the printable mount mesh):

![Coarse FOV comparison](assets/simulation/historical_wrist_fov_15_25_35_45_comparison.png)

![Tested wrist-camera views](assets/simulation/wrist_rgb_factory_calibrated_comparison.png)

![External assembly/clearance views](assets/simulation/wrist_mount_assembly_side_comparison.png)

The corresponding CSV files are in [`data/`](../data/). Simulation screenshots contain visual assets from the external robot project and are not relicensed under this repository's CC BY terms; see [LICENSE.md](../LICENSE.md).
