//! Append one native Settings entry; N67 has no system-update page.
use crate::{fw_api,safe_ptr};
use core::ptr::read_volatile as rd;
use core::sync::atomic::{AtomicU32,Ordering};
static mut ENABLED:[u8;2]=[1,0];
static mut LOADED:bool=false;
static mut ROW:u32=0;
static mut PARENT:u32=0;
static mut KEY:u32=0;
static mut SCAN_ROOT:u32=0;
static mut SCAN_TICKS:u32=0;
static REQUEST:AtomicU32=AtomicU32::new(0);
static mut TEXT:[u8;96]=[0;96];
const CFG:&[u8]=b"/data/chaos/native-entries.cfg\0";
const TMP:&[u8]=b"/data/chaos/native-entries.tmp\0";

unsafe fn load(){
    if LOADED{return;}LOADED=true;
    let fd=fw_api::open(CFG.as_ptr(),1,0);if fd<0{return;}
    let mut bytes=[0u8;2];let mut n=0;
    while n<2{let got=fw_api::read(fd,bytes.as_mut_ptr().add(n),(2-n) as u32);if got<=0||got as usize>2-n{break;}n+=got as usize;}
    fw_api::close(fd);
    if n==2&&bytes[0]<=1&&bytes[1]<=1{ENABLED=bytes;}
}
pub unsafe fn caption(kind:usize)->*const u8{
    load();let p=core::ptr::addr_of_mut!(TEXT) as *mut u8;let mut w=crate::W::new(p,96);
    w.s(if kind==0{"系统设置入口：".as_bytes()}else{"系统更新入口：".as_bytes()})
        .s(if ENABLED[kind]!=0{"开".as_bytes()}else{"关".as_bytes()});w.end();p
}
pub fn toggle(kind:usize){if kind==0{REQUEST.store(kind as u32+1,Ordering::Relaxed);}}
unsafe fn save()->bool{
    let fd=fw_api::open(TMP.as_ptr(),2|4|8,0o640);if fd<0{return false;}
    let mut n=0;
    while n<2{let got=fw_api::write(fd,ENABLED.as_ptr().add(n),(2-n) as u32);if got<=0||got as usize>2-n{fw_api::close(fd);return false;}n+=got as usize;}
    if fw_api::close(fd)<0{return false;}
    fw_api::rename(TMP.as_ptr(),CFG.as_ptr())==0
}
unsafe fn children(o:u32)->Option<(u32,u32)>{
    if !safe_ptr(o){return None;}let spec=rd((o+8) as *const u32);if !safe_ptr(spec){return None;}
    let arr=rd(spec as *const u32);let n=rd((spec+4) as *const u32);
    if n>160||n>0&&!safe_ptr(arr){None}else{Some((arr,n))}
}
unsafe fn text_is(o:u32,expected:&[u8])->bool{
    // Label class comes from the literal in lv_label_create at 0xc25ebd4.
    if rd(o as *const u32)!=0x2c6834b0{return false;}
    let p=rd((o+0x24) as *const u32);
    if !crate::plausible_ptr(p){return false;}
    for(i,&b)in expected.iter().enumerate(){if !crate::plausible_ptr(p+i as u32)||rd((p+i as u32) as *const u8)!=b{return false;}}
    rd((p+expected.len() as u32) as *const u8)==0
}
unsafe fn title(o:u32,depth:u32,budget:&mut u32)->Option<usize>{
    if depth>12||*budget==0||!safe_ptr(o){return None;}*budget-=1;
    for word in ["设置","設定","Settings"]{if text_is(o,word.as_bytes()){return Some(0);}}
    let(arr,n)=children(o)?;
    for i in 0..n{let ch=rd((arr+4*i) as *const u32);if safe_ptr(ch)&&rd((ch+4) as *const u32)==o{if let Some(k)=title(ch,depth+1,budget){return Some(k);}}}
    None
}
unsafe extern "C" fn event(e:u32){
    if !safe_ptr(e){return;}
    let current=rd((e+4) as *const u32);let code=rd((e+8) as *const u8)&127;
    if code==35{fw_api::forget_tree(current);if current==ROW{ROW=0;PARENT=0;}}
    else if code==7{fw_api::page_goto(fw_api::CHAOS_APP_ID<<16,0);}
}
unsafe fn retire(delete:bool){
    let row=ROW;ROW=0;PARENT=0;
    if delete&&safe_ptr(row){fw_api::system_settings_remove(row);}
}
pub unsafe fn tick(){
    if cfg!(feature="settings-egg"){egg_tick();return;}
    load();
    let a=REQUEST.swap(0,Ordering::Relaxed);
    if a!=0{
        SCAN_ROOT=0;
        let i=(a-1) as usize;ENABLED[i]^=1;
        if !save(){ENABLED[i]^=1;crate::log::line("系统入口设置保存失败");}
        else{crate::log::kv("系统入口开关",i as u32*10+ENABLED[i] as u32);}
        crate::render_req(crate::extra_pages::SETTINGS);
    }
    if !fw_api::screen_is_on(){return;}
    let Some((key,root))=fw_api::top_page_root()else{return;};
    if key>>16!=fw_api::SETTINGS_APP_ID{return;}
    if KEY==key&&safe_ptr(ROW)&&rd((ROW+4) as *const u32)==PARENT&&fw_api::descendant(root,ROW){
        if ENABLED[0]!=0{return;}
        retire(true);return;
    }
    if crate::ui_activity::scrolling(){return;}
    SCAN_TICKS=SCAN_TICKS.wrapping_add(1);
    if SCAN_ROOT==root&&SCAN_TICKS%20!=0{return;}
    SCAN_ROOT=root;
    ROW=0;PARENT=0;KEY=key;
    let Some(kind)=title(root,0,&mut 160)else{return;};
    let Some((arr,n))=children(root)else{return;};
    let mut content=0;let mut area=0i32;
    for i in 0..n{
        let ch=rd((arr+4*i) as *const u32);if !safe_ptr(ch)||rd((ch+4) as *const u32)!=root{continue;}
        let w=rd((ch+0x18) as *const i16) as i32-rd((ch+0x14) as *const i16) as i32+1;
        let h=rd((ch+0x1a) as *const i16) as i32-rd((ch+0x16) as *const i16) as i32+1;
        if w>=200&&h>=200&&w<=480&&h<=640&&w*h>area{content=ch;area=w*h;}
    }
    if content==0{return;}
    let Some((arr,n))=children(content)else{return;};
    let mut last=content;let mut previous=0;let mut operation=0;let mut operation_previous=0;let mut operation_before=0;
    for i in 0..n{let ch=rd((arr+i*4) as *const u32);if safe_ptr(ch)&&rd((ch+4) as *const u32)==content{
        if rd(ch as *const u32)==0x2c68da78{
            let label=rd((ch+0x50) as *const u32);
            if safe_ptr(label)&&["系统操作","系統操作","System operations","System Operations"].iter().any(|s|text_is(label,s.as_bytes())){
                operation=ch;operation_previous=last;operation_before=previous;
            }
            previous=if last==content{0}else{last};last=ch;}
        let Some(spec)=safe_ptr(ch).then(||rd((ch+8) as *const u32))else{continue;};
        if !safe_ptr(spec){continue;}
        let events=rd((spec+12) as *const u32);let count=rd((spec+26) as *const u8)&63;
        if count>0&&!safe_ptr(events){continue;}
        for j in 0..count as u32{
            if rd((events+12*j) as *const u32)==event as *const () as u32{
                ROW=ch;PARENT=content;
                if ENABLED[kind]==0{retire(true);}
                return;
            }
        }
    }}
    if ENABLED[kind]==0{return;}
    let row=if operation!=0{fw_api::system_settings_row(content,if operation_previous==content{operation}else{operation_previous},operation_before)}else{fw_api::system_settings_row(content,last,previous)};if row==0{return;}
    if fw_api::obj_add_event(row,event as *const () as u32,0,0)==0{fw_api::system_settings_remove(row);return;}
    if operation!=0{fw_api::system_settings_insert(row,operation);}
    ROW=row;PARENT=content;
}

static mut EGG_TARGET:u32=0;
static mut EGG_COUNT:u32=0;
static mut EGG_LAST:u32=0;
unsafe extern "C" fn egg_event(e:u32){
 if !safe_ptr(e){return;}let target=rd((e+4) as *const u32);let code=rd((e+8) as *const u8)&127;
 if target!=EGG_TARGET{return;}
 if code==35{EGG_TARGET=0;EGG_COUNT=0;return;}
 if code!=7{return;}
 let Some((key,root))=fw_api::top_page_root()else{return;};
 if key!=0x16001b||!fw_api::descendant(root,target){EGG_COUNT=0;return;}
 let now=fw_api::uptime_ms();if now.wrapping_sub(EGG_LAST)>1200{EGG_COUNT=0;}EGG_LAST=now;
 EGG_COUNT+=1;if EGG_COUNT>=5{EGG_COUNT=0;fw_api::page_goto(fw_api::CHAOS_APP_ID<<16,0);}
}
unsafe fn egg_tick(){
 if !fw_api::screen_is_on(){EGG_COUNT=0;return;}
 let Some((key,root))=fw_api::top_page_root()else{return;};
 if key!=0x16001b{EGG_COUNT=0;return;}
 let target=rd(0x200cd0bc as *const u32);
 if !safe_ptr(target)||rd(target as *const u32)!=0x2c6834b0||!fw_api::descendant(root,target){return;}
 if EGG_TARGET==target{return;}
 if fw_api::obj_add_event(target,egg_event as *const () as u32,0,0)!=0{
  EGG_TARGET=target;EGG_COUNT=0;fw_api::flags(target,true,2);
 }
}
