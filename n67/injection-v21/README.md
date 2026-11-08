# v2.1 注入相容移植

参考用户提供的 `Chaos-9Pro-3.1.190-v2.1.bin`。原档 SHA256 与每个提取文件的摘要见 reference.json。

- bootstrap.bin：原桥接模组 0x0000..0x00da，magic、复制和双 alias 缓存同步，逐字节复用。
- timer-bootstrap.bin：0x0442..0x049c，原生定时器创建与 Lua 定时器暂停交接，逐字节复用。
- load_module.lua.in / arm_registrar.lua.in：从原档提取的对应 Lua 函数。
- 原生应用仍为当前版本与 22 个页面，ID 保留 0xE7D4 / 990000000029。

构建先正常编译桥接器，再由 tools/port_v21_bootstrap.py 移植上述独立机器码，
校验所有参考摘要、旧产物摘要、后续函数无相对跳转进入被替换前缀，重算函数偏移与摘要。
参考 C 逻辑仍见 build-support/filemanager/platform_n67.c.in 的同名函数。
定时器桥接仍为 90 字节，原生注册检查和图示恢复逻辑保留。

Lua 函数在生成前替换回参考版本；load_module 额外保留 prepare_module 的延后展开入口，
避免打开安装器就解压载荷。指纹检查、内存范围和写入所有权检查未移除。
原生 UI 已直接读系统资源，不再写不使用的 /data/chaos/ui 旧 P67 图片。

桌面验证检查逐字节一致、真实 ARM 复制/缓存同步/定时器交接，以及打包后的 Lua 实际入口。
这次是按参考版本移植注入流程，未断言已确定用户设备上上一版失败的根因，仍需设备确认。
