# 验证记录

[English](validation.md)

## 四层证据不能混用

1. **CAD 拓扑**：实体有效性、孔位、尺寸、原版托架等价性。
2. **Mesh 完整性**：STL 单连通、封闭、无非流形边。
3. **MuJoCo 筛查**：D405 包络间隙、工作距离和第一阶视野。
4. **真机验收**：打印适配、螺丝装配、USB 插拔和真实相机画面。

上一层通过不代表下一层自动通过。

## 自动 CAD 检查

`src/design_mount.py` 与 `src/validate_outputs.py` 要求：

- STEP 只有一个有效实体；
- STL 只有一个连通区域；
- STL 边界边和非流形边均为零；
- D405 与 B601 四条螺丝通道没有被堵；
- 原版完整托架在刚体变换前几何完全等价；
- 左右方向不变，USB 开口侧正确；
- 过渡体与底座、托架都有较大实体搭接；
- 新增过渡体对 D405 工程包络碰撞为零；
- D405 两螺丝轴距保持 20.000 mm；
- 元数据记录实心过渡、平移、孔径和未镜像状态。

30°几何结果：

| 指标 | 结果 |
| --- | ---: |
| STEP 实体数 | 1 |
| STEP 体积 | ~32,475.6 mm³ |
| D405 螺丝轴距 | 20.000 mm |
| 通孔/沉孔直径 | 3.6 / 6.0 mm |
| 托架横向平移 | −9.0 mm |
| Seeed源M3孔对偏移 | +1.000 mm |
| 孔位修正 | −1.000 mm |
| 源孔填回体积 | ~212.1 mm³ |
| 新过渡体–D405碰撞 | 0.0000 mm³ |
| 过渡体–底座搭接 | ~2,002 mm³ |
| 过渡体–托架搭接 | ~751 mm³ |

![修正CAD审阅图](assets/cad/rebot_b601_rs_d405_mount_30deg_review.png)

## MuJoCo 筛查

本地验证使用[`ReBot_Arm_web_RS@d289fa7202ad7da9595a480b29397d70efacc4c1`](https://github.com/Yang-Ci/ReBot_Arm_web_RS/tree/d289fa7202ad7da9595a480b29397d70efacc4c1)，以B601真实螺丝轴线基准挂载完整D405包络和实际生成的mount mesh。

保守 D405–绿色件间隙：

| 俯角 | 间隙 |
| ---: | ---: |
| 原版15° | 9.17 mm |
| 25° | 11.17 mm |
| 29° | 9.53 mm |
| **30°** | **9.12 mm** |
| 35° | 7.06 mm |

![MuJoCo 外部装配视图](assets/simulation/wrist_mount_assembly_side_comparison.png)

下面的视图使用实物D405 640×480标定参数比较多个测试角度。十字线和任务代理帮助理解画面，但托盘/方块像素面积不是通用角度的选择依据。

![实机标定视野对比](assets/simulation/wrist_rgb_factory_calibrated_comparison.png)

局限：

- D405 使用带圆角工程包络，不是每个倒角都精确的制造模型；
- MuJoCo 主点居中，忽略少量主点偏差和镜头畸变；
- 场景和 IK 姿态是筛查代理；
- mesh 距离不是公差堆栈，也不是通电碰撞认证。

## 打印与安装实证

实际制造了PETG 100%和ABS 60%两种FDM材料配置。图库包含打印件和安装视图。

以下照片和真实相机结论对应实际制造、安装的30°设计。这次安装暴露了上游1 mm孔偏移；发布件已经收入实测修正。

- 实心过渡部分连续成形；
- D405 能完整坐入继承自原版的托架；
- 两颗相机螺丝和两颗 B601 接口螺丝均可装配；
- USB-C 能从正确一侧正常插入；
- mount 不遮挡相机正面成像器；
- 安装俯角和可见间隙与仿真方向一致；
- D405 640×480 RGB 中夹爪中心线基本位于画面中心，支持9 mm平移方向正确。

修正几何通过同样的CAD和MuJoCo检查，并额外断言导出STEP中只能保留两条修正通孔/沉孔轴。

![安装背面](assets/photos/09-installed-rear-left-privacy-blurred.png)

## D405真实输出

下图使用安装在机械臂上的D405直接输出、未经裁剪的640×480帧。原版支架来源是2026-08-24录像第10.0秒提取的RGB；改造支架来源是2026-08-30在预热120帧后采集的同步RGB/Depth。Depth对齐到RGB，同时保留16位原始PNG和0.04–0.50 m彩色可视化。

![D405真实输出对比](assets/camera/d405-physical-output-comparison.png)

这些证据支持定性视野结论：改造画面让夹爪居中，并包含更多近场工作区。由于采集日期、照明和机械臂姿态均未受控，它**不能**证明定量光学提升；历史记录也没有Depth。准确来源路径、时间、哈希、内参、Depth scale和有效像素比例见[`data/physical_d405_capture_provenance.json`](../data/physical_d405_capture_provenance.json)。

## 目前不声称已经完成

- 全关节通电碰撞扫掠；
- PETG 与 ABS 振动的量化比较；
- 反复拆装后的外参重复性；
- 修正孔位的重复制造测量；
- 最大流负载下30分钟温升记录；
- 相机到机器人/tool frame 的 metric RGB-D 外参标定。

这些是后续验证任务，不能当作默认已经通过。

## 复现

CAD：

```bash
conda env create -f environment-cad.yml
conda activate rebot-d405-cad
python src/design_mount.py --angles 25 29 30 35
python src/validate_outputs.py --angles 25 29 30 35
```

仓库快速完整性检查：

```bash
python tools/check_repository.py
```

可选的只读真机RGB-D采集（脚本只打开指定相机，不连接机械臂或CAN）：

```bash
python tools/capture_d405_rgbd.py --serial <D405_SERIAL> --output-dir capture-output
python tools/build_physical_camera_comparison.py \
  --redesigned-rgb capture-output/d405-rgb.png \
  --redesigned-depth-colorized capture-output/d405-depth-colorized.png \
  --output capture-output/d405-physical-output-comparison.png
```

采集脚本需要`pyrealsense2`、NumPy和OpenCV；对比图生成脚本使用`environment-cad.yml`中的Pillow。

MuJoCo 复现见 [simulation.zh-CN.md](simulation.zh-CN.md)，机器可读数据位于 [`data/`](../data/)。
