//! N67 uses the existing RAM registrar, not insmod or a synthetic device driver.
use crate::*;
#[no_mangle]
pub unsafe extern "C" fn chaos_n67_init(base: u32, gesture: u32, event_bubble: u32, press_lock: u32) -> u32 {
    fw_api::set_flags(gesture,event_bubble,press_lock);
    APP_ID = 0xE7D4;
    crate::diagnostics::bind(base);
    crate::notifications::bind(base);
    crate::launcher_entry::bind(base);
    LANG = 1;
    crate::files::chaos_files_flags(gesture,press_lock);
    SHAKE_EN = 0; // User enables the N67 gesture subscription explicitly.
    let names: [*const u8; PAGE_COUNT] = [PAGE_MAIN.as_ptr(),PAGE_DIR0.as_ptr(),PAGE_DIR1.as_ptr(),PAGE_DIR2.as_ptr(),PAGE_DIR3.as_ptr(),PAGE_TXTSUB.as_ptr(),PAGE_ICONSUB.as_ptr(),PAGE_VIEWR.as_ptr(),PAGE_WFACES.as_ptr(),PAGE_ROT.as_ptr(),PAGE_MGR.as_ptr(),PAGE_BRIGHT.as_ptr(),PAGE_PET.as_ptr(),PAGE_FONTD.as_ptr(), b"files_native\0".as_ptr(), b"settings\0".as_ptr(), b"log\0".as_ptr(), b"about\0".as_ptr(), b"agpl\0".as_ptr(), b"mpl\0".as_ptr(), b"vibration\0".as_ptr(), b"blur_zones\0".as_ptr(),b"system_about\0".as_ptr(),b"system_version\0".as_ptr(),b"system_text\0".as_ptr(),b"device_name\0".as_ptr(),b"device_model\0".as_ptr(),b"keyboard\0".as_ptr(),b"app_list\0".as_ptr(),b"app_detail\0".as_ptr(),b"app_batch\0".as_ptr(),b"language\0".as_ptr(),b"device_options\0".as_ptr()];
    for pid in 0..PAGE_COUNT {
        if pid==14 { continue; }
        let p = if pid == 0 { base+0x40 } else { base+0x1000+(pid as u32-1)*112 };
        core::ptr::write_volatile((base+0x800+pid as u32*4) as *mut u32,p);
        for (off,value) in [(0x10,names[pid] as u32),(0x14,(APP_ID<<16)|pid as u32),(0x24,0x00020404),(0x30,chaos_on_signal as *const () as u32),(0x48,chaos_on_create as *const () as u32),(0x4c,chaos_on_resume as *const () as u32),(0x54,chaos_on_pause as *const () as u32),(0x60,chaos_on_ui_destroy as *const () as u32)] {
            core::ptr::write_volatile((p+off) as *mut u32,value);
        }
    }
    let p=base+0x1000+13*112;
    core::ptr::write_volatile((base+0x800+14*4) as *mut u32,p);
    for (off,value) in [(0x10,b"files_native\0".as_ptr() as u32),(0x14,(APP_ID<<16)|14),(0x24,0x00020404),
        (0x30,crate::files::chaos_files_signal as *const () as u32),(0x48,crate::files::chaos_files_create as *const () as u32),
        (0x4c,crate::files::chaos_files_resume as *const () as u32),(0x54,crate::files::chaos_files_pause as *const () as u32),
        (0x60,crate::files::chaos_files_destroy as *const () as u32)] {
        core::ptr::write_volatile((p+off) as *mut u32,value);
    }
    // Registrar verification checks the first page and its numeric key.
    core::ptr::write_volatile((base+0x11c) as *mut u32,APP_ID<<16);
    core::ptr::write_volatile((base+0x114) as *mut u32,base+0x800);
    crate::log::line("Chaos N67 2.2-alpha.60-honeycomb7 初始化");
    shake_arm();
    0x4e363743
}
pub(crate) unsafe fn file_open_ro(p:*const u8)->i32 {fw_api::open(p,1,0)}
pub(crate) unsafe fn file_close(fd:i32){fw_api::close(fd);}
