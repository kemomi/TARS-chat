<!--
 * @Author: fbee3157 fbee3157@outlook.com
 * @Date: 2026-05-13 17:30:39
 * @LastEditors: fbee3157 fbee3157@outlook.com
 * @LastEditTime: 2026-05-13 17:31:47
 * @FilePath: \TARS-chat\stls\README.md
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
-->
# 3D 打印件清单

本目录应包含以下 STL 文件(由你根据自己的尺寸建模或从社区下载)。下表为推荐结构,可作为建模依据。

## 文件清单

| 文件名                  | 数量 | 推荐参数                              | 说明                         |
|-------------------------|------|---------------------------------------|------------------------------|
| `base.stl`              | 1    | 0.2mm 层高 / 25% 填充 / 支撑          | 底座,容纳电池和电路板       |
| `body_front.stl`        | 1    | 0.2mm / 20% / 无需支撑                | 机身前壳,挖屏幕窗口         |
| `body_back.stl`         | 1    | 0.2mm / 20% / 无需支撑                | 机身后壳,留散热孔与接口     |
| `neck_tilt_arm.stl`     | 1    | 0.16mm / 40% / 树状支撑               | 俯仰摆臂(连接 Tilt 舵机)   |
| `neck_pan_base.stl`     | 1    | 0.16mm / 40%                          | 水平转盘                     |
| `servo_horn_adapter.stl`| 2    | 0.12mm / 80%                          | 舵机臂转接,匹配 SG90 出厂角  |
| `head_shell.stl`        | 1    | 0.2mm / 15%                           | 头部外壳(屏幕载体)         |
| `head_cover_top.stl`    | 1    | 0.2mm / 15%                           | 顶盖                         |
| `cable_clip.stl`        | 2    | 0.2mm / 30%                           | 走线卡扣                     |

## 推荐打印参数

- **材料**: PLA(室内桌面用足够;若放车里建议 PETG/ABS)
- **喷嘴**: 0.4mm
- **层高**: 外壳 0.2mm,关节 0.16mm
- **打印速度**: 50mm/s
- **温度**: 喷嘴 210°C / 热床 60°C(PLA)

## 螺丝清单(配套)

| 规格          | 数量 | 用途              |
|---------------|------|-------------------|
| M2 × 6mm 自攻 | 8    | 舵机臂固定        |
| M3 × 8mm 自攻 | 12   | 机身合壳          |
| M3 × 16mm 内六角 | 4 | 底座承重         |

## 装配顺序

1. 打印全部 STL,用美工刀去除支撑毛刺
2. 把 Pan 舵机塞入 `neck_pan_base.stl` 槽位,用 M2 螺丝固定
3. `servo_horn_adapter.stl` 卡到 Pan 舵机臂上,再装到 `neck_tilt_arm.stl`
4. Tilt 舵机同理装入摆臂
5. 屏幕用双面胶或卡扣固定到 `head_shell.stl` 的窗口内
6. 树莓派、UBEC、电池座放入 `base.stl`,走线从顶部孔上来
7. 合壳前先通电测试一遍舵机方向,有问题就 `config.yaml` 里翻转角度范围

## 没有建模文件怎么办?

如果你还没有现成 STL,可以:
- **方案 A**: 用 Fusion 360 / OnShape 按上表自己建模(舵机槽尺寸 22.5×11.8×22.7mm)
- **方案 B**: 上 [Thingiverse](https://www.thingiverse.com/) / [Printables](https://www.printables.com/) 搜索 "Pan tilt camera mount SG90",选一套尺寸近的改一下
- **方案 C**: 直接买现成的舵机云台 + 亚克力外壳,跳过 3D 打印

> 建模完成后,把 STL 文件按上面的命名规则丢到本目录即可。
