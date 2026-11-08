//! N67 LVGL8 backdrop: owned BGRA buffers, bounded software blur, reversible styles.
use crate::*;
use crate::page::Page;
use core::ptr::{read_volatile as rd};
use core::sync::atomic::{AtomicU32,Ordering};
use crate::backdrop_render::Renderer;
const W:usize=336;const H:usize=480;const BYTES:usize=W*H*4;
const FILE:&[u8]=b"/data/chaos/background.bin\0";
const CACHE:&[u8]=b"/data/chaos/n67-background-cache.bin\0";
const CACHE_TMP:&[u8]=b"/data/chaos/n67-background-cache.tmp\0";
const CFG:&[u8]=b"/data/chaos/n67-backdrop.cfg\0";
const TEMP:&[u8]=b"/data/chaos/n67-backdrop.tmp\0";
static ACTION:AtomicU32=AtomicU32::new(0);
static mut CONFIG:[u8;8]=*b"BG01\0\x0f\0\0"; // mode, zone mask, auto, source
static mut LOADED:bool=false;
static mut ACTIVATED:bool=false;
static mut MESSAGE:&'static [u8]=b"\0";
static mut TEXT:[u8;128]=[0;128];
static mut RAW:u32=0;
static mut OUTPUT:[u32;2]=[0;2];
static mut DESC:[[u32;3];2]=[[0;3];2];
static mut CURRENT:usize=0;
static mut HAVE:bool=false;
static mut RAW_VALID:bool=false;
static mut CACHE_DIRTY:bool=false;
static mut TARGET:usize=0;
static mut STAGE:u8=0; // 0 idle, 1 wait face, 2 read, 3 render, 6 cache commit
static mut FD:i32=-1;
static mut AT:usize=0;
static mut JOB:Renderer=Renderer::new();
static mut LAST_FACE:u32=0;
static mut LAST_FACE_TAG:u32=0;
unsafe fn face_tag()->u32{
 // The native manager's current base-info (+68) stores the face ID at +8.
 // Include it because an engine may reuse the same current-face node address.
 let manager=rd(WF_MGR_PTR as *const u32);if !safe_ptr(manager){return 0;}
 let info=rd((manager+0x68) as *const u32);if !safe_ptr(info){return 0;}
 let mut h=2166136261u32;
 for i in 0..12{if !crate::plausible_ptr(info+8+i){return 0;}h=(h^rd((info+8+i) as *const u8) as u32).wrapping_mul(16777619);}h
}

static mut SCAN_ROOT:u32=0;
static mut SCAN_DESC:u32=0;
static mut SCAN_TICKS:u32=0;
#[derive(Clone,Copy)]
struct Journal{obj:u32,source:u32,opa:u32,last:u32}
const EMPTY:Journal=Journal{obj:0,source:0,opa:0,last:0};
static mut JOURNAL:[Journal;64]=[EMPTY;64];
unsafe fn load(){
    if LOADED{return;}LOADED=true;
    let fd=fw_api::open(CFG.as_ptr(),1,0);if fd<0{return;}
    let mut c=[0u8;8];let mut n=0;
    while n<8{let k=fw_api::read(fd,c.as_mut_ptr().add(n),(8-n) as u32);if k<=0||k as usize>8-n{break;}n+=k as usize;}
    fw_api::close(fd);
    if n==8&&&c[..4]==b"BG01"&&c[4]<=2&&c[5]<=15&&c[6]<=1&&c[7]<=1{
        CONFIG=c;if !crate::beautify_restore::background_enabled(){CONFIG[4]=0;}if CONFIG[4]!=0{begin(2);}
    }
}
unsafe fn save()->bool{
    let fd=fw_api::open(TEMP.as_ptr(),2|4,0o640);if fd<0{return false;}
    let mut n=0;
    while n<8{let k=fw_api::write(fd,CONFIG.as_ptr().add(n),(8-n) as u32);if k<=0||k as usize>8-n{fw_api::close(fd);return false;}n+=k as usize;}
    if fw_api::close(fd)<0{return false;}fw_api::rename(TEMP.as_ptr(),CFG.as_ptr())==0
}
unsafe fn cancel(){if FD>=0{fw_api::close(FD);FD=-1;}STAGE=0;AT=0;}
unsafe fn begin(stage:u8){
    if STAGE!=0{message("背景正在处理中\0".as_bytes());return;}
    if RAW==0{RAW=fw_api::heap_malloc(BYTES as u32);}
    TARGET=if HAVE{1-CURRENT}else{0};
    if OUTPUT[TARGET]==0{OUTPUT[TARGET]=fw_api::heap_malloc(BYTES as u32);}
    if RAW==0||OUTPUT[TARGET]==0{message("背景内存不足\0".as_bytes());return;}
    if stage==1||stage==2{RAW_VALID=false;CACHE_DIRTY=false;}
    JOB.reset(CONFIG[4]==2);
    STAGE=stage;AT=0;MESSAGE=if stage==1{"请回到表盘，等待生成\0".as_bytes()}else{"正在生成背景\0".as_bytes()};
}
unsafe fn children(o:u32)->Option<(u32,u32)>{
    let s=rd((o+8) as *const u32);if !safe_ptr(s){return None;}
    let a=rd(s as *const u32);let n=rd((s+4) as *const u32);
    if n>160||n>0&&!safe_ptr(a){None}else{Some((a,n))}
}
unsafe fn visible(o:u32)->bool{
    if !safe_ptr(o)||rd((o+0x1c) as *const u32)&1!=0{return false;}
    let x=rd((o+0x14) as *const i16) as i32;let y=rd((o+0x16) as *const i16) as i32;
    let r=rd((o+0x18) as *const i16) as i32;let b=rd((o+0x1a) as *const i16) as i32;
    x<336&&r>=0&&y<480&&b>=0
}
unsafe fn markers(o:u32,depth:u32,budget:&mut u32)->u32{
    if depth>14||*budget==0||!visible(o){return 0;}*budget-=1;let mut mask=if o==crate::honeycomb::chaos_honeycomb_overlay(){1}else{0};
    let mut class=rd(o as *const u32);let mut image=false;
    if class==0x2c69e840{mask|=1;}
    // N67 native watchface image widgets use memory descriptors, not paths.
    // Observed on the stock face and verified against the ROM class table.
    if class==0x2c759314{mask|=16;}
    for _ in 0..12{if class==0x2c6825bc{image=true;break;}if class&3!=0||!(0x2c080000..0x2c800000).contains(&class){break;}let next=rd(class as *const u32);if next==class{break;}class=next;}
    if image{
        let p=rd((o+36) as *const u32);let mut path=[0u8;160];let mut n=0;
        while n<160&&crate::plausible_ptr(p+n as u32){let c=rd((p+n as u32) as *const u8);if c==0{break;}if !(32..127).contains(&c){n=0;break;}path[n]=c;n+=1;}
        let s=&path[..n];
        if s.windows(10).any(|a|a==b"watchface/"){mask|=16;}
        if s.windows(15).any(|a|a==b"control_center/"){mask|=2;}
        if s.windows(6).any(|a|a==b"widget"){mask|=4;}
        if s.windows(12).any(|a|a==b"notification"){mask|=8;}
        if s.windows(8).any(|a|a==b"launcher")||s.windows(13).any(|a|a==b"/chaos/icons/"){mask|=1;}
    }
    if let Some((arr,n))=children(o){for i in 0..n{let ch=rd((arr+i*4) as *const u32);if safe_ptr(ch)&&rd((ch+4) as *const u32)==o{mask|=markers(ch,depth+1,budget);}}}
    mask
}
unsafe fn exact_screen(o:u32)->bool{
    rd((o+0x18) as *const i16) as i32-rd((o+0x14) as *const i16) as i32+1==336&&
    rd((o+0x1a) as *const i16) as i32-rd((o+0x16) as *const i16) as i32+1==480
}
unsafe fn face(o:u32,depth:u32,budget:&mut u32)->u32{
    if depth>12||*budget==0||!visible(o){return 0;}*budget-=1;
    if exact_screen(o)&&markers(o,0,&mut 256)==16{return o;}
    if let Some((arr,n))=children(o){for i in 0..n{let ch=rd((arr+i*4) as *const u32);if safe_ptr(ch)&&rd((ch+4) as *const u32)==o{let got=face(ch,depth+1,budget);if got!=0{return got;}}}}0
}
pub unsafe fn desktop_container(o:u32,depth:u32,budget:&mut u32)->u32{
    if depth>12||*budget==0||!visible(o){return 0;}*budget-=1;
    if markers(o,0,&mut 192)==1{return o;}
    if let Some((arr,n))=children(o){for i in 0..n{let ch=rd((arr+i*4) as *const u32);if safe_ptr(ch)&&rd((ch+4) as *const u32)==o{let found=desktop_container(ch,depth+1,budget);if found!=0{return found;}}}}0
}
unsafe extern "C" fn deleted(e:u32){
    if !safe_ptr(e)||fw_api::event_get_code(e)!=35{return;}
    let o=rd((e+4) as *const u32);for j in JOURNAL.iter_mut(){if j.obj==o{*j=EMPTY;}}
}
unsafe fn restore(index:usize){
    let j=JOURNAL[index];
    if safe_ptr(j.obj)&&fw_api::style_get(j.obj,0x28)==j.last{
        fw_api::prop(j.obj,0x28,j.source);fw_api::prop(j.obj,0x29,j.opa);
    }
    JOURNAL[index]=EMPTY;
}
unsafe fn style(o:u32,on:bool){
    let old=JOURNAL.iter().position(|j|j.obj==o);
    if !on{if let Some(i)=old{restore(i);}return;}
    let desc=DESC[CURRENT].as_ptr() as u32;
    if let Some(i)=old{
        if fw_api::style_get(o,0x28)!=JOURNAL[i].last{JOURNAL[i]=EMPTY;return;}
        if JOURNAL[i].last!=desc{fw_api::prop(o,0x28,desc);JOURNAL[i].last=desc;}
        return;
    }
    let Some(i)=JOURNAL.iter().position(|j|j.obj==0)else{return;};
    let source=fw_api::style_get(o,0x28);let opa=fw_api::style_get(o,0x29);
    let spec=rd((o+8) as *const u32);if !safe_ptr(spec){return;}
    let events=rd((spec+12) as *const u32);let count=rd((spec+26) as *const u8)&63;
    if count>0&&!safe_ptr(events){return;}
    let found=(0..count as u32).any(|i|rd((events+i*12) as *const u32)==deleted as *const () as u32);
    if !found&&(count>=63||fw_api::obj_add_event(o,deleted as *const () as u32,35,0)==0){return;}
    JOURNAL[i]=Journal{obj:o,source,opa,last:desc};
    fw_api::prop(o,0x28,desc);fw_api::prop(o,0x29,255);
}
unsafe fn apply(o:u32,depth:u32,budget:&mut u32){
    if depth>14||*budget==0||!visible(o){return;}*budget-=1;
    let w=rd((o+0x18) as *const i16) as i32-rd((o+0x14) as *const i16) as i32+1;
    let h=rd((o+0x1a) as *const i16) as i32-rd((o+0x16) as *const i16) as i32+1;
    if w>=300&&h>=360{
        let mask=markers(o,0,&mut 192);
        let eligible=mask>0&&mask<16&&mask.count_ones()==1;
        style(o,eligible&&HAVE&&CONFIG[4]!=0&&(CONFIG[5] as u32&mask)!=0);
    }
    if let Some((arr,n))=children(o){for i in 0..n{let ch=rd((arr+i*4) as *const u32);if safe_ptr(ch)&&rd((ch+4) as *const u32)==o{apply(ch,depth+1,budget);}}}
}
unsafe fn publish(){
    let header=5u32+(W as u32)*1024+(H as u32)*2097152;
    DESC[TARGET]=[header,BYTES as u32,OUTPUT[TARGET]];CURRENT=TARGET;HAVE=true;STAGE=0;
    CACHE_DIRTY=false;
    message("背景已生成\0".as_bytes());crate::notifications::request(MESSAGE);crate::log::line("背景生成完成");render_req(4);
}
unsafe fn message(text:&'static [u8]){MESSAGE=text;crate::notifications::request(text);}
pub unsafe fn tick(){
    // Keep large backdrop I/O and generation out of the injection window.
    if !ACTIVATED{if APP_FG==0{return;}ACTIVATED=true;}
    load();
    let a=ACTION.swap(0,Ordering::Relaxed);
    if a!=0{SCAN_ROOT=0;
        let before=CONFIG;
        match a{
            1=>{CONFIG[4]=(CONFIG[4]+1)%3;cancel();},
            2=>{cancel();CONFIG[7]=0;begin(1);if STAGE==1{message("请返回普通表盘并保持亮屏，等待背景生成\0".as_bytes());}},
            3=>{cancel();CONFIG[7]=0;begin(2);},
            5=>{cancel();CONFIG[7]=1;begin(2);},
            4=>CONFIG[6]^=1,
            10..=13=>CONFIG[5]^=1<<(a-10),
            _=>{},
        }
        if CONFIG!=before&&!save(){CONFIG=before;message("背景设置保存失败\0".as_bytes());}
        if CONFIG[4]==0{for i in 0..64{if JOURNAL[i].obj!=0{restore(i);}}}
        if a==1&&CONFIG[4]!=0{begin(if RAW_VALID{3}else if CONFIG[7]==0{1}else{2});}
        render_req(if a>=10{21}else{4});
    }
    if !fw_api::screen_is_on()||crate::ui_activity::scrolling(){return;}
    if CONFIG[4]==0&&STAGE==0{return;}
    let current=rd(WF_ENGINE_CUR as *const u32);let tag=face_tag();
    if CONFIG[6]!=0&&CONFIG[7]==0&&CONFIG[4]!=0&&(current!=LAST_FACE||tag!=LAST_FACE_TAG)&&STAGE==0{begin(1);}
    if STAGE==1{
        if let Some((key,root))=fw_api::top_page_root(){if key>>16==fw_api::HOME_APP_ID{
            let candidate=face(root,0,&mut 384);
            if candidate!=0{
                if fw_api::snapshot_needed(candidate,5)!=BYTES as u32{cancel();message("表盘快照尺寸不兼容\0".as_bytes());return;}
                let d=[5u32,BYTES as u32,RAW];
                if fw_api::snapshot_to_buf(candidate,5,d.as_ptr(),RAW,BYTES as u32)!=1{cancel();message("表盘快照失败\0".as_bytes());return;}
                RAW_VALID=true;CACHE_DIRTY=true;LAST_FACE=current;LAST_FACE_TAG=tag;STAGE=3;AT=0;
            }
        }}
    }else if STAGE==2{
        if FD<0{
            FD=fw_api::open(if CONFIG[7]==1{FILE.as_ptr()}else{CACHE.as_ptr()},1,0);if FD<0{
                cancel();CONFIG[7]=0;let _=save();begin(1);
                message("暂无已保存背景，请返回表盘生成\0".as_bytes());render_req(4);return;
            }
            let size=fw_api::lseek(FD,0,2);let mut header=[0u8;4];let mut n=0;
            if size!=BYTES as i64+4||fw_api::lseek(FD,0,0)<0{cancel();message("背景文件长度错误\0".as_bytes());return;}
            while n<4{let k=fw_api::read(FD,header.as_mut_ptr().add(n),(4-n) as u32);if k<=0||k as usize>4-n{cancel();return;}n+=k as usize;}
            if u32::from_le_bytes(header)!=5+(W as u32)*1024+(H as u32)*2097152{cancel();message("背景格式不是 N67 BGRA8888\0".as_bytes());return;}
        }
        let amount=(BYTES-AT).min(W*4*16);
        let n=fw_api::read(FD,(RAW as *mut u8).add(AT),amount as u32);
        if n<=0||n as usize>amount{cancel();message("背景文件读取失败\0".as_bytes());return;}AT+=n as usize;
        if AT==BYTES{fw_api::close(FD);FD=-1;RAW_VALID=true;STAGE=3;AT=0;}
    }else if STAGE==3{
        let input=core::slice::from_raw_parts(RAW as *const u8,BYTES);
        let output=core::slice::from_raw_parts_mut(OUTPUT[TARGET] as *mut u8,BYTES);
        if JOB.step(input,output,16).is_err(){cancel();message("背景像素尺寸错误\0".as_bytes());return;}
        if JOB.finished(){if CACHE_DIRTY{STAGE=6;AT=0;}else{publish();}}
    }else if STAGE==6{
        if FD<0{
            FD=fw_api::open(CACHE_TMP.as_ptr(),2|4,0o640);
            if FD<0{cancel();message("背景缓存无法写入\0".as_bytes());return;}
            let header=(5u32+(W as u32)*1024+(H as u32)*2097152).to_le_bytes();let mut n=0;
            while n<4{let k=fw_api::write(FD,header.as_ptr().add(n),(4-n) as u32);if k<=0||k as usize>4-n{cancel();return;}n+=k as usize;}
        }
        let amount=(BYTES-AT).min(W*4*16);
        let n=fw_api::write(FD,(RAW as *const u8).add(AT),amount as u32);
        if n<=0||n as usize>amount{cancel();message("背景缓存写入失败\0".as_bytes());return;}AT+=n as usize;
        if AT==BYTES{
            let rc=fw_api::close(FD);FD=-1;
            if rc<0||fw_api::rename(CACHE_TMP.as_ptr(),CACHE.as_ptr())!=0{cancel();message("背景缓存提交失败\0".as_bytes());}
            else{publish();}
        }
    }
    SCAN_TICKS=SCAN_TICKS.wrapping_add(1);
    if let Some((key,root))=fw_api::top_page_root(){if key>>16==fw_api::HOME_APP_ID{
        let desc=DESC[CURRENT].as_ptr() as u32;
        if HAVE&&(root!=SCAN_ROOT||desc!=SCAN_DESC||a!=0||SCAN_TICKS%20==0){
            SCAN_ROOT=root;SCAN_DESC=desc;apply(root,0,&mut 256);
        }
    }}
}
pub struct BackgroundPage{zones:bool}
impl Page for BackgroundPage{
    fn fill_title(&self,p:*mut u8){unsafe{put_str(p,if self.zones{"模糊区域\0".as_bytes()}else{"系统模糊\0".as_bytes()});}}
    fn render(&self,c:&PageCtx)->PageResult{unsafe{
        load();let mut anchor=c.title;let p=core::ptr::addr_of_mut!(TEXT) as *mut u8;
        if self.zones{
            for(i,name)in ["启动器","控制中心","小部件","通知中心"].iter().enumerate(){
                let mut w=crate::W::new(p,128);w.s(if CONFIG[5]&(1<<i)!=0{b"[x] "}else{b"[ ] "}).s(name.as_bytes());w.end();
                anchor=build_rows(c,anchor,&[(i,RowSpec::clickable(core::slice::from_raw_parts(p,w.len()+1)))])?;
            }
        }else{
            let mut w=crate::W::new(p,128);w.s("背景模式：".as_bytes()).s(match CONFIG[4]{0=>"关闭",1=>"通透背景",_=>"模糊背景"}.as_bytes());w.end();
            anchor=build_rows(c,anchor,&[(0,RowSpec::clickable(core::slice::from_raw_parts(p,w.len()+1)))])?;
            build_rows(c,anchor,&[
                (1,RowSpec::clickable("从表盘生成背景\0".as_bytes())),
                (2,RowSpec::clickable("使用已保存背景\0".as_bytes())),
                (3,RowSpec::clickable(if CONFIG[6]!=0{"自动跟随表盘：开\0".as_bytes()}else{"自动跟随表盘：关\0".as_bytes()})),
                (4,RowSpec::clickable("模糊区域\0".as_bytes())),
                (5,RowSpec::display("背景状态\0".as_bytes(),MESSAGE.as_ptr())),
                (6,RowSpec::clickable("导入 background.bin（可选）\0".as_bytes())),
                (7,RowSpec::display("使用步骤\0".as_bytes(),"1. 点「背景模式」，切换到「模糊背景」。\n\n2. 点「从表盘生成背景」。\n\n3. 返回普通表盘，保持亮屏，等待提示「背景已生成」。\n\n4. 打开应用列表或控制中心查看效果。\n\n在「模糊区域」选择要启用的页面。换表盘后可重新生成；已有背景可点「使用已保存背景」。\0".as_ptr())),
            ])?;
        }Ok(())
    }}
    fn on_click(&self,i:usize){unsafe{
        if self.zones{if i<4{ACTION.store(10+i as u32,Ordering::Relaxed);}}
        else if i==4{nav_goto(21,0);}else if i==6{ACTION.store(5,Ordering::Relaxed);}else if i<4{ACTION.store(i as u32+1,Ordering::Relaxed);}
    }}
}
pub static BACKGROUND_PAGE:BackgroundPage=BackgroundPage{zones:false};
pub static ZONES_PAGE:BackgroundPage=BackgroundPage{zones:true};
