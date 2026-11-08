# alpha.43 構建與驗證

沿用本專案 Python 依賴、Rust thumbv7em-none-eabi、Zig 及 Node/Fengari 設定。
CHAOS_FW 指向已核對的 3.1.190 vela_ap.bin；CHAOS_FONT、FENGARI_PATH、LUAPARSE_PATH 沿用前版構建設定。

python tools/build_n67.py
python tools/verify_port.py

不設定 CHAOS_ENTRY_DIAGNOSTIC 或 CHAOS_SETTINGS_EGG，以生成標準 alpha.43。
新 preflight 編譯至獨立 native bridge，由已核對的 Lua/native 引導呼叫；不寫入系統分區。
檢查在 load_module（僅載入獨立引導程式）之後，寫圖示、分配應用描述符與載入 Chaos 模組之前。
ARM 測試不以目標函式替身取代 preflight；只以記憶體資料模擬原生註冊鏈及頁面鏈。
Lua 測試直接擷取打包 main.lua 的 entry_preflight，檢查不同攔截原因及舊檔保留情況。
已駐留的同 ID 應用將由 preflight 攔截，原本的舊圖示修復支線保留相容程式碼但不作為此次前置檢查的成功條件。
