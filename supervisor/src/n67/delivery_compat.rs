//! Restore missing data leaves for original N67 delivery faces. No script editing.
use crate::fw_api;
use core::{ptr::read_volatile as rd,sync::atomic::{AtomicBool,Ordering}};
static REQUEST:AtomicBool=AtomicBool::new(false);
const ROOT:&[u8]=b"/data/app/watchface/market/";
#[derive(Clone,Copy)]struct Leaf{offset:u32,size:u32,name:[u8;48]}
const EMPTY:Leaf=Leaf{offset:0,size:0,name:[0;48]};
static mut LEAVES:[Leaf;128]=[EMPTY;128];
static mut COUNT:usize=0;
static mut AT:usize=0;
static mut TABLE:u32=0;
static mut ITEMS:u32=0;
static mut INDEX:u32=0;
static mut SIZE:u32=0;
static mut FD:i32=-1;
static mut OUT:i32=-1;
static mut DIR:u32=0;
static mut STAGE:u8=0;
static mut VISITED:u32=0;
static mut TARGET:[u8;160]=[0;160];
static mut TEMP:[u8;180]=[0;180];
static mut DEST:[u8;180]=[0;180];
static mut COPIED:u32=0;
static mut ADDED:u32=0;
static mut FAILED:u32=0;
static mut OWN_TEMP:bool=false;
static mut KNOWN:bool=false;
fn len(s:&[u8])->usize{s.iter().position(|b|*b==0).unwrap_or(s.len())}
fn u32at(b:&[u8],n:usize)->u32{u32::from_le_bytes([b[n],b[n+1],b[n+2],b[n+3]])}
fn join(a:&[u8],b:&[u8])->Option<[u8;180]>{let mut p=[0;180];let n=len(a);if n+b.len()>=180{return None;}p[..n].copy_from_slice(&a[..n]);p[n..n+b.len()].copy_from_slice(b);Some(p)}
unsafe fn read_at(off:u32,b:&mut [u8])->bool{
 if off as u64+b.len() as u64>SIZE as u64||fw_api::lseek(FD,off as i64,0)!=off as i64{return false;}
 let mut n=0;while n<b.len(){let r=fw_api::read(FD,b[n..].as_mut_ptr(),(b.len()-n) as u32);if r<=0||r as usize>b.len()-n{return false;}n+=r as usize;}true
}
unsafe fn exists(p:&[u8])->bool{let f=fw_api::open(p.as_ptr(),1,0);if f<0{false}else{fw_api::close(f);true}}
unsafe fn close_pack(){if FD>=0{fw_api::close(FD);FD=-1;}if OUT>=0{fw_api::close(OUT);OUT=-1;}if OWN_TEMP{fw_api::fs_remove(TEMP.as_ptr());OWN_TEMP=false;}COUNT=0;AT=0;KNOWN=false;}
unsafe fn pack_error(){FAILED+=1;close_pack();STAGE=1;}
unsafe fn mkdir(p:&[u8])->bool{let f:unsafe extern "C" fn(*const u8,u32)->i32=core::mem::transmute(0x0c37e249usize);f(p.as_ptr(),0o755);let d=fw_api::opendir(p.as_ptr());if d==0{false}else{fw_api::closedir(d);true}}
#[export_name="chaos_delivery_request"] pub fn request(){REQUEST.store(true,Ordering::Relaxed);}
unsafe fn finish(){close_pack();if DIR!=0{fw_api::closedir(DIR);DIR=0;}STAGE=0;
 let mut text=[0u8;160];let mut w=crate::W::new(text.as_mut_ptr(),160);w.s("投递兼容：补回 ".as_bytes()).n(ADDED).s(" 个文件，异常 ".as_bytes()).n(FAILED).s(" 个包\n请返回原投递表盘重试\0".as_bytes());w.end();
 crate::notifications::request(&text[..len(&text)+1]);
}
unsafe fn manifest(b:&[u8])->Option<[u8;12]>{
 if !b.starts_with("-- Chaos N67素材导入器".as_bytes()){return None;}
 if !b.windows(12).any(|v|v==b"kind=\"icons\"")&&!b.windows(11).any(|v|v==b"kind=\"font\""){return None;}
 let p=b.windows(5).position(|v|v==b"pkg=\"")?+5;if p+13>b.len()||b[p+12]!=b'"'||!b[p..p+12].iter().all(u8::is_ascii_digit){return None;}
 let mut id=[0;12];id.copy_from_slice(&b[p..p+12]);Some(id)
}
#[export_name="chaos_delivery_tick"] pub unsafe fn tick(){
 if REQUEST.swap(false,Ordering::Relaxed){if STAGE!=0{crate::notifications::request("投递兼容处理中，请保持亮屏\0".as_bytes());return;}
  ADDED=0;FAILED=0;VISITED=0;DIR=fw_api::opendir(b"/data/app/watchface/market\0".as_ptr());if DIR==0{crate::notifications::request("无法读取已安装表盘\0".as_bytes());return;}STAGE=1;crate::notifications::request("开始检查投递包，请保持亮屏\0".as_bytes());}
 if STAGE==0||!fw_api::screen_is_on()||crate::ui_activity::scrolling(){return;}
 match STAGE{
 1=>{let e=fw_api::readdir(DIR);if e==0{finish();return;}VISITED+=1;if VISITED>160{FAILED+=1;finish();return;}
  if rd(e as *const u8)==10{return;}let mut id=[0u8;12];for i in 0..12{id[i]=rd((e+1+i as u32) as *const u8);}if rd((e+13) as *const u8)!=0||!id.iter().all(u8::is_ascii_digit){return;}
  let mut folder=[0;160];folder[..ROOT.len()].copy_from_slice(ROOT);folder[ROOT.len()..ROOT.len()+12].copy_from_slice(&id);folder[ROOT.len()+12]=b'/';
  let p=join(&folder,b"resource.bin").unwrap();FD=fw_api::open(p.as_ptr(),1,0);if FD<0{return;}let size=fw_api::lseek(FD,0,2);if size<328||size>64*1024*1024{close_pack();return;}SIZE=size as u32;
  let mut h=[0u8;328];if !read_at(0,&mut h)||u32at(&h,0)!=0x1234a55a{close_pack();return;}
  ITEMS=u32at(&h,0xd8);TABLE=u32at(&h,0xdc);if ITEMS==0||ITEMS>128||TABLE<328||TABLE as u64+ITEMS as u64*16>SIZE as u64{close_pack();return;}INDEX=0;COUNT=0;KNOWN=false;STAGE=2;
 },
 2=>{if INDEX>=ITEMS{if !KNOWN{close_pack();STAGE=1;return;}let n=len(&TARGET);let mut p=[0;180];p[..n].copy_from_slice(&TARGET[..n]);
   // Target is always market/<12 digits>/_lua/_Lua/; create only these directories.
   for end in [ROOT.len()+12,ROOT.len()+12+5,ROOT.len()+12+10]{let mut dir=[0;180];dir[..end].copy_from_slice(&p[..end]);if !mkdir(&dir){pack_error();return;}}
   AT=0;STAGE=3;return;}
  let mut ent=[0u8;16];if !read_at(TABLE+INDEX*16,&mut ent){pack_error();return;}if u32at(&ent,0)!=(0x05000000|INDEX)||u32at(&ent,4)!=0{pack_error();return;}INDEX+=1;
  let off=u32at(&ent,8);let length=u32at(&ent,12);if off<TABLE+ITEMS*16||length<21||off as u64+length as u64>SIZE as u64{pack_error();return;}
  let mut header=[0u8;20];if !read_at(off,&mut header){pack_error();return;}let size=u16::from_le_bytes([header[0],header[1]]) as u32;let n=header[3] as usize;
  if header[2]!=0||header[4..].iter().any(|b|*b!=0)||n==0||n>120||length!=20+n as u32+size{pack_error();return;}
  let mut name=[0;120];if !read_at(off+20,&mut name[..n]){pack_error();return;}let data=off+20+n as u32;
  if &name[..n]==b"_lua/_Lua/main.lua"{let mut main=[0;512];let k=512.min(size as usize);if !read_at(data,&mut main[..k]){pack_error();return;}if let Some(id)=manifest(&main[..k]){TARGET=[0;160];TARGET[..ROOT.len()].copy_from_slice(ROOT);TARGET[ROOT.len()..ROOT.len()+12].copy_from_slice(&id);let p=ROOT.len()+12;TARGET[p..p+11].copy_from_slice(b"/_lua/_Lua/");KNOWN=true;}return;}
  let prefix=b"_lua/_Lua/";if n<=prefix.len()||!name[..n].starts_with(prefix){return;}let stem=&name[prefix.len()..n];if !stem.ends_with(b".dat")||stem.len()>47||!stem[..stem.len()-4].iter().all(|b|b.is_ascii_lowercase()||b.is_ascii_digit()||*b==b'_'||*b==b'-'){return;}
  if size==0||COUNT>=128||LEAVES[..COUNT].iter().any(|v|&v.name[..len(&v.name)]==stem){pack_error();return;}let mut leaf=EMPTY;leaf.offset=data;leaf.size=size;leaf.name[..stem.len()].copy_from_slice(stem);LEAVES[COUNT]=leaf;COUNT+=1;
 },
 3=>{if AT>=COUNT{close_pack();STAGE=1;return;}let leaf=LEAVES[AT];DEST=join(&TARGET,&leaf.name[..len(&leaf.name)]).unwrap();if exists(&DEST){AT+=1;return;}
  TEMP=join(&DEST,b".chaos-pending").unwrap();OUT=fw_api::open(TEMP.as_ptr(),2|4|16,0o640);if OUT<0{pack_error();return;}OWN_TEMP=true;COPIED=0;STAGE=4;
 },
 4=>{let leaf=LEAVES[AT];let mut buf=[0u8;2048];let n=(leaf.size-COPIED).min(2048) as usize;if !read_at(leaf.offset+COPIED,&mut buf[..n]){pack_error();return;}let mut at=0;while at<n{let w=fw_api::write(OUT,buf[at..].as_ptr(),(n-at) as u32);if w<=0||w as usize>n-at{pack_error();return;}at+=w as usize;}COPIED+=n as u32;
  if COPIED==leaf.size{let r=fw_api::close(OUT);OUT=-1;if r<0||exists(&DEST)||fw_api::rename(TEMP.as_ptr(),DEST.as_ptr())!=0{pack_error();return;}OWN_TEMP=false;ADDED+=1;AT+=1;STAGE=3;}
 },_=>{}
 }
}

