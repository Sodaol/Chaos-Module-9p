//! Chaos messages use the stock incoming-message notification manager.
use crate::*;
use core::sync::atomic::{AtomicU32,Ordering};
const CAP:usize=192;
static mut PENDING:[u8;CAP]=[0;CAP];
static mut ACTIVE:[u8;CAP]=[0;CAP];
static LEN:AtomicU32=AtomicU32::new(0);
static mut INSTALL_BASE:u32=0;
static mut INSTALL_STABLE:u32=0;
static mut INSTALL_DONE:bool=false;
static mut INSTALL_MSG:[u32;22]=[0;22];
pub unsafe fn bind(base:u32){INSTALL_BASE=base;}
static mut MESSAGE_ID:u32=1;
unsafe fn send_system(text:*const u8,id:u32){
    INSTALL_MSG=[0;22];INSTALL_MSG[0]=0x41484301;INSTALL_MSG[1]=0x4e37534f;INSTALL_MSG[2]=id;
    INSTALL_MSG[3]=b"Chaos\0".as_ptr() as u32;INSTALL_MSG[4]=b"Chaos\0".as_ptr() as u32;
    INSTALL_MSG[5]=text as u32;
    INSTALL_MSG[7]=b"/data/chaos/chaos_icon.bin\0".as_ptr() as u32;
    INSTALL_MSG[8]=b"/data/chaos/chaos_settings_icon.bin\0".as_ptr() as u32;INSTALL_MSG[20]=1;
    let insert:unsafe extern "C" fn(*const u32)=core::mem::transmute(0x0c4f1f29usize);
    insert(core::ptr::addr_of!(INSTALL_MSG) as *const u32);
}
unsafe fn installed_tick(){
    if INSTALL_DONE||INSTALL_BASE==0||!fw_api::screen_is_on(){return;}
    let find:unsafe extern "C" fn(u32)->u32=core::mem::transmute(0x0c4467b5usize);
    let page:unsafe extern "C" fn(u32)->u32=core::mem::transmute(0x0c448749usize);
    let node=find(0xe7d4);
    let mut ready=safe_ptr(node)&&core::ptr::read_volatile((node+0x10) as *const u16)==0xe7d4;
    for i in 0..PAGE_COUNT{let expected=if i==0{INSTALL_BASE+0x40}else{INSTALL_BASE+0x1000+(i as u32-1)*112};
        if page(0xe7d40000|i as u32)!=expected{ready=false;break;}}
    if !ready{INSTALL_STABLE=0;return;}INSTALL_STABLE+=1;if INSTALL_STABLE<3{return;}
    INSTALL_DONE=true; // The native notification service may synchronously re-enter UI work.
    send_system("Chaos 已安装！\0".as_bytes().as_ptr(),1);
}
// UI callbacks/timers share one UI thread. Copy transient page buffers now;
// defer every firmware UI operation until the normal resident timer.
pub unsafe fn request(text:&[u8]){
    let mut n=text.iter().position(|&c|c==0).unwrap_or(text.len()).min(CAP-1);
    while n>0&&core::str::from_utf8(&text[..n]).is_err(){n-=1;}
    if n==0{return;}
    core::ptr::copy_nonoverlapping(text.as_ptr(),core::ptr::addr_of_mut!(PENDING) as *mut u8,n);
    PENDING[n]=0;LEN.store(n as u32,Ordering::Release);
}
pub unsafe fn tick(){
    installed_tick();
    let n=LEN.swap(0,Ordering::AcqRel) as usize;if n==0{return;}
    if !fw_api::screen_is_on()||APP_FG==0||fw_api::top_app_id()!=fw_api::CHAOS_APP_ID{return;}
    core::ptr::copy_nonoverlapping(core::ptr::addr_of!(PENDING) as *const u8,core::ptr::addr_of_mut!(ACTIVE) as *mut u8,n+1);
    MESSAGE_ID=MESSAGE_ID.wrapping_add(1).max(2);
    send_system(core::ptr::addr_of!(ACTIVE) as *const u8,MESSAGE_ID);
}
