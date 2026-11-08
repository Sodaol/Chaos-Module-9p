//! N67 font manager has native path registrations at manager+0x18.
use crate::{fw_api,mem::{rd32,rd8},safe_ptr};
pub const FONT_SLOT_MAX:u32=8;
static mut LIVE:u32=0;static mut PENDING:u32=0;static mut REVERT:u32=0;
static PATHS:[&[u8];9]=[b"/data/chaos/font/st0.ttf\0",b"/data/chaos/font/st1.ttf\0",b"/data/chaos/font/st2.ttf\0",b"/data/chaos/font/st3.ttf\0",b"/data/chaos/font/st4.ttf\0",b"/data/chaos/font/st5.ttf\0",b"/data/chaos/font/st6.ttf\0",b"/data/chaos/font/st7.ttf\0",b"/data/chaos/font/st8.ttf\0"];
#[derive(Copy,Clone)]struct Face{slot:u32,size:u32,face:u32,name:[u8;32]}
const EMPTY:Face=Face{slot:0,size:0,face:0,name:[0;32]};
static mut FACES:[Face;96]=[EMPTY;96];
pub unsafe fn live_get()->u32{LIVE}
pub unsafe fn path_of(s:u32)->*const u8{PATHS[s.min(8) as usize].as_ptr()}
pub unsafe fn pending_get()->u32{PENDING}
pub unsafe fn set_pending(s:u32)->bool{if !valid_ttf(s){return false;}PENDING=s;crate::beautify_restore::remember_font(s);true}
pub unsafe fn cancel_pending(s:u32){if PENDING==s{PENDING=0;}}
pub unsafe fn quiet()->bool{PENDING==0&&REVERT==0}
pub unsafe fn busy()->bool{!quiet()}
pub unsafe fn pending()->bool{busy()}
pub unsafe fn revert_busy()->u32{REVERT}
pub unsafe fn request_revert(){PENDING=0;REVERT=1;crate::beautify_restore::remember_font(0);}
pub unsafe fn clear_live(){LIVE=0;}
// Native font objects can read their TTF again. Keep every parsed slot on disk
// until reboot, including slots which are no longer selected.
pub unsafe fn slot_cached(s:u32)->bool{FACES.iter().any(|f|f.slot==s)}
pub unsafe fn valid_ttf(s:u32)->bool{
    if s<1||s>8{return false;}
    let fd=fw_api::open(path_of(s),1,0);if fd<0{return false;}
    let mut b=[0u8;12];let n=fw_api::read(fd,b.as_mut_ptr(),12);fw_api::close(fd);
    n==12 && (b[..4]==[0,1,0,0]||b[..4]==*b"OTTO") && u16::from_be_bytes([b[4],b[5]])>0 && u16::from_be_bytes([b[4],b[5]])<=256
}
pub unsafe fn file_exists(s:u32)->bool{let fd=fw_api::open(path_of(s),1,0);if fd<0{false}else{fw_api::close(fd);true}}
pub unsafe fn manager_ready()->bool{safe_ptr(rd32(0x200bfc6c as *const u32))}
pub unsafe fn tick(){
    if REVERT!=0{if !super::font_hot::revert_all(){return;}LIVE=0;REVERT=0;}
    if PENDING!=0{
        if !valid_ttf(PENDING){PENDING=0;crate::render_req(5);return;}
        if !super::font_hot::revert_all(){return;}LIVE=PENDING;PENDING=0;crate::render_req(5);
    }
}
pub unsafe fn cch_face_for_size(size:u32)->u32 {
    if LIVE==0{return 0;}
    if let Some(f)=FACES.iter().find(|f|f.slot==LIVE&&f.size==size){return f.face;}
    ensure_face_for_size(size)
}
pub unsafe fn ensure_face_for_size(size:u32)->u32{
    if LIVE==0||size<8||size>120||!manager_ready(){return 0;}
    if let Some(f)=FACES.iter().find(|f|f.slot==LIVE&&f.size==size){return f.face;}
    let Some(i)=FACES.iter().position(|f|f.slot==0) else{return 0;};
    FACES[i].name[..11].copy_from_slice(b"ChaosN67-S0");FACES[i].name[10]=b'0'+LIVE as u8;
    let name=FACES[i].name.as_ptr();
    // The list uses an 8-byte payload and next at +12; validate before allocation.
    let fm=rd32(0x200bfc6c as *const u32);if rd32((fm+0x18) as *const u32)!=8{return 0;}
    let mut node=rd32((fm+0x1c) as *const u32);let mut found=false;let mut count=0;let mut prev=0;
    while node!=0{if !safe_ptr(node)||count>=160||rd32((node+8) as *const u32)!=prev{return 0;}count+=1;let p=rd32(node as *const u32);if safe_ptr(p){let mut equal=true;for k in 0..12{if rd8((p+k) as *const u8)!=FACES[i].name[k as usize]{equal=false;break;}}if equal{found=true;}}prev=node;node=rd32((node+12) as *const u32);}
    if rd32((fm+0x20) as *const u32)!=prev{return 0;}
    if !found{let f:unsafe extern "C" fn(u32)->u32=core::mem::transmute(0x0c257e95usize);let nm=fw_api::fw_str_dup(name);let path=fw_api::fw_str_dup(path_of(LIVE));if nm==0||path==0{if nm!=0{fw_api::fw_free(nm);}if path!=0{fw_api::fw_free(path);}return 0;}let nd=f(fm+0x18);if !safe_ptr(nd){fw_api::fw_free(nm);fw_api::fw_free(path);return 0;}core::ptr::write_volatile(nd as *mut u32,nm);core::ptr::write_volatile((nd+4) as *mut u32,path);}
    let face=fw_api::fw_mfont_create_named(name,size,400);
    if !safe_ptr(face){return 0;}
    FACES[i].slot=LIVE;FACES[i].size=size;FACES[i].face=face;face
}

pub unsafe fn restore_selection(s:u32)->bool{
 if busy(){return false;}
 if s==0{return true;}
 if !valid_ttf(s){return false;}PENDING=s;true
}
