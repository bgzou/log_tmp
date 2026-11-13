# 发给 CPRO 同事的核实项

请分别说明**鸿蒙宿主**和**Ubuntu 环境**的结果。密码、设备序列号、账户密钥不用发；日志可打码。

1. Ubuntu 是 chroot、容器还是虚拟机？进入命令是什么？在 Ubuntu 里运行：`uname -m; cat /etc/os-release; id; mount | grep -E ' /dev | /proc | /sys '`。
2. CPRO 接 AS2-W Orin 拓展坞时，Ubuntu 里的有线网口是否可见？请回传宿主与 Ubuntu 的 `ip -br addr; ip -br link; ip route`。能否在 Ubuntu `ping -c 3 192.168.123.161`（机器人 PC1 主控）？拓展坞网口与本体主控网络之间是桥接还是路由？现场拓展坞是 NX 旗舰版还是其他版？
3. Ubuntu 内能否运行 ARM64 Linux ELF、安装 `cmake/g++` 并使用 `unitree_sdk2`？网卡能否收发 Cyclone DDS 多播？若已有 SDK2，请给版本或安装目录。
4. 本次优先用 AS2-W 原厂遥控器：请确认机器人配对正常，CPRO Ubuntu 能从 `rt/wirelesscontroller` 读到摇杆/按键状态吗？关闭原厂运控后该话题是否仍更新、原厂急停是否仍有效？后两项只有具备安全低层控制端时才实测。Xbox 设备透传仅为备用方案。
5. 我的 Windows PC 如何连接 CPRO：HDC USB/TCP 还是 SSH？请给可执行的连接方式、所需调试授权和可写文件目录。本机 HDC 已能启动，但尚未连到 CPRO；若 CPRO 固件要求特定 HDC 版本，请告知。

现场到机后可直接在 CPRO 的 Ubuntu 环境运行 `bash tools/probe_cpro.sh | tee cpro_preflight.log`，将日志发回；该脚本只读，不会发电机指令。
