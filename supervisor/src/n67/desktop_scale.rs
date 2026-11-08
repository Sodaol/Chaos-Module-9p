//! N67 3.1.190 native grid tables. Math from Chaos 10 Pro 1.0.8, AGPL-3.0.
use crate::fw_api;
use crate::mem::{rd32, safe_ptr};
use crate::{st_rd, st_wr};

const GRID_CLASS:u32=0x2c69e840;
const SELF_OFF: u32 = 4;
const MODE_OFF: u32 = 0x880;
const MODE_A: u32 = 0x0000_0001;
const MODE_B: u32 = 0x0001_0001;
const K0_A: usize = 0x0c;
const K0_B: usize = 0x4b;
const SCROLL_OFF: u32 = 0x88a;
const ROWS: usize = 7;
const COLS: usize = 3;
const OFF_X: u32 = 0;
const OFF_Y: u32 = 0x0A8;
const OFF_S: u32 = 0x150;
const STEP: f32 = 73.0;

const X_COL: [f32; 3] = [60.0, 168.0, 276.0];
const X_INSET: f32 = 10.0;

const RW6_Y_OUT: [f32; 7] = [-237.0, -193.0, -105.0, 0.0, 105.0, 193.0, 232.0];
const RW6_Y_MID: [f32; 7] = [-237.0, -198.0, -105.0, 0.0, 105.0, 198.0, 237.0];
const RW6_S_OUT: [f32; 7] = [0.0, 170.667, 256.667, 256.667, 256.667, 170.667, 0.0];
const RW6_S_MID: [f32; 7] = [0.0, 202.667, 256.667, 256.667, 256.667, 202.667, 0.0];

const Y_CENTER: f32 = 240.0;

static mut LENS_SW: u32 = 0;
static mut PITCH_SW: u32 = 0;
static mut INSET_SW: u32 = 0;
const CFG: &[u8] = b"/data/chaos/applist.cfg\0";
static mut CFG_LOADED: u32 = 0;
static mut CFG_DIRTY: u32 = 0;
static mut LAW_SIG: u32 = 0;
static mut LAW_CONT: u32 = 0;
static mut LAW_LOGGED: u32 = 0;
static mut SCROLL_PREV: i32 = 0;

unsafe fn ensure_loaded() {
    if st_rd!(CFG_LOADED) != 0 {
        return;
    }
    st_wr!(CFG_LOADED, 1);
    let fd = fw_api::open(CFG.as_ptr(), fw_api::oflag::RDONLY, 0);
    if fd < 0 {
        return;
    }
    let mut v = 0u8;
    let n = fw_api::read(fd, &mut v as *mut u8, 1);
    fw_api::close(fd);
    if n == 1 && v <= 0b111 {
        SAVED=v;
        st_wr!(LENS_SW, (v & 1) as u32);
        st_wr!(PITCH_SW, ((v >> 1) & 1) as u32);
        st_wr!(INSET_SW, ((v >> 2) & 1) as u32);
        crate::log::kv("ds cfg", v as u32);
    }
}

unsafe fn save_deferred(){
 if CFG_DIRTY==0{return;}CFG_DIRTY=0;
 let v=(LENS_SW|(PITCH_SW<<1)|(INSET_SW<<2)) as u8;
 let fd=fw_api::open(b"/data/chaos/applist.tmp\0".as_ptr(),2|4|8,0o640);
 let ok=if fd<0{false}else{let n=fw_api::write(fd,&v,1);let close=fw_api::close(fd);n==1&&close==0&&fw_api::rename(b"/data/chaos/applist.tmp\0".as_ptr(),CFG.as_ptr())==0};
 if ok{SAVED=v;}else if crate::honeycomb::enabled(){CFG_DIRTY=1;return;}else{LENS_SW=(SAVED&1) as u32;PITCH_SW=((SAVED>>1)&1) as u32;INSET_SW=((SAVED>>2)&1) as u32;crate::notifications::request("桌面设置保存失败\0".as_bytes());}
 crate::render_req(28);
}
pub(crate) unsafe fn lens_on() -> bool {
    ensure_loaded();
    st_rd!(LENS_SW) != 0
}

pub(crate) unsafe fn set_lens(on: bool) {
    if on { crate::honeycomb::set_enabled(false); }
    ensure_loaded();
    let v = if on { 1 } else { 0 };
    if st_rd!(LENS_SW) == v {
        return;
    }
    st_wr!(LENS_SW, v);
    st_wr!(CFG_DIRTY, 1);
}

pub(crate) unsafe fn pitch_on() -> bool {
    ensure_loaded();
    st_rd!(PITCH_SW) != 0
}

pub(crate) unsafe fn set_pitch(on: bool) {
    if on { crate::honeycomb::set_enabled(false); }
    ensure_loaded();
    let v = if on { 1 } else { 0 };
    if st_rd!(PITCH_SW) == v {
        return;
    }
    st_wr!(PITCH_SW, v);
    st_wr!(CFG_DIRTY, 1);
}

pub(crate) unsafe fn inset_on() -> bool {
    ensure_loaded();
    st_rd!(INSET_SW) != 0
}

pub(crate) unsafe fn set_inset(on: bool) {
    if on { crate::honeycomb::set_enabled(false); }
    ensure_loaded();
    let v = if on { 1 } else { 0 };
    if st_rd!(INSET_SW) == v {
        return;
    }
    st_wr!(INSET_SW, v);
    st_wr!(CFG_DIRTY, 1);
}

pub(crate) unsafe fn scrolling() -> bool {
    if LENS_SW|PITCH_SW|INSET_SW==0&&CAPTURED==0{return false;}
    if crate::ui_activity::scrolling(){return true;}
    let cont = current_grid();
    if cont == 0 || !safe_ptr(cont) {
        return false;
    }
    let now = core::ptr::read_volatile((cont + SCROLL_OFF) as *const i16) as i32;
    let moved = st_rd!(SCROLL_PREV) != now;
    st_wr!(SCROLL_PREV, now);
    moved
}

unsafe fn put(item: u32, a: f32, b: f32) {
    core::ptr::write_volatile(item as *mut f32, a);
    core::ptr::write_volatile((item + 4) as *mut f32, b);
}

unsafe fn knots(k0:usize,out: &mut [f32; 7], mid: &mut [f32; 7]) {
    if st_rd!(PITCH_SW) != 0 {
        let mut i = 0;
        while i < ROWS {
            out[i] = RW6_Y_OUT[i] * (96.0/112.0) + Y_CENTER;
            mid[i] = RW6_Y_MID[i] * (96.0/112.0) + Y_CENTER;
            i += 1;
        }
    } else {
        let mut i = 0;
        while i < ROWS {
            let bank=if k0==K0_A{0}else{1};
            let j=i*6;
            out[i]=f32::from_bits(ORIGINAL[bank][1][j])*(i as f32*STEP)+f32::from_bits(ORIGINAL[bank][1][j+1]);
            mid[i]=f32::from_bits(ORIGINAL[bank][1][j+2])*(i as f32*STEP)+f32::from_bits(ORIGINAL[bank][1][j+3]);
            i += 1;
        }
    }
}

fn seg(ys: &[f32; 7], q: usize) -> (f32, f32) {
    let y0 = ys[q];
    let y1 = if q + 1 < ROWS {
        ys[q + 1]
    } else {
        y0 + (y0 - ys[q - 1])
    };
    let a = (y1 - y0) / STEP;
    (a, y0 - a * (q as f32 * STEP))
}

unsafe fn x_knots(col: usize, out: &mut [f32; 7]) {
    let base = X_COL[col];
    let inward = if col == 0 {
        base + X_INSET
    } else if col == COLS - 1 {
        base - X_INSET
    } else {
        base
    };
    let inset = st_rd!(INSET_SW) != 0;
    let mut i = 0;
    while i < ROWS {
        let zoom_row = i <= 1 || i >= ROWS - 2;
        out[i] = if inset && zoom_row { inward } else { base };
        i += 1;
    }
}

fn s_seg(ys: &[f32; 7], ss: &[f32; 7], q: usize) -> (f32, f32) {
    let s0 = ss[q];
    if q + 1 >= ROWS {
        return (0.0, s0);
    }
    let dy = ys[q + 1] - ys[q];
    let a = if dy == 0.0 { 0.0 } else { (ss[q + 1] - s0) / dy };
    (a, s0 - a * ys[q])
}

fn k0_of(mode: u32) -> usize {
    if mode == MODE_A {
        K0_A
    } else if mode == MODE_B {
        K0_B
    } else {
        0
    }
}

unsafe fn law_write(me: u32, k0: usize) {
    let mut y_out = [0.0f32; 7];
    let mut y_mid = [0.0f32; 7];
    knots(k0,&mut y_out, &mut y_mid);
    let rw6_pitch = st_rd!(PITCH_SW) != 0;
    let rw6_lens = st_rd!(LENS_SW) != 0;
    let rw6_inset = st_rd!(INSET_SW) != 0;
    let mut j = 0usize;
    while j < ROWS * COLS {
        let q = j / COLS;
        let col = j % COLS;
        let item = me + SELF_OFF + ((k0 + j) as u32) * 8;
        let ys: &[f32; 7] = if col == 1 { &y_mid } else { &y_out };
        if rw6_inset {
            let mut xs = [0.0f32; 7];
            x_knots(col, &mut xs);
            let (a, b) = seg(&xs, q);
            put(item + OFF_X, a, b);
        } else {
            original_pair(item + OFF_X, k0, j, 0);
        }
        if rw6_pitch {
            let (a, b) = seg(ys, q);
            put(item + OFF_Y, a, b);
        } else {
            original_pair(item + OFF_Y, k0, j, 1);
        }
        if rw6_lens {
            let ss: &[f32; 7] = if col == 1 { &RW6_S_MID } else { &RW6_S_OUT };
            let (a, b) = s_seg(ys, ss, q);
            put(item + OFF_S, a, b);
        } else {
            original_pair(item + OFF_S, k0, j, 2);
        }
        j += 1;
    }
}

unsafe fn law_matches(me:u32,k0:usize)->bool{
 let bank=if k0==K0_A{0}else{1};
 for axis in 0..3{for j in 0..42{
  let p=me+SELF_OFF+k0 as u32*8+axis as u32*0xa8+j as u32*4;
  if core::ptr::read_volatile(p as *const u32)!=APPLIED[bank][axis][j]{return false;}
 }}true
}
pub(crate) unsafe fn tick() {
    ensure_loaded();
    save_deferred();
    if LENS_SW|PITCH_SW|INSET_SW==0&&CAPTURED==0{return;}
    if crate::ui_activity::scrolling(){return;}

    let cont = current_grid();
    if cont == 0 || !safe_ptr(cont) {
        st_wr!(LAW_SIG, 0);
        st_wr!(LAW_CONT, 0);
        return;
    }
    let me = cont;
    if !safe_ptr(me) {
        return;
    }
    capture(me);
    if CAPTURED!=me{return;}
    let mode = rd32((me + MODE_OFF) as *const u32);
    let k0 = k0_of(mode);
    if k0 == 0 {
        st_wr!(LAW_SIG, 0);
        return;
    }
    let sig = 1 + (st_rd!(LENS_SW) & 1) + ((st_rd!(PITCH_SW) & 1) << 1)
        + ((st_rd!(INSET_SW) & 1) << 2);
    let changed = st_rd!(LAW_SIG) != sig || st_rd!(LAW_CONT) != cont;
    CHECK_TICKS=CHECK_TICKS.wrapping_add(1);
    if !changed&&CHECK_TICKS%20!=0{return;}
    if changed || !law_matches(me, k0) {
        law_write(me, k0);
        remember_applied(me,k0);
        crate::fw_api::grid_relayout(me);
        st_wr!(LAW_SIG, sig);
        st_wr!(LAW_CONT, cont);
        if st_rd!(LAW_LOGGED) == 0 {
            st_wr!(LAW_LOGGED, 1);
            crate::log::kv("law ", (ROWS * COLS) as u32);
            crate::log::kv("law c", cont);
            crate::log::kv("law m", mode);
        }
    }
}

static mut SAVED:u8=0;
static mut CAPTURED:u32=0;
static mut CHECK_TICKS:u32=0;
static mut ORIGINAL:[[[u32;42];3];2]=[[[0;42];3];2];
static mut APPLIED:[[[u32;42];3];2]=[[[0;42];3];2];
unsafe fn find(o:u32,depth:u32,budget:&mut u32)->u32{
 if depth>14||*budget==0||!safe_ptr(o){return 0;}*budget-=1;
 if rd32(o as *const u32)==GRID_CLASS&&safe_ptr(o+0x894){return o;}
 let sp=rd32((o+8) as *const u32);if !safe_ptr(sp){return 0;}
 let arr=rd32(sp as *const u32);let n=rd32((sp+4) as *const u32);
 if n>160||n>0&&!safe_ptr(arr){return 0;}
 for i in 0..n{let ch=rd32((arr+4*i) as *const u32);
  if safe_ptr(ch)&&rd32((ch+4) as *const u32)==o{let found=find(ch,depth+1,budget);if found!=0{return found;}}
 }0
}
unsafe fn current_grid()->u32{
 if !fw_api::screen_is_on(){return 0;}
 let Some((key,root))=fw_api::top_page_root()else{return 0;};
 if key>>16!=fw_api::HOME_APP_ID{return 0;}
 if CAPTURED!=0&&safe_ptr(CAPTURED)&&rd32(CAPTURED as *const u32)==GRID_CLASS&&fw_api::descendant(root,CAPTURED){return CAPTURED;}
 find(root,0,&mut 384)
}
unsafe extern "C" fn deleted(e:u32){
 if !safe_ptr(e){return;}
 if core::ptr::read_volatile((e+8) as *const u8)&127==35&&rd32((e+4) as *const u32)==CAPTURED{
  CAPTURED=0;LAW_CONT=0;LAW_SIG=0;
 }
}
unsafe fn capture(me:u32){
 if CAPTURED==me{return;}
 if CAPTURED!=0&&safe_ptr(CAPTURED)&&rd32(CAPTURED as *const u32)==GRID_CLASS{
  for (bank,k0) in [K0_A,K0_B].iter().enumerate(){for axis in 0..3{for j in 0..42{
   let p=CAPTURED+SELF_OFF+*k0 as u32*8+axis as u32*0xa8+j as u32*4;
   if rd32(p as *const u32)==APPLIED[bank][axis][j]{core::ptr::write_volatile(p as *mut u32,ORIGINAL[bank][axis][j]);}
  }}}
 }
 LAW_SIG=0;
 for (bank,k0) in [K0_A,K0_B].iter().enumerate(){for axis in 0..3{for j in 0..42{
  let p=me+SELF_OFF+*k0 as u32*8+axis as u32*0xa8+j as u32*4;
  ORIGINAL[bank][axis][j]=rd32(p as *const u32);
 }}}
 if fw_api::obj_add_event(me,deleted as *const () as u32,35,0)!=0{CAPTURED=me;}
}
unsafe fn original_pair(item:u32,k0:usize,j:usize,axis:usize){
 let bank=if k0==K0_A{0}else{1};
 core::ptr::write_volatile(item as *mut u32,ORIGINAL[bank][axis][j*2]);
 core::ptr::write_volatile((item+4) as *mut u32,ORIGINAL[bank][axis][j*2+1]);
}
unsafe fn remember_applied(me:u32,k0:usize){
 let bank=if k0==K0_A{0}else{1};
 for axis in 0..3{for j in 0..42{APPLIED[bank][axis][j]=rd32((me+SELF_OFF+k0 as u32*8+axis as u32*0xa8+j as u32*4) as *const u32);}}
}
pub struct AppListPage;
impl crate::page::Page for AppListPage{
 fn fill_title(&self,p:*mut u8){unsafe{crate::put_str(p,"应用列表设置\0".as_bytes());}}
 fn render(&self,c:&crate::page::PageCtx)->crate::page::PageResult{unsafe{
  let mut prev=c.title;
  for (i,name,on) in [(0,"缩放同 RW6\0",lens_on()),(1,"排距同 RW6\0",pitch_on()),(2,"外列内缩\0",inset_on()),(3,"蜂窝视图\0",crate::honeycomb::enabled())]{
   prev=crate::page::build_row(c,prev,i,&crate::page::RowSpec::switch(name.as_bytes()));
   if prev==0{return Err(crate::page::PageError::RowFailed(i));}
   fw_api::row_update(prev,fw_api::NONE_PTR,fw_api::NONE_PTR,fw_api::NONE_PTR,0,on as u8);
  }Ok(())
 }}
 fn on_click(&self,_:usize){}
 fn is_switch_row(&self,i:usize)->bool{i<4}
 fn on_switch(&self,i:usize){unsafe{match i{0=>set_lens(!lens_on()),1=>set_pitch(!pitch_on()),2=>set_inset(!inset_on()),3=>{
  let on=!crate::honeycomb::enabled();
  if on { set_lens(false); set_pitch(false); set_inset(false); }
  crate::honeycomb::set_enabled(on);
 },_=>{}}crate::render_req(28);}}
}
pub static PAGE:AppListPage=AppListPage;
