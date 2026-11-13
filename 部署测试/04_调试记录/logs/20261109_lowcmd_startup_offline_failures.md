# LowCmd 启动修复期间的离线失败复核

本文件整理执行器已返回的失败输出，属于事后记录，不冒充原始完整 TTY 转储。所有操作仅在工作站/服务器离线进行，无 DDS 发布、无机器人动作。

1. 首次服务器 x86 合成帧审计无法启动：`/tmp/opencode/build_lowcmd_startup/deploy/robots/as2w/r214/as2w_r214_publish: error while loading shared libraries: /tmp/opencode/sdk2_install/lib/libddsc.so.0: file too short`。检查发现 `libddsc.so.0` 仅 10 字节、`libddscxx.so.0` 仅 12 字节，是 Windows checkout 转写的符号链接目标文字。用仓库既有 `tools/fix_sdk2_links.sh /tmp/opencode/sdk2_install/lib` 恢复二者为有效 symlink，再运行通过。没有修改工作站权威 SDK 源码。
2. 独立 `verify_startup_frames.py` 初版误断言 HG `mode_pr/mode_machine` 位于 raw 内存 offset 8/9，运行返回 `AssertionError: Unexpected HG header layout`。审计输出前 16 字节为 `0002000001000000295c0f3f00000000`；依据实际 HG struct 布局和字段打印改为 offset 0/1，重新对 x86/ARM64 两份完整帧做逐字 CRC 和槽位检查，全部通过。

最终通过的原始构建和合成帧输出分别见 `20261109_lowcmd_startup_{x86,arm64}_{build,audit}.log`，最终结论见上级 `INDEX.md` 最新节。
