//! N67 app registry + launcher adapter. Policy lives in a separate checksummed file.
//! N67 nodes are 60 bytes; hidden is byte +0x38 bit 0, not P67 +0x3c.
use crate::*;
use crate::page::Page;
use core::ptr::{read_volatile as rd,write_volatile as wr};
use core::sync::atomic::{AtomicU32,Ordering};
const MAX:usize=96;
const PKG:usize=96;
const CAP:usize=8+MAX*(PKG+1)+4;
const PATH:&[u8]=b"/data/chaos/n67-app-policy.bin\0";
const TEMP:&[u8]=b"/data/chaos/n67-app-policy.tmp\0";
#[derive(Clone,Copy)]
struct Entry { node:u32,id:u32,flags:u8,pkg:[u8;PKG] }
const EMPTY:Entry=Entry{node:0,id:0,flags:0,pkg:[0;PKG]};
#[derive(Clone,Copy)]
struct Policy { flags:u8,pkg:[u8;PKG] }
const NO_POLICY:Policy=Policy{flags:0,pkg:[0;PKG]};
static mut ENTRIES:[Entry;MAX]=[EMPTY;MAX];
static mut N:usize=0;
static mut POLICIES:[Policy;MAX]=[NO_POLICY;MAX];
static mut PN:usize=0;
static mut IO:[u8;CAP]=[0;CAP];
static mut LOADED:bool=false;
static mut VALID:bool=false;
static mut WINDOW:[usize;2]=[0;2];
static mut MESSAGE:&'static [u8]=b"\0";
static mut LAST_ERROR:&'static [u8]=b"\0";
static mut LINE:[u8;144]=[0;144];
static ACTION:[AtomicU32;2]=[AtomicU32::new(0),AtomicU32::new(0)];
static mut BATCH:Option<(usize,bool)>=None;
static mut BOOT_TICKS:u32=0;
static mut BOOT_INDEX:usize=0;

fn sum(b:&[u8])->u32{b.iter().fold(0x811c9dc5u32,|h,&c|(h^(c as u32)).wrapping_mul(16777619))}
unsafe fn fail(message:&'static [u8])->bool{LAST_ERROR=message;false}
fn policy_for(pkg:&[u8;PKG])->Option<usize>{unsafe{(0..PN).find(|&i|POLICIES[i].pkg==*pkg)}}
unsafe fn read_policy()->bool{
    if LOADED{return true;}
    let fd=fw_api::open(PATH.as_ptr(),1,0);
    if fd<0{LOADED=true;return true;}
    let mut n=0;
    while n<CAP{let k=fw_api::read(fd,IO.as_mut_ptr().add(n),(CAP-n) as u32);if k<0{fw_api::close(fd);return false;}if k==0{break;}if k as usize>CAP-n{fw_api::close(fd);return false;}n+=k as usize;}
    let mut extra=0u8;let trailing=fw_api::read(fd,&mut extra,1);fw_api::close(fd);
    if trailing!=0||n<12||&IO[..4]!=b"NAM1"{return false;}
    let count=u16::from_le_bytes([IO[4],IO[5]]) as usize;
    if count>MAX||n!=8+count*(PKG+1)+4{return false;}
    if sum(&IO[..n-4])!=u32::from_le_bytes(IO[n-4..n].try_into().unwrap()){return false;}
    for i in 0..count{
        let at=8+i*(PKG+1);
        if IO[at]>3||IO[at+1]==0||!IO[at+1..at+1+PKG].contains(&0){return false;}
        let mut pkg=[0;PKG];pkg.copy_from_slice(&IO[at+1..at+1+PKG]);
        if (0..i).any(|j|POLICIES[j].pkg==pkg){return false;}
        POLICIES[i]=Policy{flags:IO[at],pkg};
    }
    PN=count;LOADED=true;true
}
unsafe fn save_policy()->bool{
    IO[..8].fill(0);IO[..4].copy_from_slice(b"NAM1");IO[4..6].copy_from_slice(&(PN as u16).to_le_bytes());
    for i in 0..PN{let at=8+i*(PKG+1);IO[at]=POLICIES[i].flags;IO[at+1..at+1+PKG].copy_from_slice(&POLICIES[i].pkg);}
    let end=8+PN*(PKG+1);let checksum=sum(&IO[..end]);IO[end..end+4].copy_from_slice(&checksum.to_le_bytes());
    // N67 C file engine uses WRONLY|CREAT|TRUNC = 2|4|8.
    let fd=fw_api::open(TEMP.as_ptr(),2|4|8,0o640);if fd<0{return fail("策略临时文件无法打开\0".as_bytes());}
    let mut at=0;let size=end+4;
    while at<size{let k=fw_api::write(fd,IO.as_ptr().add(at),(size-at) as u32);if k<=0||k as usize>size-at{fw_api::close(fd);return fail("策略写入失败\0".as_bytes());}at+=k as usize;}
    if fw_api::close(fd)<0{return fail("策略文件关闭失败\0".as_bytes());}
    if fw_api::rename(TEMP.as_ptr(),PATH.as_ptr())!=0{return fail("策略文件提交失败\0".as_bytes());}
    true
}
unsafe fn snapshot()->bool{
    N=0;VALID=false;
    if !read_policy(){MESSAGE="应用策略损坏，未修改应用\0".as_bytes();return false;}
    let sent=rd(fw_api::APP_REGISTRY as *const u32);
    if !safe_ptr(sent){return false;}
    let mut prev=sent;let mut node=rd((sent+4) as *const u32);let mut count=0;
    while node!=sent{
        if count>=MAX||!safe_ptr(node)||rd(node as *const u32)!=prev{return false;}
        let next=rd((node+4) as *const u32);
        if !safe_ptr(next){return false;}
        let id=rd((node+0x10) as *const u16) as u32;
        let pkg=rd((node+8) as *const u32);
        let icon=rd((node+12) as *const u32);
        if icon!=0&&id!=0&&id!=fw_api::CHAOS_APP_ID&&safe_ptr(pkg){
            let mut name=[0u8;PKG];let mut k=0;
            while k<PKG-1{let c=rd((pkg+k as u32) as *const u8);if c==0{break;}name[k]=c;k+=1;}
            if k==0||k==PKG-1&&rd((pkg+k as u32) as *const u8)!=0{return false;}
            if core::str::from_utf8(&name[..k]).is_err(){return false;}
            if (0..N).any(|i|ENTRIES[i].pkg==name||ENTRIES[i].id==id){return false;}
            ENTRIES[N]=Entry{node,id,flags:rd((node+0x38) as *const u8),pkg:name};N+=1;
        }
        count+=1;prev=node;node=next;
    }
    if rd(sent as *const u32)!=prev{return false;}
    VALID=true;true
}
// N67 3.1.190 load_apps (0xc2a490a..0xc2a4918) distinguishes the native
// app range 0..=0x51 from dynamically installed apps. Do not guess by package
// prefix or replaceable icon path; old policies cannot override this boundary.
fn protected(e:&Entry)->bool{
    e.id<=0x51||e.id==fw_api::CHAOS_APP_ID
}
unsafe fn excluded(e:&Entry)->bool{
    if protected(e){return true;}
    policy_for(&e.pkg).map(|i|POLICIES[i].flags&2!=0).unwrap_or(e.id==16||e.id==22)
}
unsafe fn desktop_record(id:u32)->Option<u32>{
    let head=fw_api::LAUNCHER_DESKTOP_LIST;
    let link=rd(head as *const u32);if link!=24{return None;}
    let mut node=rd((head+4) as *const u32);let mut prev=0;let mut count=0;let mut found=0;
    while node!=0{
        if !safe_ptr(node)||count>=160||rd((node+link) as *const u32)!=prev{return None;}
        if rd(node as *const u16) as u32==id{if found!=0{return None;}found=node;}
        prev=node;node=rd((node+link+4) as *const u32);count+=1;
    }
    if rd((head+8) as *const u32)!=prev{return None;}
    Some(found)
}
unsafe fn visible(id:u32)->Option<bool>{desktop_record(id).map(|p|p!=0)}
// Rust's read_volatile::<u32> requires alignment even when the CPU's LDR
// tolerates unaligned addresses. Read these packed links as volatile bytes.
unsafe fn read_unaligned_word(address:u32)->u32{
    let p=address as *const u8;
    u32::from_le_bytes([rd(p),rd(p.add(1)),rd(p.add(2)),rd(p.add(3))])
}
// sort_apps uses an independent intrusive list: 128-byte package, flags at
// +0x80, unaligned links at +0x81/+0x85. The ROM-initialized list header
// at 0x200a4034 contains 129, not an aligned sizeof(struct) of 132.
// Startup copies it from 0x2c7deb00 (RW image source 0x2c7d1114 -> 0x20096648).
unsafe fn order_record(pkg:&[u8;PKG])->Option<u32>{
    let head=0x200a4034u32;
    let link=rd(head as *const u32);if link!=0x81{return None;}
    let mut node=rd((head+4) as *const u32);let mut prev=0;let mut count=0;let mut found=0;
    while node!=0{
        if !safe_ptr(node)||count>=160||read_unaligned_word(node+link)!=prev{return None;}
        let mut same=true;let mut len=0;
        while len<128{let c=rd((node+len) as *const u8);
            if len as usize>=PKG||c!=pkg[len as usize]{same=false;}
            if c==0{break;}len+=1;}
        if len==0||len==128{return None;}
        if same{if found!=0{return None;}found=node;}
        count+=1;prev=node;node=read_unaligned_word(node+link+4);
    }
    if rd((head+8) as *const u32)!=prev{return None;}
    Some(found)
}
unsafe fn set_native(e:&Entry,hide:bool)->bool{set_native_impl(e,hide,false)}
unsafe fn set_native_impl(e:&Entry,hide:bool,own:bool)->bool{
    if hide&&protected(e)&&!(own&&e.id==fw_api::CHAOS_APP_ID){return fail("系统应用已保护\0".as_bytes());}
    if rd((e.node+0x10) as *const u16) as u32!=e.id{return fail("应用注册信息已改变\0".as_bytes());}
    let name=rd((e.node+8) as *const u32);
    if !safe_ptr(name){return fail("应用包名不可用\0".as_bytes());}
    for i in 0..PKG{if rd((name+i as u32) as *const u8)!=e.pkg[i]{return fail("应用包名已改变\0".as_bytes());}if e.pkg[i]==0{break;}}
    let record=match desktop_record(e.id){Some(v)=>v,None=>return fail("桌面链未就绪或校验失败\0".as_bytes())};
    let order=match order_record(&e.pkg){Some(v)=>v,None=>return fail("排序链未就绪或校验失败\0".as_bytes())};
    let p=(e.node+0x38) as *mut u8;let old=rd(p);
    wr(p,if hide{old|1}else{old&!1});
    // Native launcher_remove also deletes the package's persistent order
    // record. Hide only the desktop record; add then reuses the native order.
    if hide&&record!=0{fw_api::launcher_hide_record(record,order);}
    else if !hide&&record==0{fw_api::launcher_add(e.id);}
    if visible(e.id)==Some(!hide){true}else{wr(p,old);fail("桌面显隐状态核对失败\0".as_bytes())}
}
unsafe fn change(index:usize,hide:bool)->bool{
    LAST_ERROR="应用操作失败\0".as_bytes();
    if !VALID||index>=N{return fail("应用列表已改变\0".as_bytes());}
    let e=ENTRIES[index];let old_hide=e.flags&1!=0;
    if hide&&protected(&e){return fail("系统应用已保护\0".as_bytes());}
    if old_hide==hide{return true;}
    let old_n=PN;let i=match policy_for(&e.pkg){Some(i)=>i,None if PN<MAX=>{let i=PN;PN+=1;POLICIES[i]=Policy{pkg:e.pkg,flags:if excluded(&e){2}else{0}};i},_=>return false};
    let old=POLICIES[i];POLICIES[i].flags=(old.flags&2)|hide as u8;
    if !set_native(&e,hide){POLICIES[i]=old;PN=old_n;return false;}
    if !save_policy(){let error=LAST_ERROR;POLICIES[i]=old;PN=old_n;
        if set_native(&e,old_hide){LAST_ERROR=error;}
        else{LAST_ERROR="保存失败，桌面恢复失败\0".as_bytes();}
        return false;}
    crate::log::pkg(if hide{"隐藏 "}else{"显示 "},e.pkg.as_ptr());
    ENTRIES[index].flags=if hide{e.flags|1}else{e.flags&!1};true
}
pub unsafe fn enter(pid:usize){details::leave(pid);if pid==1||pid==7{ACTION[if pid==1{0}else{1}].store(0,Ordering::Relaxed);let _=snapshot();}}
pub unsafe fn maintenance(){
    details::maintain();
    BOOT_TICKS=BOOT_TICKS.wrapping_add(1);
    if BOOT_TICKS<60||BOOT_TICKS%20!=0||crate::ui_activity::scrolling(){return;}
    if !snapshot(){return;}
    if BOOT_INDEX>=MAX{
        // Phone synchronization can replace registry nodes and reset hidden bits.
        // Work from package identity, never keep pointers into the old registry.
        for p in &POLICIES[..PN]{
            if p.flags&1==0{continue;}
            if let Some(i)=(0..N).find(|&i|ENTRIES[i].pkg==p.pkg){let e=ENTRIES[i];
                if !protected(&e)&&(e.flags&1==0||visible(e.id)==Some(true)){let _=set_native(&e,true);}
            }
        }
        return;
    }
    if BOOT_INDEX>=PN{BOOT_INDEX=MAX;return;}
    let p=POLICIES[BOOT_INDEX];
    if p.flags&1!=0{if let Some(i)=(0..N).find(|&i|ENTRIES[i].pkg==p.pkg){
        let e=ENTRIES[i];
        if protected(&e){
            // Repair system apps hidden by a previous version. Keep the old
            // policy on a failed commit so the next module load retries it.
            if !set_native(&e,false){return;}
            POLICIES[BOOT_INDEX].flags=(p.flags&!1)|2;
            if !save_policy(){POLICIES[BOOT_INDEX]=p;return;}
        }else if !set_native(&e,true){return;}
    }}
    BOOT_INDEX+=1;
}
pub struct AppsPage { exclude:bool }
impl Page for AppsPage{
    fn fill_title(&self,p:*mut u8){unsafe{put_str(p,if self.exclude{"排除项\0".as_bytes()}else{"应用管理\0".as_bytes()});}}
    fn render(&self,c:&PageCtx)->PageResult{unsafe{
        let k=self.exclude as usize;let _=snapshot();let mut anchor=c.title;
        if !VALID{build_rows(c,anchor,&[(0,RowSpec::display("注册表或策略不可用\0".as_bytes(),core::ptr::null()))])?;return Ok(());}
        if !self.exclude{anchor=build_rows(c,anchor,&[
            (0,RowSpec::clickable("隐藏全部（跳过排除项）\0".as_bytes())),
            (1,RowSpec::clickable("显示全部（跳过排除项）\0".as_bytes())),
            (2,RowSpec::clickable("排除项管理\0".as_bytes())),
            (5,RowSpec::clickable("批量选择操作\0".as_bytes())),
        ])?;}
        let total=(N+5)/6;if WINDOW[k]>=total{WINDOW[k]=total.saturating_sub(1);}
        if WINDOW[k]>0{anchor=build_rows(c,anchor,&[(3,RowSpec::clickable("上一页\0".as_bytes()))])?;}
        if WINDOW[k]+1<total{anchor=build_rows(c,anchor,&[(4,RowSpec::clickable("下一页\0".as_bytes()))])?;}
        for slot in 0..6{let i=WINDOW[k]*6+slot;if i>=N{break;}let e=ENTRIES[i];let buf=core::ptr::addr_of_mut!(LINE) as *mut u8;let mut w=W::new(buf,144);
            w.s(if self.exclude{if excluded(&e){b"[x] "}else{b"[ ] "}}else{if e.flags&1!=0{b"[-] "}else if protected(&e){b"[S] "}else{b"[+] "}});
            let len=e.pkg.iter().position(|&b|b==0).unwrap_or(PKG);w.s(&e.pkg[..len]);w.end();
            anchor=build_rows(c,anchor,&[(slot+6,RowSpec::clickable(core::slice::from_raw_parts(buf,w.len()+1)))])?;
        }Ok(())
    }}
    fn on_click(&self,i:usize){if i<12{ACTION[self.exclude as usize].store(i as u32+1,Ordering::Relaxed);}}
    fn needs_tick(&self)->bool{true}
    fn tick(&self){unsafe{
        let k=self.exclude as usize;let a=ACTION[k].swap(0,Ordering::Relaxed);
        if a==0 {
            if !self.exclude {if let Some((at,hide))=BATCH{
                if !snapshot(){BATCH=None;MESSAGE="注册表改变，批量已停止\0".as_bytes();render_req(1);return;}
                if at>=N{BATCH=None;MESSAGE="批量操作完成\0".as_bytes();crate::notifications::request(MESSAGE);render_req(1);}else{
                if !excluded(&ENTRIES[at])&&!change(at,hide){BATCH=None;MESSAGE=LAST_ERROR;crate::notifications::request(MESSAGE);render_req(1);return;}BATCH=Some((at+1,hide));
            }}}
            return;
        }
        if !snapshot(){MESSAGE="注册表校验失败\0".as_bytes();crate::notifications::request(MESSAGE);render_req(if self.exclude{7}else{1});return;}
        let i=a as usize-1;
        if !self.exclude&&i==2{nav_goto(7,0);return;}
        if !self.exclude&&i==5{details::open_selection();return;}
        if i==3{WINDOW[k]=WINDOW[k].saturating_sub(1);}
        else if i==4{WINDOW[k]+=1;}
        else if !self.exclude&&i<2{BATCH=Some((0,i==0));MESSAGE="批量处理中\0".as_bytes();}
        else if i>=6{
            let index=WINDOW[k]*6+i-6;if index>=N{return;}
            details::open(index,self.exclude);return;
        }
        if i!=3&&i!=4{crate::notifications::request(MESSAGE);}
        render_req(if self.exclude{7}else{1});
    }}
}
pub static APPS_PAGE:AppsPage=AppsPage{exclude:false};
pub static EXCLUDE_PAGE:AppsPage=AppsPage{exclude:true};

// Only the dedicated Chaos launcher preference may bypass self-protection.
// System applications remain protected in both this path and bulk operations.
pub unsafe fn own_visibility(show:bool)->bool{
 let sent=rd(fw_api::APP_REGISTRY as *const u32);if !safe_ptr(sent){return false;}
 let mut node=rd((sent+4) as *const u32);let mut prev=sent;
 for _ in 0..MAX{
  if node==sent{return false;}
  if !safe_ptr(node)||rd(node as *const u32)!=prev{return false;}
  if rd((node+0x10) as *const u16) as u32==fw_api::CHAOS_APP_ID{
   let p=rd((node+8) as *const u32);if !safe_ptr(p){return false;}
   let name=b"com.chaos.manager\0";let mut pkg=[0u8;PKG];
   for i in 0..name.len(){if rd((p+i as u32) as *const u8)!=name[i]{return false;}pkg[i]=name[i];}
   let e=Entry{node,id:fw_api::CHAOS_APP_ID,flags:rd((node+0x38) as *const u8),pkg};
   return set_native_impl(&e,!show,true);
  }
  prev=node;node=rd((node+4) as *const u32);
 }false
}

#[path="app_details.rs"]
mod details;
pub use details::{DETAIL_PAGE,BATCH_PAGE};
