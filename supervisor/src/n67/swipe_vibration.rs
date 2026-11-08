//! N67 scroll events only enqueue feedback. Tick performs the native request.
use crate::{fw_api,safe_ptr};
use core::ptr::read_volatile as rd;
use core::sync::atomic::{AtomicU32,Ordering};
static mut CONFIG:[u8;2]=[0;2];
static mut LOADED:bool=false;
static mut HOOKS:[u32;64]=[0;64];
static REQUEST:AtomicU32=AtomicU32::new(0);
static PENDING:AtomicU32=AtomicU32::new(0);
static mut LAST:u32=0;
static mut LAST_VALID:bool=false;
static mut TOP:u32=0;
static mut TOP_VALID:bool=false;
static mut SCAN_ROOT:u32=0;
static mut SCAN_TICKS:u32=0;
const PATH:&[u8]=b"/data/chaos/swipe_vib.cfg\0";
const TEMP:&[u8]=b"/data/chaos/n67-swipe.tmp\0";
pub fn toggle(k:usize){if k<2{REQUEST.store(k as u32+1,Ordering::Relaxed);}}
pub unsafe fn enabled(k:usize)->bool{load();CONFIG[k]!=0}
unsafe fn load(){
    if LOADED{return;}LOADED=true;
    let fd=fw_api::open(PATH.as_ptr(),1,0);if fd<0{return;}
    let mut b=[0u8;2];let mut n=0;
    while n<2{let k=fw_api::read(fd,b.as_mut_ptr().add(n),(2-n) as u32);if k<=0||k as usize>2-n{break;}n+=k as usize;}
    fw_api::close(fd);if n==2&&b[0]<=1&&b[1]<=1{CONFIG=b;}
}
unsafe fn save()->bool{
    let fd=fw_api::open(TEMP.as_ptr(),2|4|8,0o640);if fd<0{return false;}let mut n=0;
    while n<2{let k=fw_api::write(fd,CONFIG.as_ptr().add(n),(2-n) as u32);if k<=0||k as usize>2-n{fw_api::close(fd);return false;}n+=k as usize;}
    fw_api::close(fd)>=0&&fw_api::rename(TEMP.as_ptr(),PATH.as_ptr())==0
}
unsafe extern "C" fn event(e:u32){
    if !safe_ptr(e){return;}let o=rd((e+4) as *const u32);
    if !HOOKS.contains(&o){return;}
    let code=rd((e+8) as *const u8)&127;
    if code==35{for p in HOOKS.iter_mut(){if *p==o{*p=0;}}}
    // 0xc240b20 updates scroll offsets and sends raw event 11 at 0xc240b52.
    else if code==11&&CONFIG[0]!=0{PENDING.fetch_or(1,Ordering::Relaxed);}
}
unsafe fn hook_tree(o:u32,depth:u32,budget:&mut u32){
    if depth>14||*budget==0||!safe_ptr(o){return;}*budget-=1;
    let flags=rd((o+0x1c) as *const u32);if flags&1!=0{return;}
    let spec=rd((o+8) as *const u32);if !safe_ptr(spec){return;}
    if flags&16!=0&&!HOOKS.contains(&o){
        if let Some(i)=HOOKS.iter().position(|&p|p==0){
            let a=rd((spec+12) as *const u32);let n=rd((spec+26) as *const u8)&63;
            if n==0||safe_ptr(a){
                let found=(0..n as u32).any(|j|rd((a+12*j) as *const u32)==event as *const () as u32);
                if found||n<63&&fw_api::obj_add_event(o,event as *const () as u32,0,0)!=0{HOOKS[i]=o;}
            }
        }
    }
    let arr=rd(spec as *const u32);let n=rd((spec+4) as *const u32);
    if n>160||n>0&&!safe_ptr(arr){return;}
    for i in 0..n{let ch=rd((arr+4*i) as *const u32);if safe_ptr(ch)&&rd((ch+4) as *const u32)==o{hook_tree(ch,depth+1,budget);}}
}
pub unsafe fn tick(){
    load();
    let req=REQUEST.swap(0,Ordering::Relaxed);
    if req!=0{
        let k=(req-1) as usize;CONFIG[k]^=1;
        if !save(){CONFIG[k]^=1;crate::log::line("滑动震动开关保存失败");}
        PENDING.store(0,Ordering::Relaxed);crate::render_req(20);
    }
    if !fw_api::screen_is_on(){PENDING.store(0,Ordering::Relaxed);TOP_VALID=false;return;}
    let top=fw_api::top_app_id();
    if TOP_VALID&&TOP!=fw_api::HOME_APP_ID&&top==fw_api::HOME_APP_ID&&CONFIG[1]!=0{PENDING.fetch_or(2,Ordering::Relaxed);}
    TOP=top;TOP_VALID=true;
    if top==fw_api::HOME_APP_ID&&CONFIG[0]!=0{
        if let Some((_,root))=fw_api::top_page_root(){
            SCAN_TICKS=SCAN_TICKS.wrapping_add(1);
            if root!=SCAN_ROOT||SCAN_TICKS%10==0{
            SCAN_ROOT=root;let desktop=crate::background::desktop_container(root,0,&mut 256);
            if desktop!=0{hook_tree(desktop,0,&mut 256);}
            }
        }
    }
    let flags=PENDING.swap(0,Ordering::Relaxed);
    if flags==0||top!=fw_api::HOME_APP_ID{return;}
    let now=fw_api::uptime_ms();
    if LAST_VALID&&now.wrapping_sub(LAST)<200{return;}
    LAST=now;LAST_VALID=true;
    let _=fw_api::vibration_request(3);
}
