//! Allocation-free gesture telemetry; callbacks never render UI or switch faces.
use crate::*;
use core::sync::atomic::{AtomicU32,Ordering};
static EVENTS:AtomicU32=AtomicU32::new(0);
static SHAKES:AtomicU32=AtomicU32::new(0);
static CODE:AtomicU32=AtomicU32::new(0);
static WHY:AtomicU32=AtomicU32::new(0);
static QUEUED:AtomicU32=AtomicU32::new(0);
static SWITCHED:AtomicU32=AtomicU32::new(0);
static BLOCKED:AtomicU32=AtomicU32::new(0);
static CONTEXT:AtomicU32=AtomicU32::new(0);
static mut TEXT:[u8;384]=[0;384];
static mut TICKS:u32=0;
static mut SOURCE:i32=-1;
static mut SOURCE_RC:i32=-1;
static DIRECT:AtomicU32=AtomicU32::new(0);
static mut PACKET:[u32;4]=[0;4];

pub fn reason(v:u32){WHY.store(v,Ordering::Relaxed);match v{6=>{BLOCKED.fetch_add(1,Ordering::Relaxed);},8=>{QUEUED.fetch_add(1,Ordering::Relaxed);},9=>{SWITCHED.fetch_add(1,Ordering::Relaxed);},_=>{}}}
pub fn reset(){DIRECT.store(0,Ordering::Relaxed);QUEUED.store(0,Ordering::Relaxed);SWITCHED.store(0,Ordering::Relaxed);BLOCKED.store(0,Ordering::Relaxed);EVENTS.store(0,Ordering::Relaxed);SHAKES.store(0,Ordering::Relaxed);CODE.store(0,Ordering::Relaxed);CONTEXT.store(0,Ordering::Relaxed);reason(0);}
pub unsafe fn receive(event:u32)->u32{
 EVENTS.fetch_add(1,Ordering::Relaxed);
 if !safe_ptr(event)||!safe_ptr(event+0x1c)||mem::rd32((event+4) as *const u32)!=fw_api::TOPIC_QUICK_GUESTURE||mem::rd32((event+0x1c) as *const u32)<10{reason(1);return 0;}
 let payload=mem::rd32((event+0x18) as *const u32);
 if !safe_ptr(payload)||!safe_ptr(payload+8){reason(1);return 0;}
 let code=mem::rd16((payload+8) as *const u16) as u32;process(code)
}
unsafe fn process(code:u32)->u32{
 CODE.store(code,Ordering::Relaxed);
 if code!=GC_SHAKE{reason(2);return 0;}SHAKES.fetch_add(1,Ordering::Relaxed);
 let manager=mem::rd32(WF_MGR_PTR as *const u32);
 let flags=if safe_ptr(manager)&&safe_ptr(manager+0x6c){mem::rd16((manager+0x6c) as *const u16) as u32}else{0xffff};
 let top=fw_api::top_app_id();CONTEXT.store((top<<16)|flags,Ordering::Relaxed);
 if SHAKE_EN==0{reason(3);return 0;}
 if !fw_api::screen_is_on(){reason(4);return 0;}
 if top!=fw_api::HOME_APP_ID{reason(5);return 0;}
 if fw_api::watchface_is_on()==0{reason(6);return 0;}
 if SHAKE_COOL!=0{reason(7);return 0;}
 SHAKE_PENDING=1;reason(8);0
}
pub unsafe fn caption()->*const u8{
 let p=core::ptr::addr_of_mut!(TEXT) as *mut u8;let mut w=W::new(p,384);
 w.s("订阅：".as_bytes()).s(if SHAKE_SUB!=0{"有".as_bytes()}else{"无".as_bytes()});
 w.s(" 事件：".as_bytes()).n(EVENTS.load(Ordering::Relaxed)).s("\n摇动：".as_bytes()).n(SHAKES.load(Ordering::Relaxed));
 w.s(" 手势码：".as_bytes()).n(CODE.load(Ordering::Relaxed));
 let why=match WHY.load(Ordering::Relaxed){0=>"等待手势",1=>"事件格式不符",2=>"不是摇动",3=>"开关关闭",4=>"屏幕未亮",5=>"未回到表盘",6=>"可见状态阻挡",7=>"冷却中",8=>"等待切换",9=>"切换完成",10=>"没有其他参与表盘",11=>"切换接口失败",_=>"前台状态改变"};
 w.s(b"\n").s(why.as_bytes());let context=CONTEXT.load(Ordering::Relaxed);
 w.s("\n前台：".as_bytes()).n(context>>16).s(b" AOD:").n(context&255).s(b" VIS:").n((context>>8)&255);
 w.s("\n排队：".as_bytes()).n(QUEUED.load(Ordering::Relaxed)).s(" 切换：".as_bytes()).n(SWITCHED.load(Ordering::Relaxed));
 w.s("\n可见阻挡：".as_bytes()).n(BLOCKED.load(Ordering::Relaxed));
 w.s("\n直读：".as_bytes()).n(DIRECT.load(Ordering::Relaxed)).s(b" FD:");
 if SOURCE_RC<0{w.s(b"-");}w.n(SOURCE_RC.unsigned_abs());
 w.s("\n加速度样本：".as_bytes()).n(crate::accel_shake::samples()).s(" 命中：".as_bytes()).n(crate::accel_shake::detected());
 let rc=crate::accel_shake::result();w.s(b" FD:");if rc<0{w.s(b"-");}w.n(rc.unsigned_abs());
 w.end();p
}
pub unsafe fn tick(){
 if crate::accel_shake::tick(){process(GC_SHAKE);}
 TICKS=TICKS.wrapping_add(1);
 // Same native uORB subscription called by data_proxy's dispatcher. It opens
 // O_RDONLY|O_NONBLOCK (0x401); no waiting/read loop on the GUI thread.
 if SHAKE_EN==0{
  if SOURCE>=0{fw_api::close(SOURCE);SOURCE=-1;SOURCE_RC=-1;}
 }else if fw_api::screen_is_on()&&TICKS%2==0{
  if SOURCE<0&&TICKS%20==0{
   let subscribe:unsafe extern "C" fn(u32,u32)->i32=core::mem::transmute(0x0c104b9dusize);
   SOURCE=subscribe(fw_api::TOPIC_QUICK_GUESTURE,0);SOURCE_RC=SOURCE;
  }
  if SOURCE>=0{
   let count=fw_api::read(SOURCE,core::ptr::addr_of_mut!(PACKET) as *mut u8,16);
   if count==16{
    DIRECT.fetch_add(1,Ordering::Relaxed);
    EVENTS.fetch_add(1,Ordering::Relaxed);
    process(PACKET[2]&0xffff);
   }
  }
 }
 if TICKS%20!=0||APP_FG==0||FG_PAGE!=10||PAGES[10].built==0||!page_is_live(10){return;}
 let row=core::ptr::read_volatile(page_rows_ptr(10).add(3));if row!=0{fw_api::row_update(row,fw_api::NONE_PTR,fw_api::NONE_PTR,caption(),0,0);}
}
