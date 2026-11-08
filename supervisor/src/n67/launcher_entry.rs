//! Optional Chaos launcher entry, using the existing order-preserving adapter.
use crate::*;
use core::sync::atomic::{AtomicBool,Ordering};
static REQUEST:AtomicBool=AtomicBool::new(false);
static mut LOADED:bool=false;
static mut ENABLED:bool=true;
static mut APPLY:bool=false;
static mut TICKS:u32=0;
static mut MAILBOX:u32=0;
const MAGIC:u32=0x31564943;
pub unsafe fn bind(base:u32){MAILBOX=base+0x300;enabled();publish();}
unsafe fn publish(){
 if safe_ptr(MAILBOX)&&safe_ptr(MAILBOX+4){
  core::ptr::write_volatile((MAILBOX+4) as *mut u32,ENABLED as u32);
  core::ptr::write_volatile(MAILBOX as *mut u32,MAGIC);
 }
}

pub unsafe fn enabled()->bool{
 if cfg!(feature="settings-egg"){return false;}
 if !LOADED{LOADED=true;let fd=fw_api::open(b"/data/chaos/launcher.cfg\0".as_ptr(),1,0);
  if fd>=0{let mut b=[0u8;2];let n=fw_api::read(fd,b.as_mut_ptr(),2);fw_api::close(fd);if n==1&&b[0]<=1{ENABLED=b[0]!=0;APPLY=!ENABLED;}}
 }ENABLED
}
pub fn request_toggle(){REQUEST.store(true,Ordering::Relaxed);}
pub unsafe fn tick(){
 if cfg!(feature="settings-egg"){return;}
 enabled();publish();TICKS=TICKS.saturating_add(1);
 // Installer settings may change this preference after injection. Poll one
 // byte at a bounded rate while awake, deferring I/O during active scrolling.
 if TICKS%20==0&&fw_api::screen_is_on()&&!crate::ui_activity::scrolling(){
  let fd=fw_api::open(b"/data/chaos/launcher.cfg\0".as_ptr(),1,0);
  if fd>=0{let mut b=[0u8;2];let n=fw_api::read(fd,b.as_mut_ptr(),2);fw_api::close(fd);
   if n==1&&b[0]<=1&&(b[0]!=0)!=ENABLED{ENABLED=b[0]!=0;publish();APPLY=true;render_req(crate::extra_pages::SETTINGS);}
  }
 }
 let requested=REQUEST.swap(false,Ordering::Relaxed);
 if requested{
  let next=(!ENABLED) as u8;
  let fd=fw_api::open(b"/data/chaos/launcher.tmp\0".as_ptr(),2|4|8,0o640);
  let ok=if fd<0{false}else{let n=fw_api::write(fd,&next,1);let close=fw_api::close(fd);n==1&&close==0&&fw_api::rename(b"/data/chaos/launcher.tmp\0".as_ptr(),b"/data/chaos/launcher.cfg\0".as_ptr())==0};
  if ok{ENABLED=!ENABLED;publish();APPLY=true;}else{crate::notifications::request("桌面入口设置保存失败\0".as_bytes());}
  render_req(crate::extra_pages::SETTINGS);
 }
 if APPLY&&(requested||TICKS%10==1)&&fw_api::screen_is_on(){if crate::app_manager::own_visibility(ENABLED){APPLY=false;}}
}
