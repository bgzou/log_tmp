# HDC 工具排查结果（2026-11-08）

- 原 `../hdc.exe` 在 Windows PowerShell 中退出 `0xC0000135`。PE 导入表要求 `libusb_shared.dll`，原目录没有该文件；因此只把原 exe 的目录加入 PATH 不能解决问题。HDC 是命令行工具，双击没有安装流程。
- 已在 `../../部署测试/00_HDC工具/hdc_6.1.1.280/` 放好同一工具包的 `hdc.exe` 和 `libusb_shared.dll`，并将此目录加入当前 Windows 用户 PATH。在本机运行 `hdc -v` 得到 `Ver: 3.2.0d`，退出码 0；`hdc list targets -v` 得到 `[Empty]`，退出码 0。当前没有连接 CPRO，设备端还未验证。
- 两个文件从 [SDL CI 所用的 HarmonyOS 6.1.1.280 工具包镜像](https://github.com/libsdl-org/SDL/blob/main/.github/actions/setup-harmonyos-toolchain/action.yml)提取；提取脚本核验 ZIP 成员 CRC 和大小。来源、哈希和连接方法见 [现场 HDC 说明](../../部署测试/00_HDC工具/README.md)。该包不是华为官网直接下载，未取得华为整包校验和。
- [华为 HDC 文档](https://developer.huawei.com/consumer/cn/doc/HarmonyOS-Guides/hdc/)说明独立使用时 exe 与 `libusb_shared.dll` 要放在一起。新开终端后运行 `hdc -v`；连接 CPRO 并授权后再运行 `hdc list targets -v` 和 `hdc shell pwd`。
- 旧版 `commandline-tools-windows-2.0.0.2.zip` 不含 HDC 或此 DLL，不能解决本问题。策略运行本身不依赖 HDC；SSH/SCP 也可用于传现场包。
