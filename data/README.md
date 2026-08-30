# Validation data

| File | Meaning |
| --- | --- |
| `wrist_rgb_angle_sweep_1deg.csv` | Reproduced 20°–36° sweep at 1° increments and five proxy stages |
| `wrist_rgb_factory_calibrated_metrics.csv` | Reproduced rendered metrics for 15°/25°/30°/35° |
| `historical_wrist_fov_15_25_35_45_metrics.csv` | Early camera-only stress screen; retained as historical evidence, not the angle selector |
| `seeed_source_hole_alignment.json` | Direct CadQuery measurement of the pinned Seeed cradle center, rear-hole axes, +1 mm offset, and −1 mm correction |
| `physical_d405_capture_provenance.json` | Source paths, timestamps, hashes, calibration values, and limitations for the physical D405 RGB/depth comparison |

Floating-point last digits may differ across MuJoCo/NumPy/platform builds. Interpret the published millimetre-scale boundaries at physically meaningful precision.
