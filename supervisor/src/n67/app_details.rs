//! v1.1.0 app details and selection. All mutations use the live package identity.
//! Uninstallation delegates to N67's own quickapp service; JSON is read-only.
use super::*;
use crate::app_metadata::{self,Metadata};
const DETAIL:usize=29;
const SELECT:usize=30;
static REQUEST:AtomicU32=AtomicU32::new(0);
static mut TARGET:[u8;PKG]=[0;PKG];
static mut META:Metadata=Metadata::EMPTY;
static mut EXCL_CONTEXT:bool=false;
static mut CONFIRM:bool=false;
static mut SELECTED:[[u8;PKG];MAX]=[[0;PKG];MAX];
static mut SELECT_N:usize=0;
static mut WINDOW:usize=0;
static mut VIEW:[[u8;PKG];5]=[[0;PKG];5];
static mut VIEW_CHECK:[bool;5]=[false;5];
static mut VIEW_N:usize=0;
static mut VIEW_SELECTED:usize=0;
static mut VIEW_DONE:usize=0;
static mut VIEW_CONFIRM:bool=false;
static mut QUEUE:[[u8;PKG];MAX]=[[0;PKG];MAX];
static mut QN:usize=0;
static mut QI:usize=0;
static mut QOP:u8=0;
static mut DONE:usize=0;
static mut FAILED:usize=0;
static mut WAIT:u32=0;
static mut SIZE:u64=0;
static mut SCAN:bool=false;
static mut PARTIAL:bool=false;
static mut ROOT:usize=0;
static mut DEPTH:usize=0;
static mut VISITED:usize=0;
static mut DIRS:[u32;8]=[0;8];
static mut PATHS:[[u8;300];8]=[[0;300];8];
static mut CAPTION:[u8;192]=[0;192];
const ROOTS:[&[u8];12]=[b"/data/app/",b"/data/quickapp/app/",b"/data/app/quickapp/",b"/data/quickapp/",b"/data/quickapp/system/",b"/data/quickapp/cache/",b"/data/quickapp/files/",b"/data/quickapp/mass/",b"/data/app/system/",b"/data/cache/",b"/data/files/",b"/data/mass/"];
fn bytes(s:&[u8])->&[u8]{&s[..s.iter().position(|&c|c==0).unwrap_or(s.len())]}
fn valid_package(p:&[u8;PKG])->bool {let p=bytes(p);!p.is_empty()&&p!=b"."&&p!=b".."&&p.iter().all(|c|c.is_ascii_alphanumeric()||matches!(c,b'.'|b'_'|b'-'))}
unsafe fn notice(s:&'static [u8]){crate::notifications::request(s);}
unsafe fn index(pkg:&[u8;PKG])->Option<usize>{(0..N).find(|&i|ENTRIES[i].pkg==*pkg)}
unsafe fn selected(pkg:&[u8;PKG])->bool{(0..SELECT_N).any(|i|SELECTED[i]==*pkg)}
unsafe fn toggle(pkg:[u8;PKG]){if let Some(i)=(0..SELECT_N).find(|&i|SELECTED[i]==pkg){SELECT_N-=1;SELECTED[i]=SELECTED[SELECT_N];}else if SELECT_N<MAX{SELECTED[SELECT_N]=pkg;SELECT_N+=1;}CONFIRM=false;}
unsafe fn read_meta(path:&[u8],pkg:&[u8;PKG],manifest:bool)->Option<Metadata>{
 let fd=fw_api::open(path.as_ptr(),1,0);if fd<0{return None;}let ptr=fw_api::heap_malloc(65537);if ptr==0{fw_api::close(fd);return None;}
 let mut n=0;let mut ok=true;while n<65537{let k=fw_api::read(fd,(ptr as *mut u8).add(n),(65537-n) as u32);if k==0{break;}if k<0||k as usize>65537-n{ok=false;break;}n+=k as usize;}fw_api::close(fd);
 let r=if ok&&n<=65536 {let b=core::slice::from_raw_parts(ptr as *const u8,n);if manifest{app_metadata::manifest(b).ok()}else{app_metadata::registry(b,bytes(pkg)).ok().flatten()}}else{None};fw_api::fw_free(ptr);r
}
fn join(root:&[u8],pkg:&[u8;PKG],suffix:&[u8])->Option<[u8;300]>{let p=bytes(pkg);if !valid_package(pkg)||root.len()+p.len()+suffix.len()>=300{return None;}let mut b=[0;300];let mut at=0;for s in [root,p,suffix]{b[at..at+s.len()].copy_from_slice(s);at+=s.len();}Some(b)}
unsafe fn metadata(pkg:&[u8;PKG])->Metadata{
 let mut m=Metadata::EMPTY;
 for p in [b"/data/quickapp/apps.json\0".as_slice(),b"/data/app/quickapp/rpk_info.json\0",b"/quickapp/rpk_info.json\0"]{if let Some(x)=read_meta(p,pkg,false){if m.name[0]==0{m.name=x.name;}if m.version[0]==0{m.version=x.version;}}}
 if m.name[0]==0||m.version[0]==0{for root in ROOTS {if let Some(p)=join(root,pkg,b"/manifest.json"){if let Some(x)=read_meta(&p,pkg,true){if m.name[0]==0{m.name=x.name;}if m.version[0]==0{m.version=x.version;}}}}}m
}
unsafe fn scan_close(){for d in &mut DIRS{if *d!=0{fw_api::closedir(*d);*d=0;}}SCAN=false;}
pub(super) unsafe fn leave(pid:usize){if pid!=DETAIL{scan_close();}REQUEST.store(0,Ordering::Relaxed);CONFIRM=false;}
pub(super) unsafe fn open(i:usize,excl:bool){if !VALID||i>=N{return;}scan_close();TARGET=ENTRIES[i].pkg;META=metadata(&TARGET);EXCL_CONTEXT=excl;CONFIRM=false;SIZE=0;PARTIAL=false;ROOT=0;DEPTH=0;VISITED=0;SCAN=valid_package(&TARGET);nav_goto(DETAIL as u32,0);}
pub(super) unsafe fn open_selection(){SELECT_N=0;WINDOW=0;CONFIRM=false;nav_goto(SELECT as u32,0);}
unsafe fn stat(p:*const u8)->Option<(u32,u64)>{let mut b=[0u32;24];let f:unsafe extern "C" fn(*const u8,*mut u32)->i32=core::mem::transmute(0x0c37fc39usize);if f(p,b.as_mut_ptr())<0{None}else{Some((b[2],b[6] as u64|((b[7] as u64)<<32)))}}
unsafe fn scan_tick()->bool {
 if !SCAN{return false;}
 // At most eight filesystem entries per GUI tick; never follow symbolic links.
 for _ in 0..8{
  if DIRS[DEPTH]==0{
   if ROOT>=ROOTS.len(){SCAN=false;return true;}
   let path=match join(ROOTS[ROOT],&TARGET,b""){Some(p)=>p,None=>{SCAN=false;PARTIAL=true;return true;}};ROOT+=1;
   PATHS[0]=path;DEPTH=0;
   if let Some((m,n))=stat(path.as_ptr()){if m&0xf000==0x8000{SIZE=SIZE.saturating_add(n);continue;}if m&0xf000!=0x4000{continue;}}
   let d=fw_api::opendir(path.as_ptr());if d==0{continue;}DIRS[0]=d;
  }
  let e=fw_api::readdir(DIRS[DEPTH]);if e==0{fw_api::closedir(DIRS[DEPTH]);DIRS[DEPTH]=0;if DEPTH>0{DEPTH-=1;}continue;}
  if rd(e as *const u8)==10{continue;}
  VISITED+=1;if VISITED>8192{PARTIAL=true;scan_close();return true;}
  let mut name=[0u8;256];let mut n=0;while n<255{let c=rd((e+1+n as u32) as *const u8);if c==0{break;}name[n]=c;n+=1;}
  if n==0||n==255||&name[..n]==b"."||&name[..n]==b".."||name[..n].contains(&b'/'){continue;}
  let parent=bytes(&PATHS[DEPTH]);if parent.len()+1+n>=300{PARTIAL=true;continue;}let mut path=[0;300];path[..parent.len()].copy_from_slice(parent);path[parent.len()]=b'/';path[parent.len()+1..parent.len()+1+n].copy_from_slice(&name[..n]);
  if let Some((m,n))=stat(path.as_ptr()){if m&0xf000==0x8000{SIZE=SIZE.saturating_add(n);}else if m&0xf000==0x4000{if DEPTH+1==DIRS.len(){PARTIAL=true;}else{let d=fw_api::opendir(path.as_ptr());if d!=0{DEPTH+=1;DIRS[DEPTH]=d;PATHS[DEPTH]=path;}}}}
 }false
}
unsafe fn exclude_toggle(i:usize)->bool{
 let e=ENTRIES[i];if protected(&e){notice("系统应用不可取消保护\0".as_bytes());return false;}
 let oldn=PN;let p=match policy_for(&e.pkg){Some(p)=>p,None if PN<MAX=>{let p=PN;PN+=1;POLICIES[p]=Policy{pkg:e.pkg,flags:e.flags&1};p},_=>return false};let old=POLICIES[p];POLICIES[p].flags^=2;
 if !save_policy(){POLICIES[p]=old;PN=oldn;notice(LAST_ERROR);false}else{true}
}
unsafe fn quick_info(pkg:&[u8;PKG])->u32{let f:unsafe extern "C" fn(*const u8)->u32=core::mem::transmute(0x0c2c0141usize);f(pkg.as_ptr())}
unsafe fn uninstall(pkg:&[u8;PKG])->bool{
 if !snapshot(){notice("注册表改变，未卸载\0".as_bytes());return false;}let i=match index(pkg){Some(i)=>i,None=>return false};
 if protected(&ENTRIES[i])||excluded(&ENTRIES[i])||!valid_package(pkg)||quick_info(pkg)==0{notice("系统应用或排除项不能卸载\0".as_bytes());return false;}
 // Native phone uninstall dispatch 0xc2c4466 calls this same package-only API.
 // The firmware owns registry removal, pending app shutdown, and file cleanup.
 let f:unsafe extern "C" fn(*const u8)=core::mem::transmute(0x0c4b5191usize);f(pkg.as_ptr());crate::log::pkg("请求卸载 ",pkg.as_ptr());true
}
unsafe fn queue(op:u8){if QN!=0{notice("批量操作正在进行\0".as_bytes());return;}if !snapshot(){return;}QI=0;DONE=0;FAILED=0;WAIT=0;QOP=op;
 for j in 0..SELECT_N{if let Some(i)=index(&SELECTED[j]){if !excluded(&ENTRIES[i])&&!protected(&ENTRIES[i]){QUEUE[QN]=SELECTED[j];QN+=1;}}}
 if QN==0{notice("没有可操作的应用\0".as_bytes());}else{notice("批量处理中\0".as_bytes());}CONFIRM=false;
}
// Update existing native labels; preserve the content object and its scroll position.
unsafe fn update_row(pid:usize,slot:usize,text:*const u8){
 if PAGES[pid].built==0||!page_is_live(pid){return;}
 let row=rd(page_rows_ptr(pid).add(slot));if row==0{return;}
 let label=rd((row+0x50) as *const u32);if label!=0{fw_api::label_set_text(label,text);}
}
unsafe fn refresh_selection(){
 if PAGES[SELECT].built==0||!page_is_live(SELECT){return;}
 if !snapshot(){render_req(SELECT);return;}
 let mut current=[[0u8;PKG];5];let mut n=0;let mut j=0;
 for i in 0..N{let e=ENTRIES[i];if protected(&e)||excluded(&e){continue;}
  if j>=WINDOW*5&&j<WINDOW*5+5{current[n]=e.pkg;n+=1;}j+=1;
 }
 if n!=VIEW_N||current!=VIEW{render_req(SELECT);return;}
 if (VIEW_SELECTED==0)!=(SELECT_N==0){update_row(SELECT,0,if SELECT_N>0{"取消全选\0".as_ptr()}else{"全选（跳过排除项）\0".as_ptr()});}
 if VIEW_SELECTED!=SELECT_N||VIEW_DONE!=DONE{
  let p=core::ptr::addr_of_mut!(CAPTION) as *mut u8;let mut w=W::new(p,192);w.s("已选 ".as_bytes()).n(SELECT_N as u32).s(" / 已完成 ".as_bytes()).n(DONE as u32);w.end();update_row(SELECT,1,p);
 }
 if VIEW_CONFIRM!=CONFIRM{update_row(SELECT,4,if CONFIRM{"确认卸载选中？\0".as_ptr()}else{"卸载选中\0".as_ptr()});}
 for slot in 0..n{let check=selected(&current[slot]);if VIEW_CHECK[slot]!=check{
  let mut text=[0u8;PKG+8];let mut w=W::new(text.as_mut_ptr(),text.len());w.s(if check{b"[x] "}else{b"[ ] "}).s(bytes(&current[slot]));w.end();update_row(SELECT,7+slot,text.as_ptr());VIEW_CHECK[slot]=check;
 }}VIEW_SELECTED=SELECT_N;VIEW_DONE=DONE;VIEW_CONFIRM=CONFIRM;
}

unsafe fn launch(pkg:&[u8;PKG])->bool{
 if !valid_package(pkg){return false;}
 let lookup:unsafe extern "C" fn(*const u8,*const u8)->u32=core::mem::transmute(0x0c2c1269usize);
 if !safe_ptr(lookup(pkg.as_ptr(),core::ptr::null())){notice("应用服务未就绪或应用未安装\0".as_bytes());return false;}
 // Stock quickapp_launch_app: pkg in r0, optional URI in r1. Never pass app id.
 let run:unsafe extern "C" fn(*const u8,*const u8)=core::mem::transmute(0x0c4fb559usize);
 run(pkg.as_ptr(),core::ptr::null());crate::log::pkg("请求打开 ",pkg.as_ptr());true
}
unsafe fn queue_tick(){if QN==0{return;}if QI>=QN{QN=0;if QOP==2{SELECT_N=0;}notice(if FAILED==0{"批量操作完成\0".as_bytes()}else{"部分应用操作失败\0".as_bytes()});refresh_selection();return;}
 let pkg=QUEUE[QI];if QOP==2&&WAIT!=0{if quick_info(&pkg)==0{DONE+=1;QI+=1;WAIT=0;refresh_selection();}else{WAIT+=1;if WAIT>=100{FAILED+=1;QI+=1;WAIT=0;}}return;}
 if QOP==2{if uninstall(&pkg){WAIT=1;}else{FAILED+=1;QI+=1;}}else{
  if snapshot(){if let Some(i)=index(&pkg){if !excluded(&ENTRIES[i])&&change(i,QOP==0){DONE+=1;}else{FAILED+=1;}}else{FAILED+=1;}}else{FAILED+=1;}QI+=1;
 }refresh_selection();
}
pub(super) unsafe fn maintain(){queue_tick();}
pub struct DetailPage;
impl Page for DetailPage{
 fn fill_title(&self,p:*mut u8){unsafe{put_str(p,"应用详情\0".as_bytes());}}
 fn render(&self,c:&PageCtx)->PageResult{unsafe{
  let valid=snapshot();let i=if valid{index(&TARGET)}else{None};let name=if META.name[0]!=0{META.name.as_ptr()}else{TARGET.as_ptr()};
  let mut anchor=build_rows(c,c.title,&[(0,RowSpec::display("应用名称\0".as_bytes(),name)),(1,RowSpec::display("包名\0".as_bytes(),TARGET.as_ptr())),(2,RowSpec::display("版本\0".as_bytes(),if META.version[0]==0{"未知\0".as_ptr()}else{META.version.as_ptr()}))])?;
  let p=core::ptr::addr_of_mut!(CAPTION) as *mut u8;let mut w=W::new(p,192);w.n((SIZE.min(u32::MAX as u64)) as u32).s(if SCAN{" 字节（计算中）\0".as_bytes()}else if PARTIAL{" 字节（部分统计）\0".as_bytes()}else{" 字节\0".as_bytes()});w.end();anchor=build_rows(c,anchor,&[(3,RowSpec::display("占用空间\0".as_bytes(),p))])?;
  if let Some(i)=i {let e=ENTRIES[i];let state=if protected(&e){"系统应用（已保护）\0"}else if e.flags&1!=0{"已隐藏\0"}else{"显示中\0"};anchor=build_rows(c,anchor,&[(4,RowSpec::display("状态\0".as_bytes(),state.as_ptr()))])?;
   if !protected(&e){anchor=build_rows(c,anchor,&[(8,RowSpec::clickable("打开应用\0".as_bytes()))])?;anchor=build_rows(c,anchor,&[(5,RowSpec::clickable(if EXCL_CONTEXT{if excluded(&e){"取消排除\0".as_bytes()}else{"加入排除项\0".as_bytes()}}else if e.flags&1!=0{"显示该应用\0".as_bytes()}else{"隐藏该应用\0".as_bytes()}))])?;
    if !excluded(&e){build_rows(c,anchor,&[(6,RowSpec::clickable(if CONFIRM{"确认卸载应用？\0".as_bytes()}else{"卸载应用\0".as_bytes()}))])?;}
   }
  }else{build_rows(c,anchor,&[(7,RowSpec::display("应用已移除或注册表不可用\0".as_bytes(),core::ptr::null()))])?;}Ok(())
 }}
 fn on_click(&self,i:usize){if i==5||i==6||i==8{REQUEST.store(i as u32,Ordering::Relaxed);}}
 fn needs_tick(&self)->bool{true}
 fn tick(&self){unsafe{
  if scan_tick(){render_req(DETAIL);}let a=REQUEST.swap(0,Ordering::Relaxed);if a==0{return;}if !snapshot(){notice("注册表不可用\0".as_bytes());return;}
  if let Some(i)=index(&TARGET){if a==8{CONFIRM=false;if protected(&ENTRIES[i]){return;}let pkg=TARGET;if launch(&pkg){notice("已提交打开请求\0".as_bytes());}return;}if a==5{CONFIRM=false;if EXCL_CONTEXT{if exclude_toggle(i){notice("排除项已更新\0".as_bytes());}}else if change(i,ENTRIES[i].flags&1==0){notice("操作完成\0".as_bytes());}else{notice(LAST_ERROR);}}
   if a==6{if CONFIRM{let pkg=TARGET;CONFIRM=false;if uninstall(&pkg){notice("已提交卸载请求\0".as_bytes());scan_close();}}else{CONFIRM=true;}}render_req(DETAIL);
  }
 }}
}
pub static DETAIL_PAGE:DetailPage=DetailPage;
pub struct SelectionPage;
impl Page for SelectionPage{
 fn fill_title(&self,p:*mut u8){unsafe{put_str(p,"批量操作\0".as_bytes());}}
 fn render(&self,c:&PageCtx)->PageResult{unsafe{
  if !snapshot(){build_rows(c,c.title,&[(0,RowSpec::display("注册表不可用\0".as_bytes(),core::ptr::null()))])?;return Ok(());}
  let p=core::ptr::addr_of_mut!(CAPTION) as *mut u8;let mut w=W::new(p,192);w.s("已选 ".as_bytes()).n(SELECT_N as u32).s(" / 已完成 ".as_bytes()).n(DONE as u32);w.end();
  let mut a=build_rows(c,c.title,&[(0,RowSpec::clickable(if SELECT_N>0{"取消全选\0".as_bytes()}else{"全选（跳过排除项）\0".as_bytes()})),(1,RowSpec::display(core::slice::from_raw_parts(p,w.len()+1),core::ptr::null())),(2,RowSpec::clickable("隐藏选中\0".as_bytes())),(3,RowSpec::clickable("显示选中\0".as_bytes())),(4,RowSpec::clickable(if CONFIRM{"确认卸载选中？\0".as_bytes()}else{"卸载选中\0".as_bytes()}))])?;
  let mut indices=[0usize;MAX];let mut count=0;for i in 0..N{if !protected(&ENTRIES[i])&&!excluded(&ENTRIES[i]){indices[count]=i;count+=1;}}
  let total=(count+4)/5;if WINDOW>=total{WINDOW=total.saturating_sub(1);}if WINDOW>0{a=build_rows(c,a,&[(5,RowSpec::clickable("上一页\0".as_bytes()))])?;}if WINDOW+1<total{a=build_rows(c,a,&[(6,RowSpec::clickable("下一页\0".as_bytes()))])?;}
  VIEW=[[0;PKG];5];VIEW_N=0;VIEW_SELECTED=SELECT_N;VIEW_DONE=DONE;VIEW_CONFIRM=CONFIRM;
  for slot in 0..5{let j=WINDOW*5+slot;if j>=count{break;}let e=ENTRIES[indices[j]];VIEW[slot]=e.pkg;VIEW_CHECK[slot]=selected(&e.pkg);VIEW_N+=1;let mut text=[0u8;PKG+8];let mut w=W::new(text.as_mut_ptr(),text.len());w.s(if selected(&e.pkg){b"[x] "}else{b"[ ] "}).s(bytes(&e.pkg));w.end();a=build_rows(c,a,&[(7+slot,RowSpec::clickable(&text[..w.len()+1]))])?;}Ok(())
 }}
 fn on_click(&self,i:usize){if i<12{REQUEST.store(i as u32+1,Ordering::Relaxed);}}
 fn needs_tick(&self)->bool{true}
 fn tick(&self){unsafe{let a=REQUEST.swap(0,Ordering::Relaxed);if a==0||QN!=0{return;}if !snapshot(){return;}let i=a as usize-1;match i{
  0=>{if SELECT_N>0{SELECT_N=0;}else{for j in 0..N{let e=ENTRIES[j];if !protected(&e)&&!excluded(&e){toggle(e.pkg);}}}CONFIRM=false;},
  2=>queue(0),3=>queue(1),4=>{if CONFIRM{queue(2);}else{CONFIRM=true;}},5=>{WINDOW=WINDOW.saturating_sub(1);CONFIRM=false;},6=>{WINDOW+=1;CONFIRM=false;},
  7..=11=>{let want=WINDOW*5+i-7;let mut j=0;for k in 0..N{let e=ENTRIES[k];if !protected(&e)&&!excluded(&e){if j==want{toggle(e.pkg);break;}j+=1;}}},_=>{}
 }if i==5||i==6{render_req(SELECT);}else{refresh_selection();}}}
}
pub static BATCH_PAGE:SelectionPage=SelectionPage;
