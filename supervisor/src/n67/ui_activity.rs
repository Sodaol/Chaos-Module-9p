//! Scroll callbacks record a timestamp only; heavier maintenance resumes after settling.
use crate::{fw_api,safe_ptr};
static mut LAST:u32=0;
static mut VALID:bool=false;
unsafe extern "C" fn scroll(e:u32){
 if safe_ptr(e)&&fw_api::event_get_code(e)==11{LAST=fw_api::uptime_ms();VALID=true;}
}
pub unsafe fn bind(o:u32){fw_api::obj_add_event(o,scroll as *const () as u32,11,0);}
pub unsafe fn scrolling()->bool{VALID&&fw_api::uptime_ms().wrapping_sub(LAST)<180}
