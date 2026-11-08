# N67 构建

需要 Python 3.12、Rust stable（安装 thumbv7em-none-eabi target）、Zig 0.15.1、Node.js。Python 依赖见 requirements-port.txt；Node 依赖见 package.json（npm install）。

自行取得固件 3.1.190 的 vela_ap.bin，设置环境变量 CHAOS_FW 为其完整路径。预期 SHA256：`3e264bc267431ec71843cc7c2e4acd928b9280ea39ee1cd888636adcebabf82f`。

设置 CHAOS_FONT 指向可合法使用、支持中文的 TrueType 字体；仅用于安装器预览图。CHAOS_ZIG 可指定 zig 可执行文件；否则从 PATH 查找。LUAPARSE_PATH、FENGARI_PATH 可指定对应 Node 包目录。构建支持源码已放在 build-support/，包括其 work/ 子目录，请勿遗漏。

```text
python -m pip install -r requirements-port.txt
npm install
rustup target add thumbv7em-none-eabi
python tools/build_n67.py
```

输出为 n67/generated/resource.bin。可重命名后作为表盘安装器使用。SOURCE_DATE_EPOCH 可固定构建时间。程序不执行刷写。

固件、系统字体和用户投递包不随仓库分发。针对性测试位于 tools/test_*.py；请阅读各测试的外部依赖。完整测试的已知失败见 VALIDATION.md。

投递包回归测试需另设 CHAOS_DELIVERY_FIXTURE 指向自行取得的参考 iOS26 包；不随源码附带。
