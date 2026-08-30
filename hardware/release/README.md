# 30° release

This is the single public release set for the Seeed reBot B601-RS / RealSense D405 mount.

| File | SHA-256 | Purpose |
| --- | --- | --- |
| `rebot_b601_rs_d405_mount_30deg.step` | `363c1e3f710760c0cd875668e1dd60884a66ba971799836d5476cf80ac8b4f50` | Preferred manufacturing/CAD file |
| `rebot_b601_rs_d405_mount_30deg.stl` | `bf9ffe0eafc1c5f34afeac5485eced94ce3dc87977e3a995142e9cda287930d0` | Ready-to-slice mesh |
| `rebot_b601_rs_d405_mount_30deg.geometry.json` | `52606d9e267c3cf14d4a21f0ea51bb1cd08721ee84f32736ec62364912ff952b` | Pose, geometry, source-hole measurement, and correction metadata |

The 30° design was physically manufactured and installed. That installation exposed a small inherited alignment issue: the pinned Seeed [`D405_305_Mount.step`](https://github.com/Seeed-Projects/reBot-DevArm/blob/590ff16c51099a15a34abb339c6364355fde9235/hardware/reBot_B601_DM/3D_Printed_Parts/D405_305_Mount.step) centers its rear M3 pair 1.000 mm from the cradle center. The published files fill those inherited passages and recut a centered, 20.000 mm-spaced pair at 3.6/6.0 mm print-clearance diameters, matching the [RealSense D405 mechanical drawing, PDF page 146](https://realsenseai.com/wp-content/uploads/2025/09/Intel-RealSense-D400-Series-Datasheet-October-2025.pdf#page=146).

Automated validation reports ~212.1 mm³ source-hole fill, exactly two corrected through/counterbore axes with no residual old axes, one valid STEP solid, a closed/connected/manifold STL, substantial transition overlap, and zero added D405-envelope collision.
