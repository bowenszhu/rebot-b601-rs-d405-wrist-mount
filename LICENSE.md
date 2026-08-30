# Licensing

This repository is intentionally multi-licensed so that the inherited open-hardware terms remain intact and Bowen Zhu receives attribution.

| Material | License |
| --- | --- |
| `hardware/`, `src/design_mount.py`, `src/validate_outputs.py`, `src/inspect_source_hole_alignment.py`, and the generated mechanical design | [CERN-OHL-W-2.0](LICENSES/CERN-OHL-W-2.0.txt) |
| Original software in `simulation/`, `src/render_*.py`, `tools/`, and `.github/` | [MIT](LICENSES/MIT.txt) |
| Original prose and photographs in `README*` and `docs/` | [CC BY 4.0](LICENSES/CC-BY-4.0.txt) |
| `hardware/vendor/seeed-rebot-devarm/` | CERN-OHL-W-2.0, copyright and attribution retained from Seeed Studio / Seeed-Projects |

The MuJoCo screenshots in `docs/assets/simulation/` visibly incorporate assets from the separately maintained `ReBot_Arm_web_RS` project. They are included for validation commentary and are **not relicensed** by this repository; rights in underlying third-party robot/scene assets remain with their respective authors. See [ATTRIBUTION.md](ATTRIBUTION.md).

When reusing this project, keep the relevant license notice and credit **Bowen Zhu**. Hardware derivatives must also satisfy CERN-OHL-W-2.0 and retain the Seeed upstream notices.
