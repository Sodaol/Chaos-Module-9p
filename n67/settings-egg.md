# 系统关于版本文字彩蛋

构建一般版：运行 tools/build_n67.py。
构建彩蛋版：设置环境变量 CHAOS_SETTINGS_EGG=1，再运行相同脚本；会同时编译 Rust settings-egg 和 C CHAOS_SETTINGS_EGG 分支。
构建后运行 tools/verify_port.py；验证器依 manifest.profile 选择普通入口或彩蛋入口的专用检查。
运行时与注册器必须成套使用，不能只替换 Lua 或 Rust 载荷。

准确页面键为 0x0016001b。系统版本值控件槽位 0x200cd0bc，原生 Label 类 0x2c6834b0。
先核对祖先链属于当前关于页，然后登记一次点击/DELETE 事件。
连点5次通过原生 page_goto(0xE7D40000) 打开；超时1200ms、离页或删除清零。
不修改版本值、不覆盖固件页面生命周期、不新增独立定时器。
本版 C 注册器完成应用注册后核对 app 节点，直接进入成功态，不调用 launcher_add。
Lua 使用已注册 app 指针确认成功，不等待本来就不会创建的图示。
两版本共用 ID，需要重启后择一安装。
