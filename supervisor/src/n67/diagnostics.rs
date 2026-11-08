//! Architecture-specific counterpart of the P67 hidden debug view.
use crate::*;
use core::sync::atomic::{AtomicU32,Ordering};
extern "C"{static __n67_image_start:u8;static __n67_image_end:u8;}
pub static mut DEBUG:bool=false;
static mut CLICKS:u32=0;
static mut ARMED:bool=false;
static ACTION:AtomicU32=AtomicU32::new(0);
static mut STATUS:&'static [u8]=b"\0";
static mut DESCRIPTORS:u32=0;
static mut FD:i32=-1;
static mut OFFSET:usize=0;
static mut IMAGES:[[u32;3];4]=[[0;3];4];
const TEMP:&[u8]=b"/data/chaos/n67-diagnostic.tmp\0";
const DEST:&[u8]=b"/data/chaos/n67-diagnostic.bin\0";
pub unsafe fn bind(base:u32){DESCRIPTORS=base;}
pub unsafe fn enter(pid:usize){if pid==0{DEBUG=false;CLICKS=0;ARMED=false;}}
pub unsafe fn click(i:usize){
    if !DEBUG{if i==0{CLICKS+=1;if CLICKS>=5{DEBUG=true;CLICKS=0;ARMED=false;render_req(17);}}}
    else if i==0{render_req(17);}
    else if i==1{ACTION.store(1,Ordering::Relaxed);}
}
unsafe fn images()->bool{
    for index in 0..4{
        if IMAGES[index][2]!=0{continue;}
        let data=fw_api::heap_malloc(96*96*4);if data==0{return false;}
        for y in 0..96i32{for x in 0..96i32{
            let dx=x-48;let dy=y-48;let d=dx*dx+dy*dy;
            let ring=d>=36*36&&d<=43*43;
            let blue=match index{0=>dx>=0&&dy<=0,1=>!(dx<0&&dy<0),2=>true,_=>false};
            let rgb=if blue{[0xfe,0x81,0x53]}else{[0x55,0x55,0x55]};
            let at=data as *mut u8;let p=((y*96+x)*4) as usize;
            for c in 0..3{*at.add(p+c)=rgb[c];}*at.add(p+3)=if ring{255}else{0};
        }}
        IMAGES[index]=[5+96*1024+96*2097152,96*96*4,data];
    }true
}
pub unsafe fn render(c:&PageCtx)->PageResult{
    let anchor=build_rows(c,c.title,&[
        (0,RowSpec::clickable("重绘对比图\0".as_bytes())),
        (1,RowSpec::clickable("导出 N67 诊断\0".as_bytes())),
    ])?;
    if !images(){return Err(PageError::ContentFailed);}
    let captions=[b"A 25%\0".as_slice(),b"B 75%\0",b"C 100%\0",b"D 0%\0"];
    for i in 0..4{
        let image=fw_api::image_create(c.content);if image==0{return Err(PageError::ContentFailed);}
        fw_api::image_source(image,IMAGES[i].as_ptr() as u32);
        fw_api::obj_align(image,1,24+(i as i32%2)*160,320+(i as i32/2)*150);
        let label=fw_api::label_create(c.content);if label==0{return Err(PageError::ContentFailed);}
        fw_api::obj_set_size(label,130,32);fw_api::obj_align(label,1,24+(i as i32%2)*160,416+(i as i32/2)*150);
        fw_api::label_set_text(label,captions[i].as_ptr());
    }
    let _=anchor;Ok(())
}
unsafe fn write_all(p:*const u8,n:usize)->bool{
    let mut at=0;
    while at<n{let k=fw_api::write(FD,p.add(at),(n-at) as u32);if k<=0||k as usize>n-at{return false;}at+=k as usize;}true
}
unsafe fn finish(ok:bool){
    if FD>=0{let _=fw_api::close(FD);FD=-1;}
    let committed=ok&&fw_api::rename(TEMP.as_ptr(),DEST.as_ptr())==0;
    STATUS=if committed{"诊断已导出\0".as_bytes()}else{"诊断导出失败\0".as_bytes()};
    crate::notifications::request(STATUS);
    if FG_PAGE==17{render_req(17);}
}
unsafe fn message(text:&'static [u8]){STATUS=text;crate::notifications::request(text);}
pub unsafe fn tick(){
    if ACTION.swap(0,Ordering::Relaxed)!=0&&FD<0{
        if !ARMED{ARMED=true;message("再点一次确认导出\0".as_bytes());render_req(17);}
        else{
            ARMED=false;
            if DESCRIPTORS==0{message("模块尚未初始化\0".as_bytes());return;}
            FD=fw_api::open(TEMP.as_ptr(),2|4|8,0o640);
            if FD<0{message("无法创建诊断文件\0".as_bytes());render_req(17);return;}
            let start=core::ptr::addr_of!(__n67_image_start) as u32;
            let end=core::ptr::addr_of!(__n67_image_end) as u32;
            let header=[0x4744494eu32,1,start,end-start,DESCRIPTORS,8192,0x000301be,0];
            if !write_all(header.as_ptr() as *const u8,32){finish(false);return;}
            OFFSET=0;message("正在导出诊断\0".as_bytes());render_req(17);
        }
    }
    if FD<0{return;}
    let start=core::ptr::addr_of!(__n67_image_start) as usize;
    let length=core::ptr::addr_of!(__n67_image_end) as usize-start;
    let total=length+8192;
    let(amount,p)=if OFFSET<length{((length-OFFSET).min(8192),(start+OFFSET) as *const u8)}
        else{((total-OFFSET).min(8192),(DESCRIPTORS as usize+OFFSET-length) as *const u8)};
    if !write_all(p,amount){finish(false);return;}OFFSET+=amount;
    if OFFSET==total{finish(true);}
}
