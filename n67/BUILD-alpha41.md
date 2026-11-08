# alpha.41 構建

來源目錄包含這次修改對應的 supervisor、n67、tools 與 build-support；不包含原廠韌體、工具鏈或虛擬機憑證。

工具：Python 3.12、Rust（thumbv7em-none-eabi target）、Zig 0.15.1、Node.js。Python 套件見 requirements-port.txt；Lua 驗證依賴 fengari 與 luaparse。

環境變數：
- CHAOS_FW：從使用者合法取得的 N67 CN 3.1.190 完整韌體解出的 vela_ap.bin。
- CHAOS_FONT：對應 MiSans-Regular.ttf。
- CHAOS_ZIG：zig 可執行檔。
- FENGARI_PATH、LUAPARSE_PATH：Node 套件目錄。

在來源根目錄執行：

```text
python tools/build_n67.py
python tools/verify_port.py
```

生成安裝檔：n67/generated/resource.bin。

原廠 AP SHA256：3e264bc267431ec71843cc7c2e4acd928b9280ea39ee1cd888636adcebabf82f。
上游 v1.1.0 提交：cb5e166；參考安裝包 SHA256：e590319787d757752811d617aab666153d65752d9256f78e4a59c71ec2dd8fc0。

不要啟用 CHAOS_SETTINGS_EGG；本版只發布 standard profile。生成器與關於頁均標示 2.2-alpha.41。
