//! N67 native language service, same setter used by stock language changes.
use crate::*;
use crate::page::Page;
use core::{mem::transmute,sync::atomic::{AtomicU32,Ordering}};
const PID:usize=31;
const CODES:[&[u8];3]=[b"zh_CN\0",b"zh_TW\0",b"en_US\0"];
static REQUEST:AtomicU32=AtomicU32::new(u32::MAX);
unsafe fn equal(p:u32,s:&[u8])->bool{for (i,&b) in s.iter().enumerate(){if !plausible_ptr(p+i as u32)||core::ptr::read_volatile((p+i as u32) as *const u8)!=b{return false;}}true}
unsafe fn current()->usize{let get:unsafe extern "C" fn(*const u8)->u32=transmute(0x0c0be245usize);let p=get(b"LANG\0".as_ptr());(0..3).find(|&i|equal(p,CODES[i])).unwrap_or(3)}
pub struct LanguagePage;
impl Page for LanguagePage{
 fn fill_title(&self,p:*mut u8){unsafe{put_str(p,"系统语言\0".as_bytes());}}
 fn render(&self,c:&PageCtx)->PageResult{unsafe{
  REQUEST.store(u32::MAX,Ordering::Relaxed); // Re-entering must not apply a stale click.
  build_rows(c,c.title,&[(0,RowSpec::check("简体中文\0".as_bytes(),fw_api::NONE_PTR)),(1,RowSpec::check("繁體中文\0".as_bytes(),fw_api::NONE_PTR)),(2,RowSpec::check(b"English\0",fw_api::NONE_PTR)),(3,RowSpec::display("修改手环系统语言\0".as_bytes(),"手机同步可能覆盖此选择\0".as_bytes().as_ptr()))])?;
  let active=current();for i in 0..3{let row=core::ptr::read_volatile(c.rows.add(i));fw_api::row_update(row,fw_api::NONE_PTR,fw_api::NONE_PTR,fw_api::NONE_PTR,0,(active==i) as u8);}
 }Ok(())}
 fn on_click(&self,i:usize){if i<3{REQUEST.store(i as u32,Ordering::Relaxed);}}
 fn needs_tick(&self)->bool{true}
 fn tick(&self){unsafe{let i=REQUEST.swap(u32::MAX,Ordering::Relaxed) as usize;if i>=3{return;}
  if current()==i{crate::notifications::request("已是当前系统语言\0".as_bytes());return;}
  let map:unsafe extern "C" fn(*const u8)->u32=transmute(0x0c36a1cdusize);
  if map(CODES[i].as_ptr())==0{crate::notifications::request("当前固件不支持此语言\0".as_bytes());return;}
  let set:unsafe extern "C" fn(*const u8)=transmute(0x0c4ab7f5usize);set(CODES[i].as_ptr());
  if current()==i{crate::notifications::request("系统语言已切换，重新进入系统页面查看\0".as_bytes());}
  else{crate::notifications::request("系统未接受语言切换，请重试\0".as_bytes());}
  render_req(PID);
 }}
}
pub static PAGE:LanguagePage=LanguagePage;

