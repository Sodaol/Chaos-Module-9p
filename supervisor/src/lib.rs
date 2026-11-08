//! chaos_sup 完整 supervisor（/dev/chaos + 1CHS + 软浮点 + register_driver + cmd_install）
//! 关键：register_app 内部 malloc/memset 是 thunk→段B(LVGL)，需 fops.write 上下文。

#![no_std]
#![no_main]
#![allow(static_mut_refs)]

#[cfg(feature="n67")]
mod files;
#[cfg(feature="n67")]
#[path="n67/ui_activity.rs"]
mod ui_activity;
#[cfg(feature="n67")]
#[path="n67/launcher_entry.rs"]
mod launcher_entry;
#[cfg(feature="n67")]
#[path="n67/beautify_restore.rs"]
mod beautify_restore;
#[cfg(feature="n67")]
#[path="n67/desktop_scale.rs"]
mod desktop_scale;
#[cfg(feature="n67")]
#[path="n67/keyboard.rs"]
mod keyboard;
#[cfg(feature="n67")]
#[path="n67/system_custom.rs"]
mod system_custom;
#[cfg(feature="n67")]
#[path="n67/system_language.rs"]
mod system_language;
#[cfg(feature="n67")]
use system_custom::{system_version,system_text,device_name,device_model};
mod state;
pub(crate) use state::*;

#[cfg(not(feature = "n67"))]
mod font_apply;
#[cfg(feature = "n67")]
#[path = "n67/font_apply.rs"]
mod font_apply;
mod font_list;
#[cfg(not(feature = "n67"))]
mod font_hot;
#[cfg(feature = "n67")]
#[path = "n67/font_hot_checked.rs"]
mod font_hot;
mod icon_apply;
#[cfg(not(feature = "n67"))]
mod res_hook;
#[cfg(feature = "n67")]
#[path = "n67/res_hook.rs"]
mod res_hook;
mod confirm_pop;
#[cfg(feature="n67")]
#[path="n67/log.rs"]
mod log;
#[cfg(feature="n67")]
#[path="n67/extra_pages.rs"]
mod extra_pages;
#[cfg(feature="n67")]
#[path="n67/time_set.rs"]
mod time_set;
#[cfg(feature="n67")]
#[path="n67/datetime_pages.rs"]
mod datetime_pages;
#[cfg(feature="n67")]
#[path="n67/notifications.rs"]
mod notifications;
#[cfg(feature="n67")]
#[path="n67/app_manager.rs"]
mod app_manager;
#[cfg(feature="n67")]
#[path="n67/app_metadata.rs"]
mod app_metadata;
#[cfg(feature="n67")]
#[path="n67/native_entries.rs"]
mod native_entries;
#[cfg(feature="n67")]
#[path="n67/delivery_compat.rs"]
mod delivery_compat;
#[cfg(feature="n67")]
#[path="n67/gh225.rs"]
mod gh225;
#[cfg(feature="n67")]
#[path="n67/backdrop_render.rs"]
mod backdrop_render;
#[cfg(feature="n67")]
#[path="n67/background.rs"]
mod background;
#[cfg(feature="n67")]
#[path="n67/shake_probe.rs"]
mod shake_probe;
#[cfg(feature="n67")]
#[path="n67/accel_shake.rs"]
mod accel_shake;
#[cfg(feature="n67")]
#[path="n67/swipe_vibration.rs"]
mod swipe_vibration;
#[cfg(feature="n67")]
#[path="n67/diagnostics.rs"]
mod diagnostics;

mod text;
mod explorer;
mod watchface;
mod page;
mod ui;
#[cfg(not(feature = "n67"))]
mod ipc;
#[cfg(feature = "n67")]
#[path = "n67/ipc.rs"]
mod ipc;
pub(crate) use text::*;
pub(crate) use explorer::*;
pub(crate) use watchface::*;
pub(crate) use page::*;
pub(crate) use ui::*;
pub(crate) use ipc::*;

// 已验证固件 API 封装层(新界面一律走这里, 不再写裸 transmute)
#[cfg(not(feature = "n67"))]
mod fw_api;
#[cfg(feature = "n67")]
#[path = "n67/fw_api.rs"]
mod fw_api;
#[macro_use]
mod mem;
pub(crate) use mem::{plausible_ptr, safe_ptr};

use core::ptr::{read_volatile, write_volatile};



type FnLookup = unsafe extern "C" fn(u32) -> *mut u8;
type FnInstall = unsafe extern "C" fn(*const u32, *const u32, u32) -> i32;
type FnInitBuffer = unsafe extern "C" fn(u32) -> *mut u8;























































// 与固件自带模块的 ROW_CALLBACK 宏等价: 每行独立回调, 把行号固化进回调本身。
// 新增槽位时必须同时补 `chaos_row_cb!(...)` 与 `row_ev_fn` 的分支,
// 且**禁止在 dispatch 里写 `_ => ev9` 这类 catch-all** —— 槽位布局一变就会静默错配
// (踩过的坑: slot10「返回」拿到 ev9 的回调, 被当成「更多」派发)。
macro_rules! chaos_row_cb {
    ($name:ident, $idx:expr) => {
        #[no_mangle]
        unsafe extern "C" fn $name(event: u32) -> u32 { chaos_row_dispatch($idx, event) }
    };
}
chaos_row_cb!(chaos_row_ev0, 0);
chaos_row_cb!(chaos_row_ev1, 1);
chaos_row_cb!(chaos_row_ev2, 2);
chaos_row_cb!(chaos_row_ev3, 3);
chaos_row_cb!(chaos_row_ev4, 4);
chaos_row_cb!(chaos_row_ev5, 5);
chaos_row_cb!(chaos_row_ev6, 6);
chaos_row_cb!(chaos_row_ev7, 7);
chaos_row_cb!(chaos_row_ev8, 8);
chaos_row_cb!(chaos_row_ev9, 9);
chaos_row_cb!(chaos_row_ev10, 10);   // slot10 = 返回行(表盘页/轮换页)
chaos_row_cb!(chaos_row_ev11, 11);











// 模块加载即执行的构造(instream: Vela 的 insmod 会对 init_array 调一次):
// 铺 fops 四件套(open/close/read/write) + 版本字, 然后向固件注册设备节点。
// register_driver 的四参(path, fops, mode, priv)是这套内核对**所有**设备驱动
// 的通行入口约定, 0x1B6 = 0666 权限位 —— 固件自带模块全部这么传。
#[no_mangle]
#[cfg(not(feature = "n67"))]
unsafe extern "C" fn chaos_ctor() {
    if st_rd!(CTOR_DONE) != 0 {
        return;
    }
    st_wr!(CTOR_DONE, 1);

    let fp = core::ptr::addr_of_mut!(FOPS) as *mut u32;
    write_volatile(fp, chaos_open as *const () as u32);
    write_volatile(fp.add(1), chaos_close as *const () as u32);
    write_volatile(fp.add(2), chaos_read as *const () as u32);
    write_volatile(fp.add(3), chaos_write as *const () as u32);
    fops_wr(FOPS_VER, STAT_VERSION);
    let register: unsafe extern "C" fn(*const u8, *const u8, u32, u32) -> u32 =
        core::mem::transmute(FW_REGISTER_DRIVER as usize);
    let registered = register(
        core::ptr::addr_of!(DEV_PATH) as *const u8,
        fp as *const u8,
        0x1B6,
        0,
    );
    // 返回 0 才算注册成功, 与固件自带模块的"已注册"标志同一套语义
    if registered == 0 {
        st_wr!(DRIVER_ON, 1);
    }
}

// 析构必须幂等: Vela 的 insmod 会对 fini_array 立即调一次, 卸载时再调一次。
// 只有真正注册过(DRIVER_ON==1)才做反注册并清标志。
#[no_mangle]
#[cfg(not(feature = "n67"))]
unsafe extern "C" fn chaos_dtor() {
    if st_rd!(DRIVER_ON) != 1 {
        return;
    }
    let unregister: unsafe extern "C" fn(*const u8) -> i32 =
        core::mem::transmute(FW_UNREGISTER_DRIVER as usize);
    unregister(core::ptr::addr_of!(DEV_PATH) as *const u8);
    st_wr!(DRIVER_ON, 0);
}



#[no_mangle]
#[cfg(not(feature = "n67"))]
pub extern "C" fn module_main() -> i32 {
    unsafe { chaos_ctor(); }
    0
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! { loop {} }
