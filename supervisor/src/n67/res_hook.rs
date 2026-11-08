//! N67 LVGL8 image objects: exact stock paths + DRAW_MAIN_BEGIN events.
//! No P67 addresses, no filesystem or flash patch. Only current object trees
//! are dereferenced; DELETE retires journals. GPU-visible descriptors/pixels
//! are pinned for this boot, capped at 2 MiB; absent/bad assets keep stock images.
use core::{mem::transmute,ptr::{read_volatile as rd}};
use crate::{fw_api,safe_ptr,plausible_ptr,icon_apply};
struct Rule{path:&'static [u8],stem:&'static [u8],w:u32,h:u32}
const RULES:&[Rule]=&[
 Rule{path:b"S:/system/image/control_center/flashlight_all.rle",stem:b"ctrl_flashlight",w:64,h:64},
 Rule{path:b"S:/system/image/control_center/setting_all.rle",stem:b"ctrl_setting",w:64,h:64},
 Rule{path:b"S:/system/image/control_center/battery_all.rle",stem:b"ctrl_battery",w:64,h:64},
 Rule{path:b"S:/system/image/control_center/bright_open.rle",stem:b"ctrl_bright",w:64,h:64},
 Rule{path:b"S:/system/image/control_center/alarm_all.rle",stem:b"ctrl_alarm",w:64,h:64},
 Rule{path:b"S:/system/image/control_center/findphone_all.rle",stem:b"ctrl_findphone",w:64,h:64},
 Rule{path:b"S:/system/image/control_center/disturb_open.rle",stem:b"ctrl_disturb",w:64,h:64},
 Rule{path:b"S:/system/image/control_center/raise_open.rle",stem:b"ctrl_raise",w:64,h:64},
 Rule{path:b"S:/system/image/control_center/phone_conn.rle",stem:b"ctrl_phone_conn",w:48,h:48},
 Rule{path:b"S:/system/image/control_center/phone_disconn.rle",stem:b"ctrl_phone_disconn",w:48,h:48},
 Rule{path:b"S:/system/image/control_center/add.rle",stem:b"ctrl_add",w:48,h:48},
 Rule{path:b"S:/system/image/control_center/delete.rle",stem:b"ctrl_delete",w:48,h:48},
 Rule{path:b"S:/system/image/settings/icon/about.bin",stem:b"set_about",w:64,h:64},
 Rule{path:b"S:/system/image/settings/icon/applayout.bin",stem:b"set_applayout",w:64,h:64},
 Rule{path:b"S:/system/image/settings/icon/battery.bin",stem:b"set_battery",w:64,h:64},
 Rule{path:b"S:/system/image/settings/icon/dial.bin",stem:b"set_dial",w:64,h:64},
 Rule{path:b"S:/system/image/settings/icon/display.bin",stem:b"set_display",w:64,h:64},
 Rule{path:b"S:/system/image/settings/icon/disturb.bin",stem:b"set_disturb",w:64,h:64},
 Rule{path:b"S:/system/image/settings/icon/downkey.bin",stem:b"set_downkey",w:64,h:64},
 Rule{path:b"S:/system/image/settings/icon/guesture.bin",stem:b"set_guesture",w:64,h:64},
 Rule{path:b"S:/system/image/settings/icon/hr_boardcast.bin",stem:b"set_hr_boardcast",w:64,h:64},
 Rule{path:b"S:/system/image/settings/icon/motion.bin",stem:b"set_motion",w:64,h:64},
 Rule{path:b"S:/system/image/settings/icon/notify.bin",stem:b"set_notify",w:64,h:64},
 Rule{path:b"S:/system/image/settings/icon/sound.bin",stem:b"set_sound",w:64,h:64},
 Rule{path:b"S:/system/image/settings/icon/system.bin",stem:b"set_system",w:64,h:64},
 Rule{path:b"S:/system/image/settings/icon/wrist.bin",stem:b"set_wrist",w:64,h:64},
 Rule{path:b"S:/system/image/weather/i_clear.bin",stem:b"weather_clear",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_nclear.bin",stem:b"weather_nclear",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_pcloudy.bin",stem:b"weather_pcloudy",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_npcloudy.bin",stem:b"weather_npcloudy",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_fog.bin",stem:b"weather_fog",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_nfog.bin",stem:b"weather_nfog",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_haze.bin",stem:b"weather_haze",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_srain.bin",stem:b"weather_srain",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_mrain.bin",stem:b"weather_mrain",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_hrain.bin",stem:b"weather_hrain",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_storm.bin",stem:b"weather_storm",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_thunder.bin",stem:b"weather_thunder",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_ssnow.bin",stem:b"weather_ssnow",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_msnow.bin",stem:b"weather_msnow",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_hsnow.bin",stem:b"weather_hsnow",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_sleet.bin",stem:b"weather_sleet",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_rainsnow.bin",stem:b"weather_rainsnow",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_hail.bin",stem:b"weather_hail",w:48,h:48},
 Rule{path:b"S:/system/image/weather/i_native.bin",stem:b"weather_native",w:48,h:48},
 Rule{path:b"S:/system/image/heartrate/hr_abnormal.rle",stem:b"hr_abnormal",w:64,h:56},
 Rule{path:b"S:/system/image/heartrate/hr_explain.rle",stem:b"hr_explain",w:64,h:56},
 Rule{path:b"S:/system/image/heartrate/hr_rest.rle",stem:b"hr_rest",w:64,h:56},
 Rule{path:b"S:/system/image/heartrate/hr_setting.rle",stem:b"hr_setting",w:64,h:56},
 Rule{path:b"S:/system/image/heartrate/hr_zone.rle",stem:b"hr_zone",w:64,h:56},
 Rule{path:b"S:/system/image/heartrate/hr_zone_info.rle",stem:b"hr_zone_info",w:64,h:56},
 Rule{path:b"S:/system/image/oxygen/oxygan_ill_btn.rle",stem:b"oxygan_ill_btn",w:64,h:56},
 Rule{path:b"S:/system/image/oxygen/oxygan_low_ill_btn.rle",stem:b"oxygan_low_ill_btn",w:64,h:56},
 Rule{path:b"S:/system/image/oxygen/oxygen_setting.rle",stem:b"oxygen_setting",w:64,h:56},
];
pub const RULE_N:usize=RULES.len();
pub fn rule_stem(k:usize)->&'static [u8]{RULES.get(k).map(|r|r.stem).unwrap_or(b"")}
#[derive(Clone,Copy)]
#[repr(C)]
struct Journal{obj:u32,desc:u32,rule:usize,path:[u8;160]}
const EMPTY:Journal=Journal{obj:0,desc:0,rule:0,path:[0;160]};
static mut JOURNAL:[Journal;128]=[EMPTY;128];
static mut IMAGES:[[[u32;3];RULE_N];8]=[[[0;3];RULE_N];8];
static mut PACK:u32=0;static mut NEXT:usize=0;static mut BUSY:bool=false;
static mut ON:bool=false;static mut BYTES:u32=0;
static mut HIT:u32=0;static mut OK:u32=0;static mut FALLBACK:u32=0;
// The settings page is rebuilt every time it is opened. Keep only handles for
// the current tree; never retain a row across a page transition.
static mut SETTINGS_PARENT:u32=0;
static mut SETTINGS_ROW:u32=0;
static mut ABOUT_ROW:u32=0;
static mut WALK_TICKS:u32=0;
static mut WALK_ROOTS:[u32;3]=[0;3];
unsafe fn image_set(o:u32,s:u32){let f:unsafe extern "C" fn(u32,u32)=transmute(0xc2617d9usize);f(o,s);}
unsafe fn image_class(mut c:u32)->bool{
 for _ in 0..16{if c==0x2c68260c{return true;}if c&3!=0||c<0x2c080000||c+32>0x2c7ea290{return false;}let n=rd(c as *const u32);if c==n{return false;}c=n;}false
}
unsafe fn copy_path(p:u32)->Option<[u8;160]>{
 let mut b=[0u8;160];for i in 0..160{if !plausible_ptr(p+i as u32){return None;}let c=rd((p+i as u32) as *const u8);if c==0{return Some(b);}if c<32||c>126{return None;}b[i]=c;}None
}
fn matches(path:&[u8;160],r:&Rule)->bool{path.get(..r.path.len())==Some(r.path)&&path[r.path.len()]==0}
unsafe fn descriptor(k:usize)->u32{if PACK<1||PACK>8{return 0;}let d=&IMAGES[(PACK-1) as usize][k];if d[2]==0{0}else{d.as_ptr() as u32}}
unsafe fn load_rule(k:usize){
 if descriptor(k)!=0{return;}let r=&RULES[k];let size=r.w*r.h*4;
 if BYTES+size>2*1024*1024{FALLBACK=FALLBACK.wrapping_add(1);return;}
 let mut path=[0u8;96];let prefix=b"/data/chaos/icons/";path[..prefix.len()].copy_from_slice(prefix);let mut n=prefix.len();
 path[n]=b'0';path[n+1]=b'0'+PACK as u8;path[n+2]=b'/';n+=3;
 path[n..n+r.stem.len()].copy_from_slice(r.stem);n+=r.stem.len();path[n..n+4].copy_from_slice(b".bin");
 let fd=fw_api::open(path.as_ptr(),1,0);if fd<0{return;}
 let mut h=[0u8;4];let mut at=0;while at<4{let got=fw_api::read(fd,h.as_mut_ptr().add(at),4-at as u32);if got<=0{break;}at+=got as usize;}
 let header=5|(r.w<<10)|(r.h<<21);
 if at!=4||u32::from_le_bytes(h)!=header{fw_api::close(fd);FALLBACK=FALLBACK.wrapping_add(1);return;}
 let pixels=fw_api::heap_malloc(size);if !safe_ptr(pixels){fw_api::close(fd);return;}
 let mut used=0;while used<size{let got=fw_api::read(fd,(pixels+used) as *mut u8,(size-used).min(1024));if got<=0{break;}used+=got as u32;}
 let mut tail=[0u8;1];let extra=fw_api::read(fd,tail.as_mut_ptr(),1);fw_api::close(fd);
 if used!=size||extra!=0{fw_api::fw_free(pixels);FALLBACK=FALLBACK.wrapping_add(1);return;}
 IMAGES[(PACK-1) as usize][k]=[header,size,pixels];BYTES+=size;
}
unsafe fn update(o:u32,can_attach:bool){
 if !safe_ptr(o)||!image_class(rd(o as *const u32)){return;}
 let src=rd((o+36) as *const u32);
 let mut old=JOURNAL.iter().position(|j|j.obj==o);
 if let Some(i)=old{if JOURNAL[i].desc!=src{JOURNAL[i]=EMPTY;old=None;}}
 let (k,path)=if let Some(i)=old{(JOURNAL[i].rule,JOURNAL[i].path)}else{
  let Some(p)=copy_path(src)else{return;};let Some(k)=RULES.iter().position(|r|matches(&p,r))else{return;};(k,p)
 };
 let d=descriptor(k);
 if let Some(i)=old{if d==src{return;}image_set(o,JOURNAL[i].path.as_ptr() as u32);JOURNAL[i]=EMPTY;}
 if d==0||!ON{return;}
 // Preserve dimensions used by stock layout, including nonsquare health icons.
 if rd((o+44) as *const u16) as u32!=RULES[k].w||rd((o+46) as *const u16) as u32!=RULES[k].h{return;}
 let Some(i)=JOURNAL.iter().position(|j|j.obj==0)else{FALLBACK=FALLBACK.wrapping_add(1);return;};
 if can_attach {
  // Add a DELETE/draw listener once per object using its current event array.
  let spec=rd((o+8) as *const u32);if !safe_ptr(spec){return;}
  let arr=rd((spec+12) as *const u32);let n=rd((spec+26) as *const u8)&63;
  if n!=0&&!safe_ptr(arr){return;}
  let cb=chaos_n67_resource_event as *const () as u32;
  let mut found=false;for x in 0..n as u32{if rd((arr+x*12) as *const u32)==cb{found=true;break;}}
  if !found && (n>=63||fw_api::obj_add_event(o,cb,0,0)==0){return;}
 }
 HIT=HIT.wrapping_add(1);JOURNAL[i]=Journal{obj:o,desc:d,rule:k,path};
 image_set(o,d);if rd((o+36) as *const u32)==d{OK=OK.wrapping_add(1);}else{JOURNAL[i]=EMPTY;FALLBACK=FALLBACK.wrapping_add(1);}
}
#[no_mangle]
pub unsafe extern "C" fn chaos_n67_resource_event(e:u32){
 if !safe_ptr(e){return;}let o=rd(e as *const u32);if rd((e+4) as *const u32)!=o{return;}
 let code=rd((e+8) as *const u8)&127;
 if code==35{for j in JOURNAL.iter_mut(){if j.obj==o{*j=EMPTY;}}}
 else if code==21{update(o,false);}
}

unsafe extern "C" fn chaos_settings_row_event(e:u32){
  let code=fw_api::event_get_code(e);
  if code==fw_api::ev::CLICKED || code==fw_api::ev::ALL {
    fw_api::page_goto((fw_api::CHAOS_APP_ID<<16),0);
  }
}

unsafe fn is_about_image(o:u32)->bool{
  if !safe_ptr(o)||!image_class(rd(o as *const u32)){return false;}
  let src=rd((o+36) as *const u32);let Some(path)=copy_path(src)else{return false;};
  // Resource paths differ between regional builds. Match the stable final
  // component instead of requiring one exact absolute path.
  let bytes=path.as_slice();
  bytes.windows(9).any(|w|w==b"about.bin")
}

unsafe fn attach_about_entry(o:u32){
  if ABOUT_ROW!=0&&safe_ptr(ABOUT_ROW){return;}
  // The image receives the touch event on some builds; on others the event
  // is delivered to the enclosing row. Register on both objects.
  let cb=chaos_settings_row_event as *const () as u32;
  let mut hooked=0;
  if fw_api::obj_add_event(o,cb,fw_api::ev::ALL,0)!=0{hooked=o;}
  let mut p=rd((o+4) as *const u32);
  for _ in 0..8{
    if !safe_ptr(p){break;}
    let h=obj_i16(p,0x1a)-obj_i16(p,0x16)+1;
    if h>=40&&h<=140{
      if fw_api::obj_add_event(p,cb,fw_api::ev::ALL,0)!=0{hooked=p;}
      break;
    }
    p=rd((p+4) as *const u32);
  }
  if hooked!=0{
    ABOUT_ROW=hooked;
  }
}

unsafe fn obj_i16(o:u32,off:u32)->i32{rd((o+off) as *const i16) as i32}

// Find the native settings list without relying on a child index. Native rows
// are the only page objects in this tree that repeat with a compact height.
unsafe fn find_settings_list(o:u32,depth:u32,budget:&mut u32)->u32{
  if depth>=12||*budget==0||!safe_ptr(o){return 0;}
  *budget-=1;
  let spec=rd((o+8) as *const u32);if !safe_ptr(spec){return 0;}
  let arr=rd(spec as *const u32);let n=rd((spec+4) as *const u32);
  if n>160||(n>0&&!safe_ptr(arr)){return 0;}
  let mut compact=0;let mut last=0;let mut rows=0;
  for i in 0..n {
    let ch=rd((arr+i*4) as *const u32);if !safe_ptr(ch){continue;}
    if rd((ch+4) as *const u32)!=o{continue;}
    let h=obj_i16(ch,0x1a)-obj_i16(ch,0x16)+1;
    // Stock settings rows are normally 64/82 px, but the firmware may
    // report a transient geometry while the page is being laid out.
    if h>=40&&h<=120{compact+=1;last=ch;rows+=1;}
  }
  // Some settings pages expose only two rows in the current viewport.
  if compact>=2&&rows>=2{return o;}
  for i in 0..n {
    if *budget==0{break;}
    let ch=rd((arr+i*4) as *const u32);
    if safe_ptr(ch)&&rd((ch+4) as *const u32)==o{
      let found=find_settings_list(ch,depth+1,budget);if found!=0{return found;}
    }
  }
  let _=last;0
}

unsafe fn install_settings_row(){
  if fw_api::top_app_id()!=fw_api::SETTINGS_APP_ID{return;}
  let mut budget=768;let mut parent=0;
  for addr in [0xc239b69usize,0xc239c19,0xc239c55]{
    if budget==0{break;}
    let get:unsafe extern "C" fn(u32)->u32=transmute(addr);
    parent=find_settings_list(get(0),0,&mut budget);if parent!=0{break;}
  }
  if parent==0{return;}
  if SETTINGS_PARENT==parent && SETTINGS_ROW!=0 && safe_ptr(SETTINGS_ROW)
    && fw_api::obj_is_child_of(parent,SETTINGS_ROW){return;}
  SETTINGS_PARENT=parent;SETTINGS_ROW=0;
  let spec=rd((parent+8) as *const u32);if !safe_ptr(spec){return;}
  let arr=rd(spec as *const u32);let n=rd((spec+4) as *const u32);
  if n==0||n>160||!safe_ptr(arr){return;}
  let mut last=0;
  for i in 0..n {let ch=rd((arr+i*4) as *const u32);if safe_ptr(ch)&&rd((ch+4) as *const u32)==parent{last=ch;}}
  if last==0{return;}
  // Use the system list row and its native forward chevron.
  let row=fw_api::row_create(parent,b"Chaos\0".as_ptr(),fw_api::NONE_PTR,fw_api::trailing::FORWARD);
  if row==0{return;}
  fw_api::obj_set_size(row,312,64);
  fw_api::obj_align_to(row,last,fw_api::align::OUT_BOTTOM_MID,0,8);
  fw_api::obj_set_hidden(row,0);
  if fw_api::obj_add_event(row,chaos_settings_row_event as *const () as u32,fw_api::ev::CLICKED,0)==0{
    fw_api::obj_delete(row);return;
  }
  SETTINGS_ROW=row;
}
unsafe fn walk(o:u32,depth:u32,budget:&mut u32){
 if depth>=16||*budget==0||!safe_ptr(o){return;}*budget-=1;

 update(o,true);
 let spec=rd((o+8) as *const u32);if !safe_ptr(spec){return;}let arr=rd(spec as *const u32);let n=rd((spec+4) as *const u32);
 if n>160||(n>0&&!safe_ptr(arr)){return;}
 for i in 0..n {if *budget==0{break;}let ch=rd((arr+i*4) as *const u32);if safe_ptr(ch)&&rd((ch+4) as *const u32)==o{walk(ch,depth+1,budget);}}
}
pub unsafe fn install(){ON=true;}
pub unsafe fn uninstall(){ON=false;PACK=0;BUSY=false;}
pub unsafe fn refresh_cache(){PACK=icon_apply::cur_pack();NEXT=0;BUSY=PACK>=1&&PACK<=8;ON=true;}
pub unsafe fn pending()->bool{BUSY}
#[export_name="chaos_n67_resources_tick"]
#[inline(never)]
pub unsafe extern "C" fn tick(){
  if !fw_api::screen_is_on()||crate::ui_activity::scrolling(){return;}
  if fw_api::top_app_id()!=fw_api::SETTINGS_APP_ID{SETTINGS_PARENT=0;SETTINGS_ROW=0;ABOUT_ROW=0;}

 if PACK!=icon_apply::cur_pack(){refresh_cache();}
 if BUSY{load_rule(NEXT);NEXT+=1;if NEXT>=RULE_N{BUSY=false;}}
 if !ON&&JOURNAL.iter().all(|j|j.obj==0){return;}
 let mut roots=[0;3];
 for (i,addr) in [0xc239b69usize,0xc239c19,0xc239c55].iter().enumerate(){let get:unsafe extern "C" fn(u32)->u32=transmute(*addr);roots[i]=get(0);}
 WALK_TICKS=WALK_TICKS.wrapping_add(1);
 if roots==WALK_ROOTS&&!BUSY&&WALK_TICKS%8!=0{return;}
 WALK_ROOTS=roots;
 let mut budget=512;for root in roots{walk(root,0,&mut budget);}
}
pub unsafe fn counters()->(u32,u32,u32,u32){(ON as u32,HIT,OK,FALLBACK)}
pub unsafe fn sys_counters()->(u32,u32,u32){(HIT,OK,FALLBACK)}
pub unsafe fn cal_hit()->u32{0}
