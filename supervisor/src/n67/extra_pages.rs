//! New N67 pages. Firmware file-page ID 14 is reserved and remains C-owned.
use crate::*;
use crate::page::Page;
use core::sync::atomic::{AtomicU32, Ordering};

pub const SETTINGS: usize = 15;
pub const LOG: usize = 16;
pub const ABOUT: usize = 17;
pub const LICENSE: usize = 18;
pub const MPL: usize = 19;
const _: () = assert!(PAGE_COUNT == 33);

pub struct FilesPage;
impl Page for FilesPage {
    fn fill_title(&self, p: *mut u8) { unsafe { put_str(p, "文件\0".as_bytes()); } }
    // File descriptors have C callbacks; reaching the Rust dispatcher is an error.
    fn render(&self, _: &PageCtx) -> PageResult { Err(PageError::ContentFailed) }
    fn on_click(&self, _: usize) {}
}
pub static FILES_PAGE: FilesPage = FilesPage;

pub struct SettingsPage;
impl Page for SettingsPage {
    fn fill_title(&self, p: *mut u8) { unsafe { put_str(p, "设置\0".as_bytes()); } }
    fn render(&self, c: &PageCtx) -> PageResult {
        unsafe { build_rows(c, c.title, &[
            (6, RowSpec::clickable("时间设置\0".as_bytes())),
            (7, RowSpec::clickable("日期设置\0".as_bytes())),
            (0, RowSpec::clickable("亮度控制\0".as_bytes())),
            (1, RowSpec::clickable("系统语言\0".as_bytes())),
            (5, RowSpec::clickable("震动测试\0".as_bytes())),
            (2, RowSpec::clickable("运行日志\0".as_bytes())),
            (3, RowSpec::clickable("终端\0".as_bytes())),
        ])?;
        let anchor=core::ptr::read_volatile(c.rows.add(3));
        let mut anchor=anchor;
        if !cfg!(feature="settings-egg"){
        anchor=build_rows(c,anchor,&[(9,RowSpec::clickable(if crate::launcher_entry::enabled(){"应用列表显示：开\0".as_bytes()}else{"应用列表显示：关\0".as_bytes()}))])?;
        for kind in 0..1{
            let p=crate::native_entries::caption(kind);let mut len=0;while *p.add(len)!=0{len+=1;}
            anchor=build_rows(c,anchor,&[(8+kind,RowSpec::clickable(core::slice::from_raw_parts(p,len+1)))])?;
        }
        }
        let anchor=build_rows(c,anchor,&[(10,RowSpec::clickable("系统关于页面修改\0".as_bytes()))])?;
        let anchor=build_rows(c,anchor,&[(11,RowSpec::clickable("文件管理\0".as_bytes()))])?;
        build_rows(c,anchor,&[(4,RowSpec::clickable("更多设置\0".as_bytes()))])?;
        }
        Ok(())
    }
    fn on_click(&self, i: usize) { unsafe { match i {
        0 => nav_goto(11, 0),
        1 => nav_goto(31,0),
        2 => nav_goto(LOG as u32, 0),
        3 => { crate::files::chaos_files_open(1); nav_goto(14, 0); },
        4 => nav_goto(32,0),
        5 => nav_goto(20, 0),
        6 => nav_goto(2,0),
        7 => nav_goto(3,0),
        8 => if !cfg!(feature="settings-egg"){crate::native_entries::toggle(0);},
        9 => if !cfg!(feature="settings-egg"){crate::launcher_entry::request_toggle();},
        10 => nav_goto(22,0),
        11 => {crate::files::chaos_files_open(0);nav_goto(14,0);},
        _ => {}
    } } }
}
pub static SETTINGS_PAGE: SettingsPage = SettingsPage;

static LOG_ACTION: AtomicU32 = AtomicU32::new(0);
static mut CLEAR_ARMED: bool = false;
static mut LOG_BUFFER: [u8; 8192] = [0; 8192];
static mut LOG_RESULT: &'static [u8] = b"\0";

pub unsafe fn enter(pid: usize) {
    crate::datetime_pages::enter(pid);
    crate::app_manager::enter(pid);
    crate::diagnostics::enter(pid);
    if pid==20 { VIBRATION_ACTION.store(0,Ordering::Relaxed); VIBRATION_RESULT=b"\0"; }
    if pid == LOG {
        CLEAR_ARMED = false;
        LOG_RESULT = b"\0";
        LOG_ACTION.store(0, Ordering::Relaxed);
    }
}

unsafe fn body(c: &PageCtx, anchor: u32, text: *const u8) -> PageResult {
    let o = fw_api::label_create(c.content);
    if o == 0 { return Err(PageError::ContentFailed); }
    let mut lines = 1i32;
    let mut columns = 0u32;
    for k in 0..8192 {
        let b = *text.add(k);
        if b == 0 { break; }
        if b == b'\n' { lines += 1; columns = 0; }
        else if b & 0xc0 != 0x80 {
            columns += if b < 128 { 1 } else { 2 };
            if columns > 20 { lines += 1; columns = 1; }
        }
    }
    fw_api::obj_set_size(o, 280, lines * 36 + 20);
    fw_api::obj_align_to(o, anchor, fw_api::align::OUT_BOTTOM_MID, 0, 12);
    fw_api::label_wrap(o);
    fw_api::label_set_text(o, text);
    Ok(())
}

pub struct LogPage;
impl Page for LogPage {
    fn fill_title(&self, p: *mut u8) { unsafe { put_str(p, "运行日志\0".as_bytes()); } }
    fn render(&self, c: &PageCtx) -> PageResult { unsafe {
        let mut anchor = build_rows(c, c.title, &[
            (0, RowSpec::clickable("刷新日志\0".as_bytes())),
            (1, RowSpec::clickable("清空日志\0".as_bytes())),
        ])?;
        if CLEAR_ARMED { anchor = build_rows(c, anchor, &[
            (2, RowSpec::clickable("确认清空日志\0".as_bytes())),
            (3, RowSpec::clickable("取消\0".as_bytes())),
        ])?; }
        let buf = core::ptr::addr_of_mut!(LOG_BUFFER) as *mut u8;
        let n = crate::log::recent(buf, 8191);
        *buf.add(n) = 0;
        if core::str::from_utf8(core::slice::from_raw_parts(buf, n)).is_err() {
            return body(c, anchor, "日志不是 UTF-8，请用文件管理查看\0".as_ptr());
        }
        body(c, anchor, if n == 0 { "暂无日志\0".as_ptr() } else { buf })
    } }
    fn on_click(&self, i: usize) {
        if i < 4 { LOG_ACTION.store(i as u32 + 1, Ordering::Relaxed); }
    }
    fn needs_tick(&self) -> bool { true }
    fn tick(&self) { unsafe {
        let action = LOG_ACTION.swap(0, Ordering::Relaxed);
        match action {
            0 => return,
            1 => {},
            2 => CLEAR_ARMED = true,
            3 if CLEAR_ARMED => {
                LOG_RESULT = if crate::log::clear() { "日志已清空\0".as_bytes() }
                    else { "清空失败\0".as_bytes() };
                CLEAR_ARMED = false;
                crate::notifications::request(LOG_RESULT);
            },
            4 => CLEAR_ARMED = false,
            _ => return,
        }
        render_req(LOG);
    } }
}
pub static LOG_PAGE: LogPage = LogPage;

pub struct AboutPage;
impl Page for AboutPage {
    fn fill_title(&self, p: *mut u8) { unsafe { put_str(p, if crate::diagnostics::DEBUG {"调试\0".as_bytes()}else{"关于\0".as_bytes()}); } }
    fn render(&self, c: &PageCtx) -> PageResult { unsafe {
        if crate::diagnostics::DEBUG {return crate::diagnostics::render(c);}
        // Same information hierarchy and native rows as the 10 Pro 1.0.8.
        build_rows(c,c.title,&[
            (0,RowSpec::tap("Chaos\0".as_bytes(),b"2.2-alpha.59-honeycomb6\0".as_ptr())),
            (9,RowSpec::display("编译时间\0".as_bytes(),include_bytes!("../../../n67/build-time.txt").as_ptr())),
            (1,RowSpec::display("运行固件\0".as_bytes(),b"9 Pro / N67 CN / 3.1.190\0".as_ptr())),
            (2,RowSpec::display("文华逸洋\0".as_bytes(),"开发者\0".as_ptr())),
            (3,RowSpec::display("IKUN_CXKPRO\0".as_bytes(),"开发者\0".as_ptr())),
            (4,RowSpec::display("谦虚的海鸥\0".as_bytes(),"开发者\0".as_ptr())),
            (5,RowSpec::display("@wzx\0".as_bytes(),"贡献者(fetch 实现)\0".as_ptr())),
            (10,RowSpec::display(b"meowl\0","移植\0".as_ptr())),
            (6,RowSpec::display("许可证\0".as_bytes(),b"AGPL-3.0\0".as_ptr())),
            (7,RowSpec::clickable("AGPL-3.0 许可\0".as_bytes())),
            (8,RowSpec::clickable("MPL-2.0 许可\0".as_bytes())),
        ])?;
        Ok(())
    } }
    fn on_click(&self, i: usize) { unsafe {
        if crate::diagnostics::DEBUG || i==0 {crate::diagnostics::click(i);return;}
        match i {
        7 => nav_goto(LICENSE as u32,0),
        8 => nav_goto(MPL as u32,0),
        _ => {}
    } } }
}
pub static ABOUT_PAGE: AboutPage = AboutPage;

pub struct LicensePage {
    id: usize,
    text: &'static [u8],
    offset: AtomicU32,
    action: AtomicU32,
}
static mut LICENSE_BUFFER: [u8; 1025] = [0; 1025];
fn end_of_chunk(text: &[u8], start: usize) -> usize {
    let limit = (start + 1024).min(text.len());
    if limit == text.len() { return limit; }
    match text[start..limit].iter().rposition(|&b| b == b'\n') {
        Some(k) => start + k + 1,
        None => limit,
    }
}
impl Page for LicensePage {
    fn fill_title(&self, p: *mut u8) { unsafe { put_str(p,
        if self.id == LICENSE { b"AGPL-3.0\0" } else { b"MPL-2.0\0" }); } }
    fn render(&self, c: &PageCtx) -> PageResult { unsafe {
        let start = (self.offset.load(Ordering::Relaxed) as usize).min(self.text.len());
        let end = end_of_chunk(self.text, start);
        let mut anchor = c.title;
        if start > 0 { anchor = build_rows(c, anchor, &[(0, RowSpec::clickable("上一页\0".as_bytes()))])?; }
        if end < self.text.len() { anchor = build_rows(c, anchor, &[(1, RowSpec::clickable("下一页\0".as_bytes()))])?; }
        let dst = core::ptr::addr_of_mut!(LICENSE_BUFFER) as *mut u8;
        core::ptr::copy_nonoverlapping(self.text.as_ptr().add(start), dst, end - start);
        *dst.add(end - start) = 0;
        body(c, anchor, dst)
    } }
    fn on_click(&self, i: usize) {
        if i <= 1 { self.action.store(i as u32 + 1, Ordering::Relaxed); }
    }
    fn needs_tick(&self) -> bool { true }
    fn tick(&self) { unsafe {
        let action = self.action.swap(0, Ordering::Relaxed);
        let start = self.offset.load(Ordering::Relaxed) as usize;
        let next = if action == 2 { end_of_chunk(self.text, start) }
        else if action == 1 {
            let mut prev = 0; let mut at = 0;
            while at < start { prev = at; at = end_of_chunk(self.text, at); }
            prev
        } else { return; };
        self.offset.store(next as u32, Ordering::Relaxed);
        render_req(self.id);
    } }
}
pub static LICENSE_PAGE: LicensePage = LicensePage {
    id: LICENSE, text: include_bytes!("../../../LICENSE"),
    offset: AtomicU32::new(0), action: AtomicU32::new(0),
};
pub static MPL_PAGE: LicensePage = LicensePage {
    id: MPL, text: include_bytes!("../../../licenses/MIBAND10PRO-TUNMODULE-MPL-2.0.txt"),
    offset: AtomicU32::new(0), action: AtomicU32::new(0),
};

pub struct VibrationPage;
static VIBRATION_ACTION: AtomicU32 = AtomicU32::new(0);
static mut VIBRATION_LAST: u32 = 0;
static mut VIBRATION_RESULT: &'static [u8] = b"\0";
static mut VIBRATION_DETAIL:[u8;192]=[0;192];
impl Page for VibrationPage {
    fn fill_title(&self, p:*mut u8) { unsafe { put_str(p,"震动测试\0".as_bytes()); } }
    fn render(&self,c:&PageCtx)->PageResult { unsafe {
        build_rows(c,c.title,&[
            (0,RowSpec::clickable("测试系统效果 1\0".as_bytes())),
            (1,RowSpec::clickable("测试系统效果 3\0".as_bytes())),
            (2,RowSpec::clickable(if crate::swipe_vibration::enabled(0){"滑动列表震动：开\0".as_bytes()}else{"滑动列表震动：关\0".as_bytes()})),
            (3,RowSpec::clickable(if crate::swipe_vibration::enabled(1){"返回桌面震动：开\0".as_bytes()}else{"返回桌面震动：关\0".as_bytes()})),
        ])?;
        Ok(())
    } }
    fn on_click(&self,i:usize) {
        if i<2 { VIBRATION_ACTION.store(if i==0{1}else{3},Ordering::Relaxed); }
        else if i==2||i==3 {crate::swipe_vibration::toggle(i-2); }
    }
    fn needs_tick(&self)->bool { true }
    fn tick(&self) { unsafe {
        let effect=VIBRATION_ACTION.swap(0,Ordering::Relaxed);
        if effect==0 { return; }
        let now=fw_api::uptime_ms();
        if VIBRATION_LAST!=0 && now.wrapping_sub(VIBRATION_LAST)<800 { return; }
        VIBRATION_LAST=now;
        let rc=fw_api::vibration_request(effect as u8);
        let p=core::ptr::addr_of_mut!(VIBRATION_DETAIL) as *mut u8;
        let mut w=W::new(p,192);
        if rc<0{
            let reason=fw_api::vibration_failure(rc);w.s(&reason[..reason.len()-1]);
            w.s(b" (rc=-").n(rc.unsigned_abs()).s(b")");
        }else{w.s("请求已提交，未检测实际震动".as_bytes());}
        w.end();VIBRATION_RESULT=core::slice::from_raw_parts(p,w.len()+1);crate::notifications::request(VIBRATION_RESULT);
        crate::log::kv("震动效果",effect);
        crate::log::kv(if rc<0{"震动失败码"}else{"震动请求编号"},rc.unsigned_abs());
        render_req(20);
    } }
}
pub static VIBRATION_PAGE: VibrationPage=VibrationPage;
