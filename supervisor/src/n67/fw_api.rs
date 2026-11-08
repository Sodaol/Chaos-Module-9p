//! N67 CN 3.1.190 / LVGL 8 compatibility layer. No P67 addresses are callable.
#![allow(dead_code)]
use core::{mem::transmute,ptr::{read_volatile as rd,write_volatile as wr}};
pub type Obj=u32; pub type Cb=u32; pub type Cp=*const u8;
pub const NONE_PTR:Cp=core::ptr::null();
pub const MAX_ROWS_PER_PAGE:usize=12;
pub mod align {pub const DEFAULT:u32=0;pub const TOP_LEFT:u32=1;pub const TOP_MID:u32=2;pub const TOP_RIGHT:u32=3;pub const CENTER:u32=9;pub const OUT_BOTTOM_LEFT:u32=13;pub const OUT_BOTTOM_MID:u32=14;pub const OUT_BOTTOM_RIGHT:u32=15;}
pub mod ev {pub const ALL:u32=0;pub const CLICKED:u32=7;pub const VALUE_CHANGED:u32=30;}
pub mod trailing {pub const NONE:u32=0;pub const SWITCH:u32=1;pub const CHECKBOX:u32=2;pub const FORWARD:u32=3;}
pub mod oflag {pub const RDONLY:u32=1;pub const WRONLY:u32=2;pub const RDWR:u32=3;pub const CREAT:u32=4;}
pub const DESC_ROOT:u32=0x2c;
pub const APP_REGISTRY:u32=0x200a1dd0;pub const APPN_ICON:u32=0xc;pub const APPN_ID:u32=0x10;
pub const LAUNCHER_DESKTOP_LIST:u32=0x200a3938;
pub const LV_STYLE_TEXT_FONT:u32=0x57;
// N67 3.1.190 page IDs: watchface/launcher=16, settings=22.
pub const HOME_APP_ID:u32=16;
pub const SETTINGS_APP_ID:u32=22;
pub const CHAOS_APP_ID:u32=0xe7d4;
pub const BAR_W:i32=272;pub const BAR_H:i32=12;pub const BAR_FILL_RGB:u32=0x12b7ff;pub const BAR_FILL_GREEN:u32=0x75e000;pub const TEXT_GRAY_SUB:u32=0xd0d5dd;
pub const TOPIC_QUICK_GUESTURE:u32=0x2c67c708;
#[derive(Clone,Copy)]
struct Row{obj:u32,parent:u32,label:u32,sub:u32,check:u32,kind:u32,display:bool,y:i32,h:i32}
const EMPTY:Row=Row{obj:0,parent:0,label:0,sub:0,check:0,kind:0,display:false,y:0,h:80};
static mut ROWS:[Row;256]=[EMPTY;256];
static mut FONT:u32=0;
static mut SMALL_FONT:u32=0;
static mut EXTRA_FONTS:[(u32,u32);12]=[(0,0);12];
pub const PAGE_BG:u32=0x000000;pub const CARD_BG:u32=0x292c34;pub const BLUE:u32=0x0a84ff;
static mut GESTURE:u32=65536;static mut EVENT_BUBBLE:u32=131072;static mut PRESS_LOCK:u32=8192;
pub unsafe fn set_flags(g:u32,e:u32,p:u32){GESTURE=g;EVENT_BUBBLE=e;PRESS_LOCK=p;}
pub static mut MSGBOX_INSTANCE:u32=0;
pub fn msgbox_instance()->u32 {unsafe{MSGBOX_INSTANCE}}
unsafe fn index(o:u32)->Option<usize>{ROWS.iter().position(|r|r.obj==o&&o!=0)}
unsafe fn slot(o:u32,p:u32,h:i32)->Option<usize>{let i=ROWS.iter().position(|r|r.obj==0)?;ROWS[i]=Row{obj:o,parent:p,h,..EMPTY};Some(i)}
pub unsafe fn prop(o:u32,p:u32,v:u32){let f:unsafe extern "C" fn(u32,u32,u32,u32)=transmute(0x0c242e8busize);f(o,p,if p==0x20||p==0x55 {v|0xff000000}else{v},0);}
pub unsafe fn flags(o:u32,add:bool,f:u32){let fun:unsafe extern "C" fn(u32,u32)=transmute(if add{0x0c23ba45usize}else{0x0c23babbusize});fun(o,f);}
pub unsafe fn object(p:u32)->u32{let f:unsafe extern "C" fn(u32)->u32=transmute(0x0c23f09dusize);let o=f(p);if o!=0 {prop(o,0x32,0);prop(o,0x35,0);prop(o,0x39,0);for k in 0x10..=0x13{prop(o,k,0);}prop(o,0x20,CARD_BG);prop(o,0x21,255);flags(o,false,0x10|PRESS_LOCK); }o}
pub unsafe extern "C" fn obj_set_size(o:u32,w:i32,h:i32)->u32{let f:unsafe extern "C" fn(u32,i32,i32)=transmute(0x0c23af59usize);f(o,w,h);if let Some(i)=index(o){ROWS[i].h=h;if rd(o as *const u32)==0x2c68da78{compact_row(o);}}o}
pub unsafe extern "C" fn obj_set_size_wh(o:u32,w:u32,h:u32)->u32{obj_set_size(o,w as i32,h as i32)}
pub unsafe extern "C" fn obj_align(o:u32,a:u32,x:i32,y:i32)->u32{let f:unsafe extern "C" fn(u32,u32,i32,i32)=transmute(0x0c23afe3usize);f(o,a,x,y);if let Some(i)=index(o){ROWS[i].y=y;}o}
pub unsafe extern "C" fn obj_align_to(o:u32,b:u32,_a:u32,x:i32,gap:i32)->u32 {
    let parent=rd((o+4) as *const u32);
    let gap=if index(o).map(|i|ROWS[i].h==0).unwrap_or(false){0}else{gap};
    let y=if let Some(i)=index(b){if ROWS[i].parent==parent{ROWS[i].y+ROWS[i].h+gap}else{if gap==0{0}else{8}}}else if b==parent{if gap==0{0}else{8}}else{
        // Own labels are measured by LVGL before their following action rows.
        let f:unsafe extern "C" fn(u32)=transmute(0x0c23c881usize);f(b);
        let py=rd((parent+0x16) as *const i16) as i32;
        rd((b+0x1a) as *const i16) as i32-py+1+gap
    };
    obj_align(o,align::TOP_MID,x,y)
}
pub unsafe extern "C" fn obj_set_hidden(o:u32,h:u32)->u32{flags(o,h!=0,1);o}
pub unsafe extern "C" fn obj_add_event(o:u32,cb:u32,filter:u32,ud:u32)->u32{let f:unsafe extern "C" fn(u32,u32,u32,u32)->u32=transmute(0x0c241159usize);f(o,cb|1,filter,ud)}
pub unsafe extern "C" fn event_get_code(e:u32)->u32 {
    if e==0{return 0;}let code=(rd((e+8) as *const u8)&127) as u32;
    let target=rd(e as *const u32);
    if code==29 && ROWS.iter().any(|r|r.check==target&&r.kind==1){30}else{code}
}
pub unsafe fn forget_tree(o:u32){
    if o==0{return;}let mut doomed=[false;256];
    for i in 0..ROWS.len(){let mut p=ROWS[i].obj;for _ in 0..32{if p==o{doomed[i]=true;break;}if let Some(k)=index(p){p=ROWS[k].parent;}else{break;}}}
    for i in 0..ROWS.len(){if doomed[i]{ROWS[i]=EMPTY;}}
    if MSGBOX_INSTANCE==o{MSGBOX_INSTANCE=0;}
}
pub unsafe extern "C" fn obj_delete(o:u32){if o==0{return;}forget_tree(o);let f:unsafe extern "C" fn(u32)=transmute(0x0c242785usize);f(o);}
pub unsafe extern "C" fn label_create(p:u32)->u32{let f:unsafe extern "C" fn(u32)->u32=transmute(0x0c25ebbdusize);let o=f(p);if o!=0 {if FONT==0 {FONT=fw_mfont_create_named(b"MiSans-Regular\0".as_ptr(),22,400);}prop(o,0x57,font_for(22));prop(o,0x55,0xf2f2f2);prop(o,0x21,0);let width:unsafe extern "C" fn(u32,i32)=transmute(0x0c23913busize);width(o,264);flags(o,false,2|0x10);}o}
unsafe fn font_for(sz:u32)->u32{let custom=crate::font_apply::cch_face_for_size(sz);if custom!=0{custom}else if sz==22{if FONT==0{FONT=fw_mfont_create_named(b"MiSans-Regular\0".as_ptr(),22,400);}FONT}else if sz==18{if SMALL_FONT==0{SMALL_FONT=fw_mfont_create_named(b"MiSans-Regular\0".as_ptr(),18,400);}SMALL_FONT}else{
    if let Some(f)=EXTRA_FONTS.iter().find(|f|f.0==sz){return f.1;}
    let Some(i)=EXTRA_FONTS.iter().position(|f|f.0==0)else{return FONT;};
    let face=fw_mfont_create_named(b"MiSans-Regular\0".as_ptr(),sz,400);
    if face!=0{EXTRA_FONTS[i]=(sz,face);}face
}}
pub unsafe extern "C" fn label_set_text(o:u32,s:Cp)->u32{let f:unsafe extern "C" fn(u32,Cp)=transmute(0x0c263e09usize);if o!=0 && !s.is_null(){f(o,s);}o}
pub unsafe extern "C" fn label_attr2(o:u32,_v:u32)->u32{o}
pub unsafe extern "C" fn style_apply(o:u32,_s:u32,_a:u32,_b:u32)->i32{prop(o,0x57,font_for(22));0}
pub unsafe extern "C" fn obj_style_color_a70(o:u32,rgb:u32,_a:u32)->u32{prop(o,0x55,rgb);o}
// Native labels live inside the row's text container; coordinates here are
// relative to that container, never the outer row. Apply after native updates.
pub unsafe fn label_wrap(o:u32){
 let f:unsafe extern "C" fn(u32,u32)=transmute(0x0c2644d9usize);f(o,0);
}
// Conservative line measurement reserves room for the native WRAP layout,
// including long words and manual newlines. CJK uses full-width glyphs.
pub unsafe fn wrapped_height(o:u32,size:i32,width:i32)->i32{
 let p=rd((o+0x24) as *const u32);if !crate::plausible_ptr(p){return size+8;}
 let mut line=0;let mut lines=1;
 for i in 0..4096{if !crate::plausible_ptr(p+i){break;}let c=rd((p+i) as *const u8);if c==0{break;}
  if c==b'\n'{lines+=1;line=0;continue;}
  if c&0xc0==0x80{continue;}
  let w=if c>=128{size}else if c==b' '||b"ilI.,:!".contains(&c){size/3}else if c==b'W'||c==b'M'{size}else{(size*2+2)/3};
  if line+w>width&&line>0{lines+=1;line=0;}line+=w;
 }lines*(size+8)
}
unsafe fn compact_row(o:u32){
 let Some(i)=index(o)else{return;};let r=ROWS[i];if r.h<=0{return;}
 let body=rd((o+0x4c) as *const u32);if body==0{return;}
 let frame=rd((o+0x38) as *const u32);let width=if r.check!=0{208}else{272};
 let main_h=if r.label!=0{wrapped_height(r.label,28,width)}else{0};
 let sub_h=if r.sub!=0{wrapped_height(r.sub,22,width)}else{0};
 let body_h=main_h+if r.sub!=0{6+sub_h}else{0};
 let h=if r.kind==100{r.h.max(body_h+40)}else{r.h.max(body_h+24)};
 ROWS[i].h=h;
 if h!=r.h{let f:unsafe extern "C" fn(u32,i32,i32)=transmute(0x0c23af59usize);f(o,304,h);}
 if frame!=0{for p in 0x10..=0x13{prop(frame,p,0);}obj_set_size(frame,304,h);obj_align(frame,1,0,0);}
 for p in 0x10..=0x13{prop(body,p,0);}
 obj_set_size(body,width,body_h);obj_align(body,1,16,if r.kind==100{8}else{(h-body_h)/2});
 if r.label!=0{prop(r.label,0x57,font_for(28));prop(r.label,0x5b,1);label_wrap(r.label);obj_set_size(r.label,width,main_h);obj_align(r.label,1,0,0);}
 if r.sub!=0{prop(r.sub,0x57,font_for(22));prop(r.sub,0x5b,1);label_wrap(r.sub);obj_set_size(r.sub,width,sub_h);obj_align(r.sub,1,0,main_h+6);}
 if r.check!=0{obj_align(r.check,8,-16,0);}
}
// Native N67 system list item. Its own class owns layout and trailing controls.
pub unsafe extern "C" fn row_create(p:u32,s:Cp,sub:Cp,tr:u32)->u32 {
    let create:unsafe extern "C" fn(u32)->u32=transmute(0x0c2702b5usize);
    let fill:unsafe extern "C" fn(u32,u32,Cp,Cp,i32,u32,u32)->u32=transmute(0x0c275ad5usize);
    let o=create(p);if o==0{return 0;}
    let h=if sub.is_null(){88}else{112};
    let Some(i)=slot(o,p,h)else{obj_delete(o);return 0;};
    obj_set_size(o,304,h);
    // Native fill reads fonts from its PRIMARY/SECONDARY parts.
    let style:unsafe extern "C" fn(u32,u32,u32,u32)=transmute(0x0c242e8busize);
    style(o,0x57,font_for(28),0x90000);style(o,0x57,font_for(22),0xa0000);
    for p in 0x10..=0x13{prop(o,p,0);}wr((o+0x5c) as *mut u16,16);
    fill(o,0,s,sub,0,0,tr);
    ROWS[i].label=rd((o+0x50) as *const u32);ROWS[i].sub=rd((o+0x54) as *const u32);
    ROWS[i].check=rd((o+0x60) as *const u32);ROWS[i].kind=tr;
    // Checkbox rows are handled by Chaos on either target. Do not also let
    // the native row forward the same click to its trailing control.
    if tr==2{wr((o+0x71) as *mut u8,0);flags(ROWS[i].check,false,EVENT_BUBBLE);}
    compact_row(o);flags(o,true,GESTURE);o
}
// Status/information is text, not an action button. Keep an empty handle
// for callers but remove its geometry from the following-row alignment chain.
pub unsafe fn display_row(o:u32,text:Cp,sub:Cp){
    let Some(i)=index(o)else{return;};ROWS[i].display=true;
    let empty=(text.is_null()||rd(text)==0)&&(sub.is_null()||rd(sub)==0);
    flags(o,false,2|8|PRESS_LOCK);
    for off in [0x38,0x4c]{let inner=rd((o+off) as *const u32);if inner!=0{flags(inner,false,2|8|PRESS_LOCK);}}
    if empty{obj_set_hidden(o,1);obj_set_size(o,304,0);}
    else{obj_set_hidden(o,0);if ROWS[i].h==0{obj_set_size(o,304,if ROWS[i].sub==0{88}else{112});}compact_row(o);}
}
pub unsafe extern "C" fn row_trailing(o:u32)->u32{index(o).map(|i|ROWS[i].check).unwrap_or(0)}
pub unsafe fn row_secondary(o:u32)->u32{index(o).map(|i|ROWS[i].sub).unwrap_or(0)}
// N67 native zoom pickers, matching the original P67 month/day interaction.
pub unsafe fn date_picker(parent:u32,min:u32,max:u32,value:u32,x:i32)->u32{
    let create:unsafe extern "C" fn(u32)->u32=transmute(0x0c4349d5usize);
    let range:unsafe extern "C" fn(u32,u32,u32,u32)=transmute(0x0c434a55usize);
    let p=create(parent);if p==0{return 0;}
    let width:unsafe extern "C" fn(u32,i32)=transmute(0x0c23913busize);width(p,132);
    prop(p,0x57,font_for(64));prop(p,0x14,0);
    prop(p,0x55,0xf2f2f2);wr((p+0x2d8) as *mut u16,3);
    range(p,min,max,1);date_picker_index(p,value-min);obj_align(p,9,x-102,-44);p
}
pub unsafe fn date_picker_index(p:u32,index:u32){
    let f:unsafe extern "C" fn(u32,u32)=transmute(0x0c4349f1usize);f(p,index);
}
pub unsafe fn date_picker_value(p:u32,min:u32,max:u32)->Option<u32>{
    if p==0{return None;}
    let get:unsafe extern "C" fn(u32)->u32=transmute(0x0c43ba45usize);
    let text=get(p);if text<0x1c000000||text>=0x40000000{return None;}
    let mut n=0;for i in 0..3{let c=rd((text+i) as *const u8);
        if c==0{return if i>0&&n>=min&&n<=max{Some(n)}else{None};}
        if c<b'0'||c>b'9'{return None;}n=n*10+(c-b'0') as u32;
    }None
}
pub unsafe fn date_caption(parent:u32,text:Cp,x:i32,y:i32,w:i32,size:u32){
    about_label(parent,text,size,0xb3bdcc,x,y,w,32,true);
}
pub unsafe fn confirm_button(parent:u32)->u32{
    let create:unsafe extern "C" fn(u32)->u32=transmute(0x0c43da65usize);
    let o=create(parent);if o==0{return 0;}
    let Some(i)=slot(o,parent,80)else{obj_delete(o);return 0;};
    ROWS[i].label=label_create(o);o
}
pub unsafe fn date_confirm(row:u32){
    let Some(i)=index(row)else{return;};obj_set_size(row,224,88);obj_align(row,1,56,304);
    prop(row,0x20,0x222222);prop(row,0x0b,44);obj_set_hidden(ROWS[i].label,1);
    let im=image_create(row);if im!=0{image_source(im,b"S:/system/image/common/icon/confirm.bin\0".as_ptr() as u32);obj_align(im,9,0,0);flags(im,false,2|0x10);}
}
// About-only presentation. Keep shared rows and every other page's geometry.
unsafe fn about_label(parent:u32,text:Cp,size:u32,color:u32,x:i32,y:i32,w:i32,h:i32,center:bool)->bool{
    let lb=label_create(parent);if lb==0{return false;}
    // LVGL 8 lv_txt.h: AUTO=0, LEFT=1, CENTER=2, RIGHT=3.
    // A boolean cast selects LEFT when true, not CENTER.
    prop(lb,0x57,font_for(size));prop(lb,0x55,color);prop(lb,0x5b,if center{2}else{1});
    obj_set_size(lb,w,h);obj_align(lb,align::TOP_LEFT,x,y);label_set_text(lb,text);true
}
pub unsafe fn about_identity(row:u32,version:Cp)->bool{
    if index(row).is_none(){return false;}
    obj_set_size(row,304,228);prop(row,0x21,0);
    let image=image_create(row);if image==0{return false;}
    image_source(image,b"/data/chaos/chaos_icon.bin\0".as_ptr() as u32);
    obj_set_size(image,100,100);
    obj_align(image,align::TOP_LEFT,102,0);flags(image,false,2|0x10);
    if !about_label(row,b"Chaos\0".as_ptr(),32,0xf4f5f7,0,104,304,40,true){return false;}
    let badge=object(row);if badge==0{return false;}
    obj_set_size(badge,128,28);obj_align(badge,align::TOP_LEFT,88,146);
    prop(badge,0x20,0x15324d);prop(badge,0x0b,14);flags(badge,false,2|0x10);
    if !about_label(badge,version,18,0x8fc7ff,0,2,128,24,true){return false;}
    if !about_label(row,b"9 Pro  /  N67 CN  /  3.1.190\0".as_ptr(),16,0xa5adba,0,179,304,24,true){return false;}
    about_label(row,b"WenHuaYiYang / Chaos-Module\0".as_ptr(),14,0x7d8797,0,205,304,20,true)
}
pub unsafe fn about_action(row:u32)->bool{
    let Some(i)=index(row)else{return false;};
    obj_set_size(row,304,52);prop(row,0x20,0x1d222b);prop(row,0x0b,16);
    let label=ROWS[i].label;
    let body=rd((row+0x4c) as *const u32);obj_set_size(body,248,28);obj_align(body,1,16,12);
    prop(label,0x57,font_for(20));obj_set_size(label,248,28);obj_align(label,align::TOP_LEFT,0,0);
    about_label(row,"›\0".as_ptr(),24,0x7d8797,272,9,16,34,true)
}
pub unsafe extern "C" fn row_update(o:u32,a:Cp,text:Cp,sub:Cp,badge:i32,sel:u8)->i32 {
    let f:unsafe extern "C" fn(u32,Cp,Cp,Cp,i32,u8)->i32=transmute(0x0c276ae5usize);
    let rc=f(o,a,text,sub,badge,sel);
    if text.is_null()&&sub.is_null(){return rc;}
    if index(o).map(|i|ROWS[i].display).unwrap_or(false)&&!text.is_null(){display_row(o,text,sub);}else{compact_row(o);}rc
}
pub unsafe extern "C" fn content_create(root:u32)->u32{flags(root,false,2|0x10);flags(root,true,GESTURE);prop(root,0x32,0);prop(root,0x35,0);prop(root,0x39,0);prop(root,0x20,PAGE_BG);prop(root,0x21,255);for k in 0x10..=0x13{prop(root,k,0);}let o=object(root);if o!=0{prop(o,0x21,0);flags(o,true,0x10|GESTURE);let dir:unsafe extern "C" fn(u32,u32)=transmute(0x0c23ea15usize);dir(o,12);slot(o,root,424);crate::ui_activity::bind(o);}o}
pub unsafe extern "C" fn content_pad_bottom(o:u32,pad:i32,_f:u32)->u32{prop(o,0x11,pad as u32);o}
pub unsafe extern "C" fn page_title_create(root:u32,text:Cp,mode:u32,cb:u32,ud:u32)->u32 {
    let f:unsafe extern "C" fn(u32,Cp,u32,u32,u32)->u32=transmute(0x0c275501usize);
    let o=f(root,text,mode,cb,ud);if o!=0{
        slot(o,root,56);for p in 0x10..=0x13{prop(o,p,0);}obj_set_size(o,336,56);obj_align(o,1,0,0);
        let label=rd((o+0x28) as *const u32);let clock=rd((o+0x30) as *const u32);
        // Native title creation selects SCROLL_CIRC (3). DOT (1) cancels
        // its marquee, including vertical scrolling in a fixed-height label.
        let long_mode:unsafe extern "C" fn(u32,u32)=transmute(0x0c2644d9usize);
        flags(o,false,0x10);
        if label!=0{long_mode(label,1);}if clock!=0{long_mode(clock,1);}
        if label!=0{prop(label,0x57,font_for(28));prop(label,0x5b,1);obj_set_size(label,if mode==0{220}else{180},38);obj_align(label,1,if mode==0{16}else{46},9);}
        if clock!=0{prop(clock,0x57,font_for(18));prop(clock,0x5b,3);obj_set_size(clock,64,26);obj_align(clock,1,256,15);}
    }o
}
// The system title owns its clock widget and refresh lifecycle.
pub unsafe fn header_tick() {}
pub unsafe extern "C" fn page_goto(key:u32,data:u32){let f:unsafe extern "C" fn(u32,u32,u32,u32)->i32=transmute(0x0c44a5c5usize);f(key,data,0,0);}
pub unsafe extern "C" fn page_back(){let f:unsafe extern "C" fn()->i32=transmute(0x0c4490b9usize);f();}
pub struct DataRow{pub row:u32,pub name:u32,pub value:u32,pub bar:u32}
pub unsafe fn data_row_create(p:u32,name:Cp,rgb:u32,pct:u32)->DataRow {
    let o=row_create(p,name,b" \0".as_ptr(),0);
    if o==0{return DataRow{row:0,name:0,value:0,bar:0};}
    let n=index(o).map(|i|ROWS[i].label).unwrap_or(0);let v=row_secondary(o);
    if let Some(i)=index(o){ROWS[i].kind=100;}obj_set_size(o,304,112);
    let create:unsafe extern "C" fn(u32,u32)->u32=transmute(0x0c23ef91usize);
    let init:unsafe extern "C" fn(u32)=transmute(0x0c23e909usize);
    let bar=create(0x2c683310,o);if bar!=0{
        init(bar);obj_set_size(bar,272,12);obj_align(bar,1,16,92);
        let style:unsafe extern "C" fn(u32,u32,u32,u32)=transmute(0x0c242e8busize);
        style(bar,0x20,rgb|0xff000000,0x20000);bar_set_pct(bar,pct);
    }
    DataRow{row:o,name:n,value:v,bar}
}
pub unsafe fn data_row_place(d:&DataRow,b:u32){obj_align_to(d.row,b,14,0,8);}
pub unsafe fn bar_set_pct(bar:u32,pct:u32){
    if bar==0{return;}let f:unsafe extern "C" fn(u32,u32,u32)=transmute(0x0c25bc39usize);f(bar,pct.min(100),0);
}
pub unsafe extern "C" fn open(p:Cp,f:u32,m:u32)->i32{let fun:unsafe extern "C" fn(Cp,u32,u32)->i32=transmute(0x0c37e30dusize);fun(p,f,m)}
pub unsafe extern "C" fn close(fd:i32)->i32{let f:unsafe extern "C" fn(i32)->i32=transmute(0x0c37dba5usize);f(fd)}
pub unsafe extern "C" fn read(fd:i32,p:*mut u8,n:u32)->i32{let f:unsafe extern "C" fn(i32,*mut u8,u32)->i32=transmute(0x0c37f459usize);f(fd,p,n)}
pub unsafe extern "C" fn write(fd:i32,p:Cp,n:u32)->i32{let f:unsafe extern "C" fn(i32,Cp,u32)->i32=transmute(0x0c37f0fdusize);f(fd,p,n)}
pub unsafe extern "C" fn opendir(p:Cp)->u32{let f:unsafe extern "C" fn(Cp)->u32=transmute(0x0c0e4139usize);f(p)}
pub unsafe extern "C" fn readdir(p:u32)->u32{let f:unsafe extern "C" fn(u32)->u32=transmute(0x0c0e4199usize);f(p)}
pub unsafe extern "C" fn closedir(p:u32)->i32{let f:unsafe extern "C" fn(u32)->i32=transmute(0x0c0e4171usize);f(p)}
pub unsafe extern "C" fn fs_remove(p:Cp)->i32{let f:unsafe extern "C" fn(Cp)->i32=transmute(0x0c37fe01usize);let r=f(p);if r==0 {r}else{let dir:unsafe extern "C" fn(Cp)->i32=transmute(0x0c37f775usize);dir(p)}}
pub unsafe extern "C" fn heap_malloc(n:u32)->u32{let f:unsafe extern "C" fn(u32)->u32=transmute(0x0c0f1171usize);f(n)}
pub unsafe extern "C" fn fw_str_dup(p:Cp)->u32 {let mut n=0;while n<160&&rd(p.add(n))!=0{n+=1;}if n==160{return 0;}let o=heap_malloc(n as u32+1);if o!=0{for i in 0..=n{wr((o as *mut u8).add(i),rd(p.add(i)));}}o}
pub unsafe extern "C" fn fw_free(p:u32){let f:unsafe extern "C" fn(u32)=transmute(0x0c0f0791usize);f(p);}
pub unsafe extern "C" fn fw_img_free_by_path(p:u32){let f:unsafe extern "C" fn(u32)=transmute(0x0c241c89usize);f(p);}
pub unsafe extern "C" fn fw_list_head(head:u32)->u32{rd((head+4) as *const u32)}
pub unsafe extern "C" fn fw_list_next(head:u32,node:u32)->u32{rd((node+rd(head as *const u32)+4) as *const u32)}
pub unsafe extern "C" fn launcher_refresh_app(_id:u32){let e=[0x18u32,0,0xe7d4];let f:unsafe extern "C" fn(*const u32)=transmute(0x0c2a4931usize);f(e.as_ptr());}
pub unsafe extern "C" fn fw_mfont_create_named(name:Cp,size:u32,flag:u32)->u32{let f:unsafe extern "C" fn(Cp,u32,u32)->u32=transmute(0x0c2665f1usize);f(name,size,flag)}
pub unsafe extern "C" fn timer_create(cb:u32,p:u32,ud:u32)->u32{let f:unsafe extern "C" fn(u32,u32,u32)->u32=transmute(0x0c25a289usize);f(cb,p,ud)}
pub unsafe extern "C" fn timer_set_period(t:u32,ms:u32){wr(t as *mut u32,ms);}
pub unsafe fn timer_period_of(t:u32)->u32{if t!=0{rd(t as *const u32)}else{0}}
pub unsafe fn screen_is_on()->bool{rd((0x200ca360+0x19) as *const u8)==2}
pub unsafe fn top_app_id()->u32{let f:unsafe extern "C" fn(i32)->u32=transmute(0x0c44a5adusize);let d=f(-1);if crate::safe_ptr(d){rd((d+0x16) as *const u16) as u32}else{0}}
pub unsafe fn watchface_is_on()->u32{
 if top_app_id()!=HOME_APP_ID||!screen_is_on(){return 0;}
 // Native visible-change handler 0xc453a74 stores is_aod at +6c and visible +6d.
 let manager=rd(crate::WF_MGR_PTR as *const u32);
 if !crate::safe_ptr(manager)||!crate::safe_ptr(manager+0x6c){return 0;}
 (rd((manager+0x6c) as *const u8)==0&&rd((manager+0x6d) as *const u8)!=0) as u32
}
pub unsafe extern "C" fn eventbus_subscribe(t:u32,a:u32,cb:u32,ud:u32)->u32{let f:unsafe extern "C" fn(u32,u32,u32,u32)->u32=transmute(0x0c46a00busize);f(t,a,cb|1,ud)}
pub unsafe fn brightness_get_target()->u32{rd((0x200ca360+0x10) as *const u32)}
pub unsafe fn brightness_get_auto_adjustment()->u32{rd((0x200ca360+4) as *const u8) as u32}
pub unsafe fn brightness_set_value(v:u32){brightness_apply_raw(v); }
pub unsafe fn brightness_set_auto_adjustment(v:u32){wr((0x200b5bd0+0x1a5) as *mut u8,(v!=0) as u8);let f:unsafe extern "C" fn(u32)=transmute(0x0c44c421usize);f(0);}
pub unsafe fn brightness_apply_raw(v:u32){let f:unsafe extern "C" fn(u32,u32)=transmute(0x0c44c399usize);f(v.min(600),0);}
pub unsafe fn obj_is_child_of(p:u32,o:u32)->bool{if p==0||o==0{return false;}let spec=rd((p+8) as *const u32);if !crate::safe_ptr(spec){return false;}let arr=rd(spec as *const u32);let n=rd((spec+4) as *const u32);if n>160||!crate::safe_ptr(arr){return false;}for i in 0..n{if rd((arr+i*4) as *const u32)==o{return true;}}false}
pub unsafe extern "C" fn msgbox_create(p:u32,_m:u32)->u32{
    let top:unsafe extern "C" fn(i32)->u32=transmute(0x0c44a5adusize);let page=top(-1);
    if !crate::safe_ptr(page)||rd((page+DESC_ROOT) as *const u32)!=p{return 0;}
    let f:unsafe extern "C" fn(u32,u32)->u32=transmute(0x0c271d6dusize);
    let o=f(p,page);if o!=0{MSGBOX_INSTANCE=o;}o
}
pub unsafe extern "C" fn msgbox_fill(o:u32,k:u32,img:u32,text:Cp,sub:u32,btn:*const u32,n:u32){
    let f:unsafe extern "C" fn(u32,u32,u32,Cp,u32,*const u32,u32)=transmute(0x0c274f61usize);
    f(o,k,img,text,sub,btn,n);
}

// lseek binding already used by the release's C file engine (integration slot 20).
pub mod seek { pub const SET:u32=0; pub const END:u32=2; }
pub unsafe fn lseek(fd:i32,offset:i64,whence:u32)->i64 {
    let f:unsafe extern "C" fn(i32,i64,u32)->i64=transmute(0x0c37e1f5usize);
    f(fd,offset,whence)
}
pub unsafe fn now_tm()->Option<[i32;11]> {
    let get:unsafe extern "C" fn(u32,*mut u64)->i32=transmute(0x0c0bb095usize);
    let local:unsafe extern "C" fn(*const u64,*mut i32)->*mut i32=transmute(0x0c0f12d5usize);
    let mut ts=[0u64;2];let mut tm=[0i32;11];
    if get(0,ts.as_mut_ptr())!=0 || local(ts.as_ptr(),tm.as_mut_ptr()).is_null(){return None;}
    if !(0..60).contains(&tm[0]) || !(0..60).contains(&tm[1]) || !(0..24).contains(&tm[2]) || !(1..32).contains(&tm[3]) || !(0..12).contains(&tm[4]){return None;}
    Some(tm)
}

// N67 call sites 0xc26fa22 and 0xc290018 zero twelve bytes and set byte 0
// to 3 and 1 respectively before calling 0xc45dc68. No P67 effect mapping.
// Persistent aligned storage also survives any deferred firmware consumption.
static mut VIBRATION_REQUEST: [u32;3] = [0;3];
pub unsafe fn uptime_ms()->u32 {
    let f:unsafe extern "C" fn()->u32=transmute(0x0c1610b9usize);f()
}
pub unsafe fn vibration_request(effect:u8)->i32 {
    if effect != 1 && effect != 3 { return -22; }
    if let Some(rc)=crate::gh225::request(effect){return rc;}
    VIBRATION_REQUEST = [effect as u32,0,0];
    let f:unsafe extern "C" fn(*const u32)->i32=transmute(0x0c45dc69usize);
    f(core::ptr::addr_of!(VIBRATION_REQUEST) as *const u32)
}
// 0xc45dc82 returns -5 for global disable; 0xc368f7e returns the same
// value for mode >1. -3 is the busy/priority gate, not a malformed buffer.
pub unsafe fn vibration_failure(rc:i32)->&'static [u8]{
    match rc{
        -5 if rd(0x200cbb6d as *const u8)!=0=>"系统已停用震动，请检查震动设置\0".as_bytes(),
        -5 if rd(0x200cc6bc as *const u8)>1=>"当前系统模式禁止震动\0".as_bytes(),
        -3=>"其他震动正在执行，请稍后重试\0".as_bytes(),
        -2=>"系统不支持此震动效果\0".as_bytes(),
        -4=>"震动参数为空\0".as_bytes(),
        _=>"震动服务返回失败\0".as_bytes(),
    }
}

// NSH date call site 0xc102546 uses this ioctl entry with RTC_RD_TIME=0x1901.
pub unsafe fn ioctl(fd:i32,request:u32,arg:u32)->i32 {
    let f:unsafe extern "C" fn(i32,u32,u32)->i32=transmute(0x0c37e1b5usize);f(fd,request,arg)
}

pub unsafe fn rename(from:Cp,to:Cp)->i32{let f:unsafe extern "C" fn(Cp,Cp)->i32=transmute(0x0c37f491usize);f(from,to)}
pub unsafe fn launcher_remove(id:u32){let f:unsafe extern "C" fn(u32)=transmute(0x0c2a47edusize);f(id)}
// The desktop-only part of app_launcher_del (0xc2a480e..0xc2a481a,
// 0xc2a483a..0xc2a4840). Deliberately skip 0xc2a481e..0xc2a4836:
// that section removes/frees the package from the separate order list at
// 0x200a4034. Caller validates the complete desktop chain before passing rec.
pub unsafe fn launcher_hide_record(rec:u32,order:u32){
    let remove_icon:unsafe extern "C" fn(u32)=transmute(0x0c2a1d21usize);
    let unlink:unsafe extern "C" fn(u32,u32)=transmute(0x0c257ecfusize);
    let free:unsafe extern "C" fn(u32)=transmute(0x0c258499usize);
    let sort:unsafe extern "C" fn()=transmute(0x0c2a46d5usize);
    // bit 1 means present on the desktop. Native insertion searches for the
    // next order record with this bit set; hidden anchors must be skipped.
    if order!=0{let p=(order+0x80) as *mut u8;wr(p,rd(p)&!2);}
    remove_icon(rec);unlink(LAUNCHER_DESKTOP_LIST,rec);free(rec);sort();
}
pub unsafe fn launcher_add(id:u32){let f:unsafe extern "C" fn(u32)=transmute(0x0c2a47a1usize);f(id)}

pub unsafe fn top_page_root()->Option<(u32,u32)>{
    let f:unsafe extern "C" fn(i32)->u32=transmute(0x0c44a5adusize);let d=f(-1);
    if !crate::safe_ptr(d){return None;}let key=rd((d+0x14) as *const u32);let root=rd((d+0x2c) as *const u32);
    if !crate::safe_ptr(root){None}else{Some((key,root))}
}

// get_style_prop confirmed by native BG_COLOR/BG_OPA wrappers 0xc40661c/0xc40662a.
pub unsafe fn style_get(o:u32,prop:u32)->u32{let f:unsafe extern "C" fn(u32,u32,u32)->u32=transmute(0x0c24427dusize);f(o,0,prop)}
// Native snapshot wrapper 0xc43b6f4 calls both entries with this exact ABI.
pub unsafe fn snapshot_needed(o:u32,format:u32)->u32{let f:unsafe extern "C" fn(u32,u32)->u32=transmute(0x0c43479fusize);f(o,format)}
pub unsafe fn snapshot_to_buf(o:u32,format:u32,desc:*const u32,buffer:u32,size:u32)->u32{
    let f:unsafe extern "C" fn(u32,u32,*const u32,u32,u32)->u32=transmute(0x0c43ad91usize);f(o,format,desc,buffer,size)
}

pub unsafe fn image_create(parent:u32)->u32{let f:unsafe extern "C" fn(u32)->u32=transmute(0x0c25eba1usize);f(parent)}
pub unsafe fn image_source(o:u32,source:u32){let f:unsafe extern "C" fn(u32,u32)=transmute(0x0c2617d9usize);f(o,source)}

// Compatibility surface for the 1.0.8 keyboard, using N67 LVGL8 interfaces.
pub const LV_DIR_HOR:u32=3;
pub const LV_OBJ_FLAG_CLICKABLE:u32=2;
pub const LV_OBJ_FLAG_SCROLLABLE:u32=16;
pub const LV_OBJ_FLAG_SCROLL_ELASTIC:u32=32;
pub const LV_OBJ_FLAG_SCROLL_CHAIN:u32=256|512;
pub const LV_OBJ_FLAG_GESTURE_BUBBLE:u32=65536;
pub unsafe fn obj_create(parent:u32,_copy:u32)->u32{object(parent)}
pub unsafe fn obj_clear_box_spacing(o:u32){for p in 0x10..=0x13{prop(o,p,0);}}
pub unsafe fn obj_clear_scrollable(o:u32){flags(o,false,16);}
pub unsafe fn obj_add_flag(o:u32,f:u32){flags(o,true,f);}
pub unsafe fn obj_clear_flag(o:u32,f:u32){flags(o,false,f);}
pub unsafe fn obj_style_color(o:u32,color:u32,_selector:u32){prop(o,0x20,color);}
pub unsafe fn obj_set_scroll_dir(o:u32,d:u32){let f:unsafe extern "C" fn(u32,u32)=transmute(0x0c23ea15usize);f(o,d);}
// The integrated N67 file engine bt_app_event independently reads e[3].
pub unsafe fn event_user_data(e:u32)->u32{if e==0{0}else{rd((e+12) as *const u32)}}
// Native About layout calls 0xc23c8b8 directly with OUT_BOTTOM_LEFT=13.
pub unsafe fn native_align_to(o:u32,base:u32,a:u32,x:i32,y:i32){let f:unsafe extern "C" fn(u32,u32,u32,i32,i32)=transmute(0x0c23c8b9usize);f(o,base,a,x,y);}

pub unsafe fn native_button(parent:u32)->u32{let f:unsafe extern "C" fn(u32)->u32=transmute(0x0c43da65usize);f(parent)}

// Do not pass the system Settings entry through Chaos compact_row: let the
// N67 class/theme own fonts, insets, icon and arrow; match a stock sibling.
// Reorder only validated direct children on the GUI thread. Keep native row
// identities/events intact; re-anchor following rows for non-flex lists too.
unsafe fn settings_siblings(row:u32)->Option<(u32,u32,u32,u32)>{
    if !crate::safe_ptr(row){return None;}let parent=rd((row+4) as *const u32);
    if !crate::safe_ptr(parent){return None;}let spec=rd((parent+8) as *const u32);
    if !crate::safe_ptr(spec){return None;}let arr=rd(spec as *const u32);let n=rd((spec+4) as *const u32);
    if n>160||!crate::safe_ptr(arr){return None;}
    for i in 0..n{let child=rd((arr+i*4) as *const u32);if !crate::safe_ptr(child)||rd((child+4) as *const u32)!=parent{return None;}}
    let i=(0..n).find(|&i|rd((arr+i*4) as *const u32)==row)?;Some((parent,arr,n,i))
}
unsafe fn settings_follow(arr:u32,n:u32,start:u32,mut anchor:u32,mut original_bottom:i32,first_gap:i32){
    let mut first=true;
    for i in start..n{let o=rd((arr+i*4) as *const u32);if rd(o as *const u32)!=0x2c68da78{continue;}
        let top=rd((o+0x16) as *const i16) as i32;let bottom=rd((o+0x1a) as *const i16) as i32;
        let gap=if first{first_gap}else{(top-original_bottom-1).clamp(0,32)};
        native_align_to(o,anchor,14,0,gap);anchor=o;original_bottom=bottom;first=false;
    }
}
pub unsafe fn system_settings_insert(row:u32,target:u32){
    let Some((parent,arr,n,from))=settings_siblings(row)else{return;};
    let Some(to)=(0..from).find(|&i|rd((arr+i*4) as *const u32)==target)else{return;};
    let top=rd((target+0x16) as *const i16) as i32;let bottom=rd((target+0x1a) as *const i16) as i32;
    let mut previous=0;for i in 0..to{let o=rd((arr+i*4) as *const u32);if rd(o as *const u32)==0x2c68da78{previous=o;}}
    let gap=if previous!=0{(top-rd((previous+0x1a) as *const i16) as i32-1).clamp(0,32)}else{8};
    for i in (to..from).rev(){let value=rd((arr+i*4) as *const u32);wr((arr+(i+1)*4) as *mut u32,value);}
    wr((arr+to*4) as *mut u32,row);
    if previous!=0{native_align_to(row,previous,14,0,gap);}else{native_align_to(row,target,1,0,0);}
    settings_follow(arr,n,to+1,row,bottom,gap);
    let invalidate:unsafe extern "C" fn(u32)=transmute(0x0c23b38busize);invalidate(parent);
}
pub unsafe fn system_settings_remove(row:u32){
    if let Some((_parent,arr,n,index))=settings_siblings(row){
        let mut previous=0;for i in 0..index{let o=rd((arr+i*4) as *const u32);if rd(o as *const u32)==0x2c68da78{previous=o;}}
        if let Some(next)=(index+1..n).map(|i|(i,rd((arr+i*4) as *const u32))).find(|&(_,o)|rd(o as *const u32)==0x2c68da78){
            let bottom=rd((next.1+0x1a) as *const i16) as i32;
            let gap=(rd((next.1+0x16) as *const i16) as i32-rd((row+0x1a) as *const i16) as i32-1).clamp(0,32);
            if previous!=0{native_align_to(next.1,previous,14,0,gap);}else{native_align_to(next.1,row,1,0,0);}
            settings_follow(arr,n,next.0+1,next.1,bottom,gap);
        }
    }
    obj_delete(row);
}
pub unsafe fn system_settings_row(parent:u32,last:u32,previous:u32)->u32{
    let create:unsafe extern "C" fn(u32)->u32=transmute(0x0c2702b5usize);
    let fill:unsafe extern "C" fn(u32,u32,Cp,Cp,i32,u32,u32)->u32=transmute(0x0c275ad5usize);
    let o=create(parent);if o==0{return 0;}
    fill(o,b"/data/chaos/chaos_settings_icon.bin\0".as_ptr() as u32,b"Chaos\0".as_ptr(),NONE_PTR,0,0,trailing::NONE);
    let update:unsafe extern "C" fn(u32)=transmute(0x0c23c881usize);update(parent);
    let mut gap=8;
    if last!=parent&&crate::safe_ptr(last){
        let width=rd((last+0x18) as *const i16) as i32-rd((last+0x14) as *const i16) as i32+1;
        let height=rd((last+0x1a) as *const i16) as i32-rd((last+0x16) as *const i16) as i32+1;
        if width>=160&&width<=336&&height>=40&&height<=160{obj_set_size(o,width,height);}
        if crate::safe_ptr(previous){
            let g=rd((last+0x16) as *const i16) as i32-rd((previous+0x1a) as *const i16) as i32-1;
            if g>=0&&g<=32{gap=g;}
        }
        native_align_to(o,last,align::OUT_BOTTOM_MID,0,gap);
    }else{obj_align(o,align::TOP_MID,0,8);}
    update(o);
    // Match measured native sibling children, including the real label font.
    // Align against the outer row so native content padding is not added twice.
    let row_width=rd((o+0x18) as *const i16) as i32-rd((o+0x14) as *const i16) as i32+1;
    for (offset,fallback_x,fallback_w,fallback_h) in [(0x48,16,64,64),(0x4c,96,192,48)]{
        let child=rd((o+offset) as *const u32);if !crate::safe_ptr(child){continue;}
        let(mut x,mut y,mut width,mut height)=(fallback_x,0,fallback_w,fallback_h);
        for reference in [last,previous]{
            if !crate::safe_ptr(reference)||reference==parent{continue;}
            let source=rd((reference+offset) as *const u32);if !crate::safe_ptr(source){continue;}
            let left=rd((source+0x14) as *const i16) as i32;
            let top=rd((source+0x16) as *const i16) as i32;
            let right=rd((source+0x18) as *const i16) as i32;
            let bottom=rd((source+0x1a) as *const i16) as i32;
            let sx=left-rd((reference+0x14) as *const i16) as i32;
            let sw=right-left+1;let sh=bottom-top+1;
            let sy=(top+bottom-rd((reference+0x16) as *const i16) as i32-rd((reference+0x1a) as *const i16) as i32)/2;
            if sx<0||sw<16||sh<16||sx+sw>row_width||sh>160{continue;}
            if offset==0x48&&(sw>96||sh>96){continue;}
            x=sx;y=sy;width=sw;height=sh;break;
        }
        flags(child,true,1<<15);obj_set_size(child,width,height);
        if offset==0x48&&rd(child as *const u32)==0x2c69c2e4{
            let resize:unsafe extern "C" fn(u32,i32,i32)=transmute(0x0c44840fusize);resize(child,width,height);
        }
        native_align_to(child,o,7,x,y);
    }
    let label=rd((o+0x50) as *const u32);
    if crate::safe_ptr(label){for reference in [last,previous]{
        if !crate::safe_ptr(reference)||reference==parent{continue;}
        let source=rd((reference+0x50) as *const u32);
        if !crate::safe_ptr(source)||rd(source as *const u32)!=0x2c6834b0{continue;}
        let font=style_get(source,0x57);
        if crate::plausible_ptr(font){prop(label,0x57,font);break;}
    }}
    flags(o,true,GESTURE);o
}

pub unsafe fn grid_relayout(o:u32){
 let f:unsafe extern "C" fn(u32,i32,i32)=transmute(0x0c4fb975usize);f(o,0,0);
}

pub unsafe fn text_font(size:u32)->u32{font_for(size)}

pub unsafe fn descendant(root:u32,mut o:u32)->bool{
 for _ in 0..32{if !crate::safe_ptr(o){return false;}if root==o{return true;}o=rd((o+4) as *const u32);}false
}
