# R249 平地低速策略适配

来源：`YuTaoV5/Rob2Nav` main 分支 `deliveries/as2w-deploy/flat-low-speed-r249`，本地 sparse clone 保存在 `部署参考/Rob2Nav-r249-source`。

- 用途：低速平地遥控预览；交付方明确说明楼梯回归 0/16，禁止用于楼梯。
- ONNX：`obs[1,60] -> actions[1,16]`，SHA-256 `2483c7b49ccd0c4db1d738aca8c2fa716a12e52e92e52d6fc8669f9b63b90a2d`。
- 观测：动态命令偏置、IMU、q/dq、上一帧最终动作和 0.62 秒步态时钟；无机体实际线速度、无 recurrent state。
- 适配器必须执行交付方的低速后腿 action gate，并把 gate 后的最终动作写回 history。
- 策略增益从本目录 `deploy.yaml` 读取；当前交付值为腿 `kp=55/kd=2`、轮 `kp=0/kd=2`，只对 R249 生效，不是其他策略的全局常量。
- 交付没有逐帧 trace，不能沿用 R214 的 1050 帧 replay 门槛；先以 ONNX 合同、C++ smoke、offline audit 和独立 MuJoCo 复演补齐，再做有界 zero-B 真机首测。
