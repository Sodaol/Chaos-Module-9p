# N67 3.1.190 设备选项 ABI

仅用于 AP SHA256 `3e264bc267431ec71843cc7c2e4acd928b9280ea39ee1cd888636adcebabf82f`。

## 快应用启动

`0xc4fb558` 为 stock quickapp_launch_app 请求生成器，r0 为 NUL 包名，r1 为可选 URI；调用前使用相同的 `0xc2c1268(pkg, NULL)` 检查。原生生成器调用 `0xc44e76c(pkg,24)`、清零 44 字节请求并将 appinfo 首字段放在 +16，再交给 `0xc44a850`。不把 app ID 当字符串，不手动初始化代理，不修改 apps.json。

## 蓝牙名称

初期考察过 bttools globals `0x200d55e4/ec`，最终不使用它们。实际 Bluelet 启动路径 `0xc17621c` 取 adapter 槽 `0x200bad90`，`0xc17622a` 取 API 槽 `0x200bad94`，将 `0x200a14d0` 写入 API 槽。原厂 RW 初始化镜像在对应位置提供接口表：+0x14 为 `0xc3bd211`，+0x18 为 `0xc3bd25d`。

`0xc176660..678` 原厂设置名称路径使用同一 adapter，r1 名称、r2 strlen+1，调用 API+0x14。BTM 包装函数验证 adapter 与下层方法后转发。Chaos 校验接口表、读取当前名称、延后提交并轮询读回，不直接改手机绑定信息。

## 原生 LVGL8 旋转

Lua display 属性表 `0x2c75d894` 将 set_rotation 对应到 `0xc46c721`。它的前半段处理 Lua 参数；`0xc46c776..0xc46c83a` 是内联的原生显示旋转主体。默认 display 槽为 `0x200b3750`。

C 小桥复现原函数 prologue（保存 r4-r8/lr、16 字节栈、r7=sp+8），以 r4=display、r3=rotation 进入原厂主体。主体更新 driver+0x10 bits4..5、重新计算 screen root 边界、发送 0x2b 事件、失效并通知驱动。原厂 epilogue `0xc46c756` 恢复栈。桥不调用 Lua API，不替换固件代码，不移植 10 Pro 的 LVGL9 地址。

调用前检查 display/driver、336×480 分辨率和根数组边界。ARM 测试验证 0/180、根尺寸事件、callee-saved 寄存器及 SP 恢复。没有验证真实刷新驱动或实体触控；软件模型不能证明其显示效果。
