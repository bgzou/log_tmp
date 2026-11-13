# 2026-11-09 公开资料定向检索

使用 agent-reach 的 GitHub CLI 与 Exa 搜索。查询：`as2w lowcmd`、`AS2-W`、`as2w`、`As2W`、`AS2-W unitree lowcmd wheel motor index sdk2 github`。

- GitHub 精确 `as2w lowcmd` 代码搜索返回空；宽泛 `as2w` 主要命中 [官方 unitree_ros README](https://github.com/unitreerobotics/unitree_ros) 和大量同形字符串。仓库名搜 `AS2-W` 主要是无关项目。
- Exa 结果包含 [标准 AS2 官方 SDK 指南](https://support.unitree.com/home/en/AS2_SDK_Development_Guide)、B2-W/Go2-W 的资料，以及 G1 关节表；这些都不能给当前 AS2-W 固件的四轮 LowCmd 合同。
- [官方 AS2-W URDF 目录](https://github.com/unitreerobotics/unitree_ros/tree/master/robots/as2w_description) 通过 `gh api` 确认有 `as2w.urdf`，但 URDF 不定义 DDS 消息槽位、轮轴控制模式或控制权交接。

结论仅限此次定向检索：没有找到可直接验证本机 AS2-W 16 轴 LowCmd/轮轴模式的公开官方示例。继续向宇树或掌握此固件资料的同事索取，问题清单见 `../../02_现场操作/需厂商确认的低层信息.md`。不把 B2-W、Go2-W 或标准 AS2 的示例移植为真机写入依据。
