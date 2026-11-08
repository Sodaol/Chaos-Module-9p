//! N67 GH225 / AW86225 bounded pulse, based on GH225-v18-adapter (mode4/parameter/start/stop).
use crate::fw_api;
use core::{mem::transmute,ptr::read_volatile as rd};
static mut FD:i32=-1;
static mut UNTIL:u32=0;
#[repr(C)]struct Parameter{reserved:u32,strength:f32,pattern:u32}
unsafe fn ioctl(fd:i32,cmd:u32,arg:u32)->i32{let f:unsafe extern "C" fn(i32,u32,u32)->i32=transmute(0x0c37e1b5usize);let rc=f(fd,cmd,arg);if rc==-1{let errno:unsafe extern "C" fn()->*const i32=transmute(0x0c0e4121usize);-rd(errno())}else{rc}}
unsafe fn valid(p:u32,n:u32)->bool{p%4==0&&((p>=0x20000000&&p<=0x20200000-n)||(p>=0x3c000020&&p<=0x3efffff8-n))}
unsafe fn lower(fd:i32)->u32{let get:unsafe extern "C" fn(i32,*mut u32)->i32=transmute(0x0c37c0d1usize);let mut file=0;if get(fd,&mut file)<0||!valid(file,20){return 0;}let inode=rd((file+16) as *const u32);if !valid(inode,32){return 0;}let upper=rd((inode+28) as *const u32);if !valid(upper,4){return 0;}let low=rd(upper as *const u32);if valid(low,16){low}else{0}}
// Unknown drivers delegate to the existing native effect service.
pub unsafe fn request(effect:u8)->Option<i32>{
 if FD>=0{return Some(-3);}
 let fd=fw_api::open(b"/dev/lra0\0".as_ptr(),0x403,0);if fd<0{return None;}
 let low=lower(fd);if low==0{fw_api::close(fd);return None;}
 let table=rd(low as *const u32);if table!=0x2c6f6754&&table!=0x2c6f66ac{fw_api::close(fd);return None;}
 if rd(0x200cbb6d as *const u8)!=0||rd(0x200cc6bc as *const u8)>1{fw_api::close(fd);return Some(-5);}
 if rd(0x200d6de4 as *const u8)!=0||rd(0x200d6dec as *const u8)!=0{fw_api::close(fd);return Some(-3);}
 let mut parameter=Parameter{reserved:0,strength:1.0,pattern:0};let mut rc=0;
 let mut strength=if effect==1{0.25f32}else{0.125f32};
 if rd((low+8) as *const u8)!=0{let limit=f32::from_bits(rd((low+12) as *const u32));if !limit.is_finite()||limit<=0.0{fw_api::close(fd);return Some(-34);}strength=strength.min(limit.min(0.5));}
 else{rc=ioctl(fd,0x3109,&parameter as *const _ as u32);}
 if rc>=0{rc=ioctl(fd,0x3108,4);}
 if rc>=0{parameter.strength=strength;rc=ioctl(fd,0x3105,&parameter as *const _ as u32);}
 if rc>=0{rc=ioctl(fd,0x3101,0);}
 if rc<0{FD=fd;UNTIL=fw_api::uptime_ms();tick();return Some(rc);}
 FD=fd;UNTIL=fw_api::uptime_ms().wrapping_add(if effect==1{150}else{60});Some(0)
}
#[export_name="chaos_gh225_tick"] pub unsafe fn tick(){if FD<0||(fw_api::uptime_ms().wrapping_sub(UNTIL) as i32)<0{return;}
 let mut rc=ioctl(FD,0x3102,0);if rc<0{rc=ioctl(FD,0x3102,0);}if rc<0{UNTIL=fw_api::uptime_ms().wrapping_add(50);return;}
 fw_api::close(FD);FD=-1;
}
