//! N67 persistent beautification choices. Restored only after Chaos is loaded.
use crate::*;
const PATHS:[&[u8];2]=[b"/data/chaos/n67-beautify-a.bin\0",b"/data/chaos/n67-beautify-b.bin\0"];
static mut LOADED:bool=false;
static mut CONFIG:[u8;4]=[1,255,0,1]; // restore font/icons, font, icon, restore background
static mut SAVED:[u8;4]=[1,255,0,1];
static mut GEN:u32=0;
static mut DIRTY:bool=false;
static mut SAVE_TRIES:u32=0;
static mut SAVE_WAIT:u32=0;
static mut FONT_CHANGED:bool=false;
static mut ICON_CHANGED:bool=false;
static mut RESTORED:bool=false;
static mut TOGGLE:u8=0;
fn checksum(b:&[u8])->u32{b.iter().fold(2166136261,|h,&v|(h^v as u32).wrapping_mul(16777619))}
fn decode(b:&[u8])->Option<([u8;4],u32)>{
 if b.len()!=16||&b[..4]!=b"NBR1"||b[4]>1||b[7]>1||(b[5]!=255&&b[5]>8)||b[6]>8{return None;}
 let word=|i|u32::from_le_bytes([b[i],b[i+1],b[i+2],b[i+3]]);
 if checksum(&b[..12])!=word(12){return None;}
 Some(([b[4],b[5],b[6],b[7]],word(8)))
}
unsafe fn read(path:&[u8])->Option<([u8;4],u32)>{
 let fd=fw_api::open(path.as_ptr(),1,0);if fd<0{return None;}
 let mut b=[0u8;17];let mut n=0;
 while n<17{let k=fw_api::read(fd,b.as_mut_ptr().add(n),(17-n) as u32);if k<=0||k as usize>17-n{break;}n+=k as usize;}
 let closed=fw_api::close(fd);if closed<0{return None;}decode(&b[..n])
}
pub unsafe fn load(){
 if LOADED{return;}LOADED=true;
 let a=read(PATHS[0]);let b=read(PATHS[1]);
 let chosen=match(a,b){(Some(a),Some(b))=>Some(if b.1.wrapping_sub(a.1) as i32>0{b}else{a}),(a,b)=>a.or(b)};
 if let Some((c,g))=chosen{CONFIG=c;SAVED=c;GEN=g;}
}
pub unsafe fn enabled()->bool{load();CONFIG[0]!=0}
pub unsafe fn background_enabled()->bool{load();CONFIG[3]!=0}
pub unsafe fn remember_font(slot:u32){load();if slot<=8{FONT_CHANGED=true;if CONFIG[1]!=slot as u8{CONFIG[1]=slot as u8;DIRTY=true;}}}
pub unsafe fn remember_icon(pack:u32){load();if pack<=8{ICON_CHANGED=true;if CONFIG[2]!=pack as u8{CONFIG[2]=pack as u8;DIRTY=true;}}}
pub unsafe fn request_toggle(kind:usize){if kind<2{TOGGLE|=1<<kind;}}
unsafe fn save()->bool{
 let gen=GEN.wrapping_add(1);let mut b=[0u8;16];b[..4].copy_from_slice(b"NBR1");b[4..8].copy_from_slice(&CONFIG);b[8..12].copy_from_slice(&gen.to_le_bytes());
 let check=checksum(&b[..12]);b[12..].copy_from_slice(&check.to_le_bytes());
 // NuttX O_EXCL=8 rejects an existing twin on the third save.
 // Fixed-size records need WRONLY|CREAT=6, not exclusive creation.
 let path=PATHS[(GEN&1) as usize];let fd=fw_api::open(path.as_ptr(),2|4,0o640);if fd<0{return false;}
 let mut n=0;while n<16{let k=fw_api::write(fd,b.as_ptr().add(n),(16-n) as u32);if k<=0||k as usize>16-n{break;}n+=k as usize;}
 let close=fw_api::close(fd);if n!=16||close<0||read(path)!=Some((CONFIG,gen)){return false;}
 GEN=gen;SAVED=CONFIG;true
}
pub unsafe fn tick(){
 load();let toggles=TOGGLE;TOGGLE=0;
 if toggles&1!=0{CONFIG[0]^=1;DIRTY=true;}
 if toggles&2!=0{CONFIG[3]^=1;DIRTY=true;}
 if DIRTY{
  if SAVE_WAIT>0{SAVE_WAIT-=1;}
  else if save(){DIRTY=false;SAVE_TRIES=0;crate::render_req(13);}
  else{
   SAVE_TRIES+=1;
   if SAVE_TRIES<3{SAVE_WAIT=20;}
   else{
    DIRTY=false;SAVE_TRIES=0;
    // A failed preference write cannot undo the independently queued font/icon.
    // Only restore switches roll back; retain the user's current selection.
    CONFIG[0]=SAVED[0];CONFIG[3]=SAVED[3];
    crate::notifications::request("选择未保存，下次载入可能恢复旧设置\0".as_bytes());
    crate::render_req(13);
   }
  }
 }
 if !RESTORED{
  if CONFIG[0]==0{RESTORED=true;}
  else if fw_api::screen_is_on()&&APP_FG==0&&font_apply::quiet()&&!icon_apply::restore_busy()&&(CONFIG[2]==0||icon_apply::desktop_ready()){
   RESTORED=true;
   if !FONT_CHANGED&&CONFIG[1]!=255{if !font_apply::restore_selection(CONFIG[1] as u32){crate::log::line("保存的字体不可用，保留系统字体");}}
   if !ICON_CHANGED&&!icon_apply::restore_selection(CONFIG[2] as u32){crate::log::line("保存的图标包不可用，保留系统图标");}
  }
 }
}
