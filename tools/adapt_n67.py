"""One-time source migration, deliberately idempotent replacements."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]/'supervisor/src'
def edit(name,replacements):
 p=R/name;s=p.read_text('utf-8')
 for a,b in replacements:s=s.replace(a,b)
 p.write_text(s,'utf-8')
values={'FW_FILE_OPEN':0xc380399,'FW_FILE_CLOSE':0xc37ebd1,'FW_FILE_READ':0xc37f457,
 'WF_MGR_PTR':0x200caea8,'FW_SET_WATCHFACE':0xc44fafd,'FW_REFRESH_CUR_WF':0xc306441,
 'WF_ENGINE_CUR':0x200ce848,'FW_OPENDIR':0xc0e4139,'FW_READDIR':0xc0e4199,
 'FW_CLOSEDIR':0xc0e4171,'FW_ERRNO_LOCATION':0xc0e4121,'FW_FONT_DEFAULT':0x2c684eec,
 'FW_STYLE_MISANS_REG_24':0,'FW_STYLE_HR_NAME':0,'FW_STYLE_HR_VALUE':0}
import re
p=R/'state.rs';s=p.read_text('utf-8')
for name,value in values.items():
 pat=rf'(pub const {name}: u32 = )([^;]+)(;)'
 m=re.search(pat,s)
 if f'#[cfg(not(feature = "n67"))]\n{m.group(0)}' not in s:
  s=re.sub(pat,lambda m:f'#[cfg(feature = "n67")]\npub const {name}: u32 = 0x{value:08X};\n#[cfg(not(feature = "n67"))]\n'+m.group(0),s,count=1)
p.write_text(s,'utf-8')
edit('ui.rs',[
 ('PAGES[pid].root = _p1;','PAGES[pid].root = if cfg!(feature="n67") { let r=rd32((_page+fw_api::DESC_ROOT) as *const u32); if safe_ptr(r){r}else{_p1} } else {_p1};'),
 ('dsc + 0x30','dsc + fw_api::DESC_ROOT'),
 ('st_wr!(FG_PAGE, pid as u32);\n    shake_arm();','st_wr!(FG_PAGE, pid as u32);\n    st_wr!(APP_FG, 1);\n    shake_arm();'),
 ('PAGES[pid].desc = 0;','#[cfg(feature="n67")]\n    fw_api::forget_tree(PAGES[pid].root);\n    PAGES[pid].desc = 0;')])
edit('page.rs',[
 ('let vl = read_volatile((r2 + ROW_SUB_LB) as *const u32);','#[cfg(not(feature="n67"))]\n                let vl = read_volatile((r2 + ROW_SUB_LB) as *const u32);\n                #[cfg(feature="n67")]\n                let vl = fw_api::row_secondary(r2);'),
 ('RowSpec::clickable(b"2000nit\\0")','RowSpec::clickable(if cfg!(feature="n67"){b"300nit\\0"}else{b"2000nit\\0"})'),
 ('self.req_val.store(2000,','self.req_val.store(if cfg!(feature="n67"){300}else{2000},'),
 ('st_wr!(BRIGHT_REQ_VAL, 2000);','st_wr!(BRIGHT_REQ_VAL, if cfg!(feature="n67"){300}else{2000});'),
 ('let req = st_rd!(BRIGHT_REQ);','let req = st_rd!(BRIGHT_REQ);\n            self.req.store(0, Ordering::Relaxed);')])
edit('confirm_pop.rs',[
 ('fw_api::obj_is_child_of(root_of(slot), o) || rd32(fw_api::MSGBOX_SINGLETON as *const u32) == o','{\n        #[cfg(feature="n67")]\n        {fw_api::obj_is_child_of(root_of(slot),o)}\n        #[cfg(not(feature="n67"))]\n        {fw_api::obj_is_child_of(root_of(slot), o) || rd32(fw_api::MSGBOX_SINGLETON as *const u32) == o}\n    }'),
 ('fw_api::obj_delete(o);\n    st_wr!(CP_ST[slot], 0);','#[cfg(feature="n67")]\n    { st_wr!(CP_ST[slot],3); return 2; }\n    #[cfg(not(feature="n67"))]\n    fw_api::obj_delete(o);\n    st_wr!(CP_ST[slot], 0);')])
edit('n67/fw_api.rs',[
 ('pub const TOPIC_QUICK_GUESTURE:u32=0;','pub const TOPIC_QUICK_GUESTURE:u32=0x2c67d0a4;'),
 ('transmute(0x0c445941usize);f(key,data,0,0);','transmute(0x0c440be5usize);f(key,data,0,0);'),
 ('transmute(0x0c0f0f19usize)','transmute(0x0c0f0791usize)'),
 ('transmute(0x0c260819usize)','transmute(0x0c243ca5usize)'),
 ('pub unsafe fn watchface_is_on()->u32{0}','pub unsafe fn watchface_is_on()->u32{(crate::APP_FG==0 && rd(0x200ce898 as *const u32)!=0 && rd(0x200cb828 as *const u8)!=0) as u32}'),
 ('pub unsafe extern "C" fn eventbus_subscribe(_t:u32,_a:u32,_cb:u32,_ud:u32)->u32{0}','pub unsafe extern "C" fn eventbus_subscribe(t:u32,a:u32,cb:u32,ud:u32)->u32{let f:unsafe extern "C" fn(u32,u32,u32,u32)->u32=transmute(0x0c465789usize);f(t,a,cb|1,ud)}'),
 ('pub unsafe fn brightness_set_value(v:u32){let f:unsafe extern "C" fn(u32)=transmute(0x0c44db3dusize);f(v);}','pub unsafe fn brightness_set_value(v:u32){brightness_apply_raw(v); }'),
 ('pub unsafe fn brightness_set_auto_adjustment(v:u32){let f:unsafe extern "C" fn(u32)=transmute(0x0c44daf1usize);f(v);}','pub unsafe fn brightness_set_auto_adjustment(v:u32){wr((0x200b5be0+0x1a5) as *mut u8,(v!=0) as u8);let f:unsafe extern "C" fn(u32)=transmute(0x0c44da59usize);f(0);}')])
edit('n67/ipc.rs',[('SHAKE_EN = 0;','SHAKE_EN = 0; // User enables the N67 gesture subscription explicitly.')])
edit('icon_apply.rs',[
 ('if slot == IC_CAL_SLOT {\n        let node','if slot == IC_CAL_SLOT && !cfg!(feature="n67") {\n        let node'),
 ('if safe_ptr(path) && icon_stem_eq','if plausible_ptr(path) && icon_stem_eq'),
 ('let slot = rd32(0x2010_F05C as *const u32);','#[cfg(not(feature="n67"))]\n    let slot = rd32(0x2010_F05C as *const u32);\n    #[cfg(feature="n67")]\n    let slot = 0;')])
print('N67 direct call sites adapted')
