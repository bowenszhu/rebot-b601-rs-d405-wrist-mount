# Attribution and upstream sources

## This project

- Design, analysis, documentation, physical validation, and photographs: **Bowen Zhu**, 2026.
- Suggested attribution: `Bowen Zhu, reBot B601-RS D405 Wrist Mount, https://github.com/bowenszhu/rebot-b601-rs-d405-wrist-mount`.

## Seeed open-hardware source

The mechanical interface and complete D405 cradle are derived from Seeed-Projects' `D405_305_Mount.step`:

- Repository: <https://github.com/Seeed-Projects/reBot-DevArm>
- Pinned commit: [`590ff16c51099a15a34abb339c6364355fde9235`](https://github.com/Seeed-Projects/reBot-DevArm/tree/590ff16c51099a15a34abb339c6364355fde9235)
- Original file: [`hardware/reBot_B601_DM/3D_Printed_Parts/D405_305_Mount.step`](https://github.com/Seeed-Projects/reBot-DevArm/blob/590ff16c51099a15a34abb339c6364355fde9235/hardware/reBot_B601_DM/3D_Printed_Parts/D405_305_Mount.step)
- License: CERN-OHL-W-2.0
- Vendored source SHA-256: `99df53e11fcdd192830ef205d080db310448cc39b891b62a8f64316f6565c28d`

The new mount preserves the upstream wrist interface and complete camera cradle, then applies a rigid 30° pitch, a 9 mm lateral shift, a 6 mm lift, print-clearance holes, a rounded exposed tip, and a solid lofted transition.

## MuJoCo validation environment

The validation renderer used a pinned local checkout of:

- Repository: <https://github.com/Yang-Ci/ReBot_Arm_web_RS>
- Commit: [`d289fa7202ad7da9595a480b29397d70efacc4c1`](https://github.com/Yang-Ci/ReBot_Arm_web_RS/tree/d289fa7202ad7da9595a480b29397d70efacc4c1)

That repository did not expose a repository-level license at the pinned commit. Its source and meshes are not redistributed here. Published screenshots are marked as third-party-containing documentation images and are not covered by this project's CC BY grant.

## RealSense references

RealSense and D405 are trademarks/product names of their respective owners. This project is independent and is not endorsed by RealSense or Seeed Studio.
