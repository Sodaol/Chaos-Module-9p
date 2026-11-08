//! N67 equivalent of P67 1.0.8's four display customization pages.
//! Values change only the native About labels, never identity/RTC/version.ini.
use crate::*;
use crate::page::{Page,PageResult,PageCtx};
use core::ptr::read_volatile as rd;

const PATH:&[u8]=b"/data/chaos/n67-system-about.bin\0";
const TEMP:&[u8]=b"/data/chaos/n67-system-about.tmp\0";
const SIZE:usize=144;
#[derive(Clone,Copy)]
struct Choice{enabled:bool,index:u8,custom:[u8;32]}
const EMPTY:Choice=Choice{enabled:false,index:0,custom:[0;32]};
static mut CONFIG:[Choice;4]=[EMPTY;4];
static mut LOADED:bool=false;
static mut MESSAGE:&'static [u8]=b"\0";
static mut ROOT:u32=0;
static mut ORIGINAL:[[u8;512];5]=[[0;512];5];
static mut HEIGHT:[i32;5]=[36;5];
static mut KEY:u32=0;
static mut GENERATION:u32=1;
static mut APPLIED:u32=0;
// Display-only line breaks; the persisted values and keyboard input stay intact.
static mut DISPLAY:[[u8;1024];5]=[[0;1024];5];
static mut CHECKS:u32=0;


static VER:&[&[u8]]=&[b"3.1.190\0",b"4.103.022\0",b"91.78.13\0"];
static SYS:&[&[u8]]=&[b"Xiaomi HyperOS\0",b"HarmonyOS\0"];
static MODEL_VALUES:&[&[u8]]=&[b"M2551B1\0",b"M2553B1\0",b"M9178B13\0"];
static NAME_VALUES:&[&[u8]]=&[
    "小米手环9 Pro\0".as_bytes(),"小米手环10 Pro\0".as_bytes(),
    "小米手环10 Pro 陶瓷版\0".as_bytes(),"小米手环11 Pro\0".as_bytes(),
    "小米手环11 Pro 陶瓷版\0".as_bytes(),"三星note7\0".as_bytes(),
];
fn presets(k:usize)->&'static [&'static [u8]]{match k{0=>VER,1=>SYS,2=>NAME_VALUES,_=>MODEL_VALUES}}
fn title(k:usize)->&'static [u8]{match k{0=>"系统版本显示\0",1=>"手环系统文本\0",2=>"设备名称\0",_=>"手环型号\0"}.as_bytes()}
fn valid(k:usize,c:u8)->bool{c.is_ascii_alphanumeric()||c==b'.'||k!=0&&c==b' '}
fn sum(b:&[u8])->u32{b.iter().fold(0x811c9dc5,|h,&v|(h^v as u32).wrapping_mul(16777619))}
unsafe fn load(){
    if LOADED{return;}LOADED=true;
    let fd=fw_api::open(PATH.as_ptr(),1,0);if fd<0{return;}
    let mut b=[0u8;SIZE];let mut n=0;
    while n<SIZE{let got=fw_api::read(fd,b.as_mut_ptr().add(n),(SIZE-n) as u32);if got<=0||got as usize>SIZE-n{break;}n+=got as usize;}
    let mut extra=0;let tail=fw_api::read(fd,&mut extra,1);fw_api::close(fd);
    if n!=SIZE||tail!=0||&b[..4]!=b"NSC1"||sum(&b[..SIZE-4])!=u32::from_le_bytes(b[SIZE-4..].try_into().unwrap()){MESSAGE="设置文件损坏，保留系统显示\0".as_bytes();return;}
    let mut cfg=[EMPTY;4];
    for k in 0..4{let at=4+k*34;
        if b[at]>1||b[at+1] as usize>presets(k).len(){return;}
        let text=&b[at+2..at+34];let Some(len)=text.iter().position(|&c|c==0)else{return;};
        if !text[..len].iter().all(|&c|valid(k,c)){return;}
        if b[at]!=0&&b[at+1] as usize==presets(k).len()&&len==0{return;}
        cfg[k].enabled=b[at]!=0;cfg[k].index=b[at+1];cfg[k].custom.copy_from_slice(text);
    }CONFIG=cfg;
}
unsafe fn commit(cfg:[Choice;4])->bool{
    let mut b=[0u8;SIZE];b[..4].copy_from_slice(b"NSC1");
    for k in 0..4{let at=4+k*34;b[at]=cfg[k].enabled as u8;b[at+1]=cfg[k].index;b[at+2..at+34].copy_from_slice(&cfg[k].custom);}
    let hash=sum(&b[..SIZE-4]);b[SIZE-4..].copy_from_slice(&hash.to_le_bytes());
    let fd=fw_api::open(TEMP.as_ptr(),2|4|8,0o640);if fd<0{return false;}
    let mut n=0;while n<SIZE{let got=fw_api::write(fd,b.as_ptr().add(n),(SIZE-n) as u32);if got<=0||got as usize>SIZE-n{fw_api::close(fd);return false;}n+=got as usize;}
    if fw_api::close(fd)<0||fw_api::rename(TEMP.as_ptr(),PATH.as_ptr())!=0{return false;}
    CONFIG=cfg;GENERATION=GENERATION.wrapping_add(1);MESSAGE="已保存，重新进入系统关于页生效\0".as_bytes();crate::notifications::request(MESSAGE);true
}
pub unsafe fn save_custom(k:usize,text:*const u8)->bool{
    load();if text.is_null(){return false;}let mut custom=[0u8;32];let mut n=0;
    while n<32{let c=rd(text.add(n));if c==0{break;}if n==31||!valid(k,c){crate::notifications::request("格式无效，请使用英文、数字或小数点\0".as_bytes());return false;}custom[n]=c;n+=1;}
    if n==0{return false;}let mut next=CONFIG;next[k]=Choice{enabled:true,index:presets(k).len() as u8,custom};
    if commit(next){true}else{MESSAGE="保存失败，原设置未改变\0".as_bytes();crate::notifications::request(MESSAGE);false}
}
pub(crate) mod system_version{pub unsafe fn save_custom(p:*const u8)->bool{super::save_custom(0,p)}}
pub(crate) mod system_text{pub unsafe fn save_custom(p:*const u8)->bool{super::save_custom(1,p)}}
pub(crate) mod device_name{pub unsafe fn save_custom(p:*const u8)->bool{super::save_custom(2,p)}}
pub(crate) mod device_model{pub unsafe fn save_custom(p:*const u8)->bool{super::save_custom(3,p)}}

pub struct Menu;
impl Page for Menu{
 fn fill_title(&self,p:*mut u8){unsafe{put_str(p,"系统关于页面修改\0".as_bytes());}}
 fn render(&self,c:&PageCtx)->PageResult{unsafe{let mut prev=c.title;for k in 0..4{prev=build_rows(c,prev,&[(k,RowSpec::clickable(title(k)))])?;}Ok(())}}
 fn on_click(&self,i:usize){if i<4{unsafe{nav_goto(23+i as u32,0);}}}
}
pub static MENU:Menu=Menu;
pub struct FieldPage{kind:usize}
impl Page for FieldPage{
 fn fill_title(&self,p:*mut u8){unsafe{put_str(p,title(self.kind));}}
 fn render(&self,c:&PageCtx)->PageResult{unsafe{
    load();let k=self.kind;let list=presets(k);let choice=CONFIG[k];
    let mut prev=build_rows(c,c.title,&[(0,RowSpec::check("系统默认\0".as_bytes(),fw_api::NONE_PTR))])?;
    fw_api::row_update(rd(c.rows),fw_api::NONE_PTR,fw_api::NONE_PTR,fw_api::NONE_PTR,0,(!choice.enabled) as u8);
    for i in 0..list.len(){prev=build_rows(c,prev,&[(i+1,RowSpec::check(list[i],fw_api::NONE_PTR))])?;
        fw_api::row_update(rd(c.rows.add(i+1)),fw_api::NONE_PTR,fw_api::NONE_PTR,fw_api::NONE_PTR,0,(choice.enabled&&choice.index as usize==i) as u8);}
    build_rows(c,prev,&[(list.len()+1,RowSpec::clickable("自定义…\0".as_bytes()))])?;

    Ok(())
 }}
 fn on_click(&self,i:usize){unsafe{
    load();let k=self.kind;let count=presets(k).len();
    if i==count+1{let completion=match k{0=>crate::keyboard::Completion::SystemVersion,1=>crate::keyboard::Completion::SystemText,2=>crate::keyboard::Completion::DeviceName,_=>crate::keyboard::Completion::DeviceModel};crate::keyboard::open(CONFIG[k].custom.as_ptr(),completion);return;}
    if i>count{return;}let mut next=CONFIG;next[k].enabled=i!=0;if i>0{next[k].index=(i-1) as u8;}
    if !commit(next){MESSAGE="保存失败，原设置未改变\0".as_bytes();crate::notifications::request(MESSAGE);}render_req(23+k);
 }}
}
pub static VERSION:FieldPage=FieldPage{kind:0};
pub static SYSTEM:FieldPage=FieldPage{kind:1};
pub static NAME:FieldPage=FieldPage{kind:2};
pub static MODEL:FieldPage=FieldPage{kind:3};
pub struct KeyboardPage;
impl Page for KeyboardPage{
 fn fill_title(&self,p:*mut u8){unsafe{put_str(p,crate::keyboard::title());}}
 fn render(&self,c:&PageCtx)->PageResult{unsafe{if crate::keyboard::render(c.content){Ok(())}else{Err(PageError::RowFailed(0))}}}
 fn on_click(&self,_:usize){}
}
pub static KEYBOARD:KeyboardPage=KeyboardPage;

// Exact slots from native about on_create 0xc2d6514 and text layout 0xc2cfd60.
const VALUES:[u32;5]=[0x200cd0bc,0x200cd0b0,0x200cd098,0x200cd0a0,0x200cd0cc];
unsafe fn inside(mut o:u32,root:u32)->bool{for _ in 0..32{if !safe_ptr(o){return false;}if o==root{return true;}o=rd((o+4) as *const u32);}false}
unsafe fn text_copy(label:u32,out:&mut [u8;512])->bool{
    if rd(label as *const u32)!=0x2c6834b0{return false;}
    let p=rd((label+0x24) as *const u32);
    for i in 0..512{if !plausible_ptr(p+i as u32){return false;}let c=rd((p+i as u32) as *const u8);out[i]=c;if c==0{return core::str::from_utf8(&out[..i]).is_ok();}}false
}
unsafe fn wanted(k:usize)->*const u8{
    if k==4{return ORIGINAL[k].as_ptr();}
    let choice=CONFIG[k];if !choice.enabled{return ORIGINAL[k].as_ptr();}
    if choice.index as usize==presets(k).len(){CONFIG[k].custom.as_ptr()}else{presets(k)[choice.index as usize].as_ptr()}
}
unsafe fn display_text(k:usize,p:*const u8)->*const u8{
 let out=core::ptr::addr_of_mut!(DISPLAY[k]) as *mut u8;
 let mut n=0usize;let mut used=0usize;let mut width=0i32;
 while n<511&&used<1018{
  let c=rd(p.add(n));if c==0{break;}
  let bytes=if c<128{1}else if c<0xe0{2}else if c<0xf0{3}else{4};
  let advance=if c>=128{32}else if c==b' '||b"ilI.,:!".contains(&c){11}else if c==b'W'||c==b'M'||c==b'w'||c==b'm'{32}else{22};
  if c==b'\n'{width=0;}else{
   if (k==4||CONFIG[k].enabled)&&width>0&&width+advance>280{*out.add(used)=b'\n';used+=1;width=0;}
   width+=advance;
  }
  if n+bytes>511{break;}
  for j in 0..bytes{let b=rd(p.add(n+j));if b==0{*out.add(used)=0;return out;}*out.add(used)=b;used+=1;}
  n+=bytes;
 }
 *out.add(used)=0;out
}
unsafe fn same_text(o:u32,wanted:*const u8)->bool{
 let p=rd((o+0x24) as *const u32);
 for i in 0..1024{if !plausible_ptr(p+i){return false;}let a=rd((p+i) as *const u8);if a!=rd(wanted.add(i as usize)){return false;}if a==0{return true;}}false
}
unsafe fn footer_ok(root:u32)->bool{
 let tail=rd(0x200cd0cc as *const u32);let button=rd(0x200cd0d0 as *const u32);
 if !inside(tail,root)||!inside(button,root){return true;}
 rd((button+0x16) as *const i16) as i32>=rd((tail+0x1a) as *const i16) as i32+16
}
unsafe extern "C" fn root_event(e:u32){
    if e!=0&&fw_api::event_get_code(e)==35&&rd((e+4) as *const u32)==ROOT{ROOT=0;APPLIED=0;}
}
pub unsafe fn tick(){
    load();
    if !fw_api::screen_is_on(){return;}
    let Some((key,root))=fw_api::top_page_root()else{return;};
    if key!=0x0016001b{return;}
    let mut labels=[0u32;5];for k in 0..5{labels[k]=rd(VALUES[k] as *const u32);if !inside(labels[k],root){return;}}
    if ROOT!=root||KEY!=key{
        let mut originals=[[0u8;512];5];
        for k in 0..5{if !text_copy(labels[k],&mut originals[k]){return;}
            let y1=rd((labels[k]+0x16) as *const i16) as i32;let y2=rd((labels[k]+0x1a) as *const i16) as i32;HEIGHT[k]=(y2-y1+1).clamp(24,640);}
        ORIGINAL=originals;ROOT=root;KEY=key;APPLIED=0;
        fw_api::obj_add_event(root,root_event as *const () as u32,35,0);
    }
    CHECKS=CHECKS.wrapping_add(1);
    if APPLIED==GENERATION{
        if CHECKS%10!=0{return;}
        if (0..5).all(|k|(k<4&&!CONFIG[k].enabled)||(same_text(labels[k],DISPLAY[k].as_ptr())&&rd((labels[k]+0x50) as *const u8)&7==0))&&footer_ok(root){return;}
    }
    let repair=APPLIED==GENERATION;
    if !same_text(labels[4],DISPLAY[4].as_ptr()){
        let mut serial=[0u8;512];
        if text_copy(labels[4],&mut serial){ORIGINAL[4]=serial;}
    }
    for k in 0..5{
        if k<4&&repair&&!CONFIG[k].enabled{continue;}
        let p=display_text(k,wanted(k));
        // Establish a fixed width and WRAP before changing text; hard breaks
        // also handle the native label's no-break treatment of a long token.
        fw_api::obj_set_size(labels[k],304,HEIGHT[k]);
        fw_api::label_wrap(labels[k]);
        fw_api::label_set_text(labels[k],p);
        let height=if k==4||CONFIG[k].enabled{fw_api::wrapped_height(labels[k],32,280).max(HEIGHT[k])}else{HEIGHT[k]};
        fw_api::obj_set_size(labels[k],304,height);

    }
    let update:unsafe extern "C" fn(u32)=core::mem::transmute(0x0c23c881usize);
    update(root);
    // Keep MAC, serial number and subsequent fields in the original chain.
    let pairs=[(0x10,0x0c,5),(0x14,0x10,15),(0x18,0x14,5),(0x1c,0x18,15),(0x20,0x1c,5),(0x24,0x20,15),(0x28,0x24,5),(0x30,0x28,15),(0x34,0x30,5),(0x40,0x34,15),(0x44,0x40,5)];
    for(a,b,gap)in pairs{let o=rd((0x200cd088+a) as *const u32);let base=rd((0x200cd088+b) as *const u32);if inside(o,root)&&inside(base,root){fw_api::native_align_to(o,base,13,0,gap);}}
    let serial=rd(0x200cd0cc as *const u32);let button=rd(0x200cd0d0 as *const u32);
    if inside(serial,root)&&inside(button,root){fw_api::native_align_to(button,serial,14,0,15);}
    update(root);
    APPLIED=GENERATION;
}
