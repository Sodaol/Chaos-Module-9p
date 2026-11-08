//! LVGL 8: 28-byte font body, wrapper record pointer +28. GUI thread only.
//! Re-enumerate both lists before every write; no retained traversal cursor.
use crate::{safe_ptr,mem::{rd32,rd16,rd8},fw_api};
#[derive(Copy,Clone)]struct Saved{record:u32,font:u32,size:u32,body:[u32;7],applied:[u32;7]}
const EMPTY:Saved=Saved{record:0,font:0,size:0,body:[0;7],applied:[0;7]};
static mut SAVED:[Saved;160]=[EMPTY;160];
static mut CUR:usize=0;static mut PASSES:u32=0;static mut CHANGED:u32=0;static mut ERROR:u32=0;
unsafe fn family(p:u32)->bool{
    if !crate::plausible_ptr(p){return false;}
    let mut b=[0u8;32];
    for i in 0..32{b[i]=rd8((p+i as u32) as *const u8);if b[i]==0{break;}}
    // 系统设置等页面还会用 MiSans-Medium / MiSans-Light 等族名；只匹配
    // Regular/All 会让这些已注册的系统页面继续显示原字体。运动、白晶及泰文字体
    // 有专用字形，保留原样，避免把图标或非拉丁字形换成用户字体。
    b.starts_with(b"MiSans-")
        && !b.windows(5).any(|w|w==b"Sport")
        && !b.windows(4).any(|w|w==b"BaiJ")
        && !b.windows(4).any(|w|w==b"Thai")
}
unsafe fn enumerate(head:u32,link:u32,out:&mut [u32])->Option<usize>{
    if rd32(head as *const u32)!=link{return None;}
    let mut n=0;let mut prev=0;let mut p=rd32((head+4) as *const u32);
    while p!=0{if !safe_ptr(p)||n>=out.len()||rd32((p+link) as *const u32)!=prev{return None;}out[n]=p;n+=1;prev=p;p=rd32((p+link+4) as *const u32);}
    if rd32((head+8) as *const u32)!=prev{return None;}Some(n)
}
unsafe fn lists(r:&mut [u32;160],w:&mut [u32;512])->Option<(usize,usize)>{
    let fm=rd32(0x200bfc6c as *const u32);if !safe_ptr(fm){return None;}
    Some((enumerate(fm,48,r)?,enumerate(fm+12,32,w)?))
}
unsafe fn body(p:u32)->[u32;7]{let mut b=[0;7];for k in 0..7{b[k]=rd32((p+k as u32*4) as *const u32);}b}
unsafe fn copies(rec:u32,font:u32,src:&[u32;7],wrappers:&[u32]){
    for k in 0..7{core::ptr::write_volatile((font as *mut u32).add(k),src[k]);}
    for &w in wrappers{if rd32((w+28) as *const u32)==rec{for k in 0..7{core::ptr::write_volatile((w as *mut u32).add(k),src[k]);}}}
}
pub unsafe fn revert_all()->bool{
    let mut r=[0;160];let mut w=[0;512];let Some((nr,nw))=lists(&mut r,&mut w)else{ERROR=312;return false;};
    for i in 0..160{let s=SAVED[i];
        if s.record!=0 && r[..nr].contains(&s.record) && rd32(s.record as *const u32)==s.font && safe_ptr(s.font) && rd16((s.record+8) as *const u16) as u32==s.size && body(s.font)==s.applied{copies(s.record,s.font,&s.body,&w[..nw]);}
        SAVED[i]=EMPTY;
    }CUR=0;true
}
pub unsafe fn tick(){if crate::ui_activity::scrolling(){return;}if !fw_api::screen_is_on()||crate::font_apply::live_get()==0{return;}
    let mut r=[0;160];let mut w=[0;512];let Some((nr,_))=lists(&mut r,&mut w)else{ERROR=312;return;};
    if CUR>=nr{CUR=0;PASSES=PASSES.wrapping_add(1);}if nr==0{return;}
    let node=r[CUR];CUR+=1;let name=rd32((node+4) as *const u32);if !family(name){return;}
    let font=rd32(node as *const u32);let size=rd16((node+8) as *const u16) as u32;
    if !safe_ptr(font)||size<8||size>120{return;}
    if rd16((font+8) as *const u16)==0||rd16((font+8) as *const u16)>180{ERROR=314;return;}
    let f=crate::font_apply::ensure_face_for_size(size);if !safe_ptr(f){ERROR=315;return;}
    // Creating a custom face modifies these lists; validate the NEW lists first.
    let Some((nr,nw))=lists(&mut r,&mut w)else{ERROR=312;return;};
    if !r[..nr].contains(&node)||rd32(node as *const u32)!=font{return;}
    let now=body(font);let src=body(f);
    if now==src{return;}
    let i=if let Some(i)=SAVED.iter().position(|s|s.record==node){
        if SAVED[i].font!=font||SAVED[i].size!=size||now!=SAVED[i].applied{SAVED[i]=EMPTY;return;}i
    }else{let Some(i)=SAVED.iter().position(|s|s.record==0)else{ERROR=316;return;};SAVED[i]=Saved{record:node,font,size,body:now,applied:src};i};
    SAVED[i].applied=src;copies(node,font,&src,&w[..nw]);CHANGED=CHANGED.wrapping_add(1);
}
pub unsafe fn readout()->(u32,u32,u32,u32,u32,u32){(PASSES,CHANGED,ERROR,CUR as u32,0,0)}
pub unsafe fn probe_run(){CUR=0;}
