//! Axis-independent acceleration changes; nonblocking stock sensor subscription.
use crate::*;
static mut FD:i32=-1;
static mut NEXT_OPEN:u32=0;
static mut BASELINE:[f32;3]=[0.0;3];
static mut HAVE:bool=false;
static mut LAST_STAMP:u64=0;
static mut LAST_CLOCK:u32=0;
static mut HITS:u32=0;
static mut FIRST:u32=0;
static mut SAMPLES:u32=0;
static mut DETECTED:u32=0;
static mut OPEN_RC:i32=-1;
const TOPIC:u32=0x2c5eba9c;
#[repr(C,align(8))]struct Packet{stamp:u64,xyz:[f32;3],temperature:f32}
pub unsafe fn samples()->u32{SAMPLES}
pub unsafe fn detected()->u32{DETECTED}
pub unsafe fn result()->i32{OPEN_RC}
unsafe fn reset_motion(){HAVE=false;HITS=0;LAST_STAMP=0;}
unsafe fn close(){if FD>=0{fw_api::close(FD);FD=-1;}reset_motion();}
unsafe fn sample(p:&Packet,now:u32)->bool{
 if !p.xyz.iter().all(|v|v.is_finite()&&v.abs()<=200.0){reset_motion();return false;}
 if HAVE&&p.stamp==LAST_STAMP{return false;}
 if HAVE&&(p.stamp<LAST_STAMP||now.wrapping_sub(LAST_CLOCK)>500){reset_motion();}
 LAST_STAMP=p.stamp;LAST_CLOCK=now;SAMPLES=SAMPLES.saturating_add(1);
 let old=BASELINE;BASELINE=p.xyz;
 if !HAVE{HAVE=true;return false;}
 if SHAKE_COOL!=0||SHAKE_PENDING!=0{HITS=0;return false;}
 let mut delta=0.0;for i in 0..3{let d=p.xyz[i]-old[i];delta+=d*d;}
 if now.wrapping_sub(FIRST)>400{HITS=0;}
 if delta<16.0{return false;}
 if HITS==0{HITS=1;FIRST=now;return false;}
 if now.wrapping_sub(FIRST)<20{return false;}
 HITS=0;DETECTED=DETECTED.saturating_add(1);true
}
// Caller feeds a confirmed motion into the existing switch queue, never switches here.
#[export_name="chaos_accel_tick"] pub unsafe fn tick()->bool{
 let now=fw_api::uptime_ms();
 if SHAKE_EN==0||!fw_api::screen_is_on()||fw_api::top_app_id()!=fw_api::HOME_APP_ID||fw_api::watchface_is_on()==0{close();return false;}
 if FD<0{
  if (now.wrapping_sub(NEXT_OPEN) as i32)<0{return false;}
  NEXT_OPEN=now.wrapping_add(2000);
  if core::ptr::read_volatile((TOPIC+4) as *const u32)!=24{return false;}
  let subscribe:unsafe extern "C" fn(u32,u32)->i32=core::mem::transmute(0x0c104b9dusize);
  FD=subscribe(TOPIC,0);OPEN_RC=FD;if FD<0{return false;}reset_motion();
 }
 let mut hit=false;
 for _ in 0..2{let mut p=Packet{stamp:0,xyz:[0.0;3],temperature:0.0};
  let n=fw_api::read(FD,&mut p as *mut _ as *mut u8,24);
  if n<=0{break;}if n!=24{close();OPEN_RC=-22;break;}
  if sample(&p,now){hit=true;}
 }
 hit
}
