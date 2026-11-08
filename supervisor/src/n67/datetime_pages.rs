//! Local civil-time editor; UTC RTC conversion is in time_set, shared with P67.
use crate::*;
use crate::page::Page;
use core::sync::atomic::{AtomicU32,Ordering};
static mut TIME:[u32;6]=[2026,1,1,0,0,0];
static mut DATE:[u32;6]=[2026,1,1,0,0,0];
static mut RESULT:[&'static [u8];2]=[b"\0",b"\0"];
static mut ERROR_TEXT:[[u8;96];2]=[[0;96];2];
static ACTION:[AtomicU32;2]=[AtomicU32::new(0),AtomicU32::new(0)];
static mut PICKERS:[u32;2]=[0;2];
static mut READY:[bool;2]=[false;2];
fn days(y:u32,m:u32)->u32 {
    match m {2=>if y%4==0&&(y%100!=0||y%400==0){29}else{28},4|6|9|11=>30,_=>31}
}
unsafe fn error(k:usize,rc:i32){
    let p=core::ptr::addr_of_mut!(ERROR_TEXT[k]) as *mut u8;let mut w=W::new(p,96);
    w.s("保存失败 (rc=".as_bytes());if rc<0{w.s(b"-");}w.n(rc.unsigned_abs()).s(b")");w.end();
    RESULT[k]=core::slice::from_raw_parts(p,w.len()+1);
}
unsafe fn render_editor(c:&PageCtx,k:usize)->PageResult{
    PICKERS=[0;2];
    // Center against the whole 424px editor, without list bottom padding.
    fw_api::content_pad_bottom(c.content,0,0);
    fw_api::date_caption(c.content,if k==0{"时\0".as_ptr()}else{"月\0".as_ptr()},20,24,132,22);
    fw_api::date_caption(c.content,if k==0{"分\0".as_ptr()}else{"日\0".as_ptr()},184,24,132,22);
    PICKERS[0]=if k==0{fw_api::date_picker(c.content,0,23,TIME[3],20)}else{fw_api::date_picker(c.content,1,12,DATE[1],20)};
    PICKERS[1]=if k==0{fw_api::date_picker(c.content,0,59,TIME[4],184)}else{fw_api::date_picker(c.content,1,31,DATE[2],184)};
    if PICKERS.contains(&0){return Err(PageError::RowFailed(0));}
    fw_api::date_caption(c.content,if k==0{b":\0".as_ptr()}else{b"/\0".as_ptr()},152,152,32,32);
    let row=fw_api::confirm_button(c.content);
    if row!=0{core::ptr::write_volatile(c.rows,row);fw_api::obj_add_event(row,row_ev_fn(0),7,0);}
    if row==0{return Err(PageError::RowFailed(0));}fw_api::date_confirm(row);Ok(())
}

pub unsafe fn enter(pid:usize) {
    if pid!=2&&pid!=3{return;}
    PICKERS=[0;2];
    let k=pid-2;ACTION[k].store(0,Ordering::Relaxed);
    RESULT[k]=b"\0";READY[k]=false;
    if let Some(tm)=crate::time_set::now_tm() {
        if tm[5]+1900>=2000 && tm[5]+1900<=2099 && (0..12).contains(&tm[4]) && (1..32).contains(&tm[3]) {
            let d=[(tm[5]+1900) as u32,(tm[4]+1) as u32,tm[3] as u32,tm[2] as u32,tm[1] as u32,tm[0] as u32];
            if k==0{TIME=d;}else{DATE=d;}READY[k]=true;
        }
    }
    if !READY[k]{RESULT[k]="读取系统时间失败\0".as_bytes();crate::notifications::request(RESULT[k]);}
}
pub struct DateTimePage { pid:usize }
impl Page for DateTimePage {
    fn fill_title(&self,p:*mut u8){unsafe{put_str(p,if self.pid==2{"时间设置\0".as_bytes()}else{"日期设置\0".as_bytes()});}}
    fn render(&self,c:&PageCtx)->PageResult{unsafe{
        render_editor(c,self.pid-2)
    }}
    fn on_click(&self,i:usize){if i==0{ACTION[self.pid-2].store(6,Ordering::Relaxed);}}
    fn needs_tick(&self)->bool{true}
    fn tick(&self){unsafe{
        let k=self.pid-2;let a=ACTION[k].swap(0,Ordering::Relaxed);
        if a==0{return;}if !READY[k]{crate::notifications::request(RESULT[k]);return;}
        let (lo0,hi0,lo1,hi1)=if k==0{(0,23,0,59)}else{(1,12,1,31)};
        let (Some(first),Some(second))=(fw_api::date_picker_value(PICKERS[0],lo0,hi0),fw_api::date_picker_value(PICKERS[1],lo1,hi1))else{
            RESULT[k]="请等待滚轮停止后重试\0".as_bytes();crate::notifications::request(RESULT[k]);render_req(self.pid);return;
        };
        let d=if k==0{&mut TIME}else{&mut DATE};
        if k==0{d[3]=first;d[4]=second;}else{d[1]=first;d[2]=second;}
        if a==6{
            // Refresh unedited fields so a visit does not freeze the clock.
            if let Some(now)=crate::time_set::now_tm(){
                if k==0 {d[0]=(now[5]+1900) as u32;d[1]=(now[4]+1) as u32;d[2]=now[3] as u32;}
                else {d[0]=(now[5]+1900) as u32;d[2]=d[2].min(days(d[0],d[1]));d[3]=now[2] as u32;d[4]=now[1] as u32;d[5]=now[0] as u32;}
            }else{RESULT[k]="读取时间失败，未保存\0".as_bytes();crate::notifications::request(RESULT[k]);render_req(self.pid);return;}
            let rc=crate::time_set::set(d[0],d[1],d[2],d[3],d[4],if k==0{0}else{d[5]});
            if rc<0{error(k,rc);}else{RESULT[k]=
                match crate::time_set::now_tm(){Some(tm) if tm[5]+1900==d[0] as i32&&tm[4]+1==d[1] as i32&&tm[3]==d[2] as i32&&tm[2]==d[3] as i32&&tm[1]==d[4] as i32=>"已保存\0".as_bytes(),_=>"已写入，回读不一致\0".as_bytes()}
            ;}
            crate::notifications::request(RESULT[k]);
            crate::log::kv("时间日期保存返回码",rc as u32);
        }
        render_req(self.pid);
    }}
}
pub static TIME_PAGE:DateTimePage=DateTimePage{pid:2};
pub static DATE_PAGE:DateTimePage=DateTimePage{pid:3};
