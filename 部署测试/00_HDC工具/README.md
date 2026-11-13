# Windows HDC 工具

## 已完成的本机验证（2026-11-08）

- 原 `../../部署参考/hdc.exe` 单独运行退出 `0xC0000135`。它的 PE 导入表要求 `libusb_shared.dll`，原目录缺该文件；把原 exe 路径加入 PATH 不能解决 DLL 缺失。
- 从 SDL 项目[公开 CI 使用的 HarmonyOS 6.1.1.280 命令行工具包镜像](https://libsdl.org/harmonyos-devtools/commandline-tools-windows-x64-6.1.1.280.zip)按 ZIP 索引提取同包的 `hdc.exe` 与 `libusb_shared.dll`，存于 `hdc_6.1.1.280/`。来源可以在 [SDL 的 CI 配置](https://github.com/libsdl-org/SDL/blob/main/.github/actions/setup-harmonyos-toolchain/action.yml)核对；提取脚本 `fetch_hdc.py` 核验 ZIP 成员 CRC 和长度。没有取得华为发布的整包 SHA-256，因此未把 SDL 镜像声称为华为官网直接下载。
- `hdc.exe` SHA-256：`f8e156f0949cf26530935f7202e93a3f628aa8252d693cfcce6eb57f117d0a2e`。
- `libusb_shared.dll` SHA-256：`76ec9ad86f8e90a87b15bd0d302f79811edf75c8878eb66fcf2a55d88d3c7331`。
- PowerShell 实测 `hdc -v` → `Ver: 3.2.0d`，退出码 0；`hdc list targets -v` → `[Empty]`，退出码 0。`[Empty]` 表示当前没有连接或授权的 CPRO，不是 HDC 启动失败。
- 工具目录已加入 **当前 Windows 用户的 PATH**，无需管理员权限。新开 PowerShell/终端后运行 `hdc -v`；已打开的旧终端可直接调用本目录 `hdc_6.1.1.280/hdc.exe`。

## CPRO 接入时

1. 在 CPRO 上开启相应开发者调试方式并授权当前 PC。
2. USB 调试：`hdc list targets -v`；若无线调试：按 CPRO 显示的实际 `IP:port` 执行 `hdc tconn IP:port`，再 `hdc list targets -v`。不要把机器人 Orin 的 IP 当成 CPRO HDC 地址。
3. 若识别设备，先用 `hdc shell pwd` 验证 shell，再询问同事 Ubuntu 与宿主共享的可写目录。传包语法见[华为 HDC 文档](https://developer.huawei.com/consumer/cn/doc/HarmonyOS-Guides/hdc/)：`hdc file send SOURCE DEST`。也可改用 SSH/SCP；策略运行不依赖 HDC。
4. 若显示 `Unauthorized`，在 CPRO 上接受授权；若 `[Empty]`，先查调试开关、USB 数据线/无线调试端口和驱动。
