//! N67 native Bluetooth manager + LVGL8 display setter. No P67 addresses.
use crate::*;
use crate::page::Page;
use core::{mem::transmute,ptr::{read_volatile as rd},sync::atomic::{AtomicU32,Ordering}};
const PID:usize=32;
static ACTION:AtomicU32=AtomicU32::new(0);
static mut NAME:[u8;64]=[0;64];
static mut WANTED:[u8;32]=[0;32];
static mut WAIT:u32=0;
extern "C" {fn chaos_n67_rotate_display(display:u32,rotation:u32);}
unsafe fn adapter()->u32{
 let api=rd(0x200bad94 as *const u32);let a=rd(0x200bad90 as *const u32);
 if !safe_ptr(a)||api&3!=0||!plausible_ptr(api+0x18){return 0;}
 if rd((api+0x14) as *const u32)!=0x0c3bd211||rd((api+0x18) as *const u32)!=0x0c3bd25d{return 0;}a
}
unsafe fn read_name()->bool{
 NAME.fill(0);let a=adapter();if a==0{return false;}
 let get:unsafe extern "C" fn(u32)->u32=transmute(0x0c3bd25dusize);let p=get(a);
 for i in 0..NAME.len(){if !plausible_ptr(p+i as u32){NAME.fill(0);return false;}
  let c=rd((p+i as u32) as *const u8);if c==0{return core::str::from_utf8(&NAME[..i]).is_ok();}NAME[i]=c;
 }NAME.fill(0);false
}
unsafe fn display()->u32{
 let d=rd(0x200b3750 as *const u32);if !safe_ptr(d){return 0;}let drv=rd(d as *const u32);
 if !safe_ptr(drv){return 0;}
 // Validate dimensions and root array before the native setter walks it.
 if rd(drv as *const u16)!=336||rd((drv+2) as *const u16)!=480{return 0;}
 let n=rd((d+0x24) as *const u32);let list=rd((d+0xc) as *const u32);
 if n>64||n!=0&&!safe_ptr(list){return 0;}
 for i in 0..n{if !safe_ptr(rd((list+4*i) as *const u32)){return 0;}}d
}
unsafe fn rotation()->u32{let d=display();if d==0{return u32::MAX;}let drv=rd(d as *const u32);((rd((drv+0x10) as *const u8)>>4)&3) as u32}
pub unsafe fn request_name(p:*const u8)->bool{
 if WAIT!=0{crate::notifications::request("蓝牙名称正在更新，请稍后\0".as_bytes());return false;}
 let mut b=[0u8;32];let mut n=0;while n<32{let c=*p.add(n);if c==0{break;}if !c.is_ascii_alphanumeric()&&c!=b' '&&c!=b'.'&&c!=b'-'&&c!=b'_' {return false;}b[n]=c;n+=1;}
 if n==0||n==32{return false;}WANTED=b;ACTION.store(4,Ordering::Relaxed);true
}
unsafe fn notice(s:&'static [u8]){crate::notifications::request(s);}
pub struct DevicePage;
impl Page for DevicePage{
 fn fill_title(&self,p:*mut u8){unsafe{put_str(p,"更多设置\0".as_bytes());}}
 fn render(&self,c:&PageCtx)->PageResult{unsafe{
  let ok=read_name();let rot=rotation();
  build_rows(c,c.title,&[
   (0,RowSpec::tap("蓝牙名称\0".as_bytes(),if ok{NAME.as_ptr()}else{"蓝牙服务未就绪\0".as_ptr()})),
   (1,RowSpec::clickable(if rot==2{"屏幕方向：180°（点按恢复）\0".as_bytes()}else{"屏幕方向：正常（点按翻转）\0".as_bytes()})),
   (2,RowSpec::clickable("投递包兼容修复\0".as_bytes())),
   (3,RowSpec::display("说明\0".as_bytes(),"蓝牙名称与关于页设备名称独立。翻转同时使用系统触控映射；重启后可能恢复默认。\0".as_ptr())),
  ])?;Ok(())
 }}
 fn on_click(&self,i:usize){if i<3{ACTION.store(i as u32+1,Ordering::Relaxed);}}
 fn needs_tick(&self)->bool{true}
 fn tick(&self){unsafe{
  if crate::ui_activity::scrolling(){return;}
  if WAIT!=0{WAIT-=1;if read_name()&&NAME[..32]==WANTED{WAIT=0;notice("蓝牙名称已更新\0".as_bytes());render_req(PID);}else if WAIT==0{notice("请求已发送，暂未确认名称更新，请刷新查看\0".as_bytes());}return;}
  match ACTION.swap(0,Ordering::Relaxed){
   1=>{if read_name(){crate::keyboard::open(NAME.as_ptr(),crate::keyboard::Completion::BluetoothName);}else{notice("蓝牙服务未就绪\0".as_bytes());}},
   2=>{let d=display();let old=rotation();if d==0||old!=0&&old!=2{notice("当前显示状态不支持翻转\0".as_bytes());return;}
    let target=if old==2{0}else{2};chaos_n67_rotate_display(d,target);
    if rotation()==target{notice("屏幕方向已切换\0".as_bytes());crate::log::kv("屏幕旋转",target*90);}else{notice("系统未接受翻转请求\0".as_bytes());}render_req(PID);
   },
   3=>{ // Name editing uses a separate action from delivery repair.
    crate::delivery_compat::request();
   },
   4=>{let a=adapter();if a==0{notice("蓝牙服务未就绪\0".as_bytes());return;}
    let n=WANTED.iter().position(|&c|c==0).unwrap_or(31)+1;
    let set:unsafe extern "C" fn(u32,*const u8,u32)->i32=transmute(0x0c3bd211usize);
    if set(a,WANTED.as_ptr(),n as u32)==0{WAIT=40;notice("蓝牙名称更新请求已发送\0".as_bytes());}
    else{notice("系统未接受蓝牙名称请求\0".as_bytes());}
   },_=>{}
  }
 }}
}
pub static PAGE:DevicePage=DevicePage;
