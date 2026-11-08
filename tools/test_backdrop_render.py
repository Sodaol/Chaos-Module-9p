"""Execute the rewritten renderer as ARM code, independent of LVGL/firmware."""
from pathlib import Path
import subprocess,tempfile,shutil,io
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[1]
W,H=336,480;SIZE=W*H*4
harness='''#![no_std]
#[path="@@MODULE@@"]mod render;
use render::*;
#[panic_handler]fn panic(_: &core::panic::PanicInfo)->!{loop{}}
static mut JOB:Renderer=Renderer::new();
#[no_mangle]pub unsafe extern "C" fn reset(blur:u32){JOB.reset(blur!=0);}
#[no_mangle]pub unsafe extern "C" fn done()->u32{JOB.finished() as u32}
#[no_mangle]pub unsafe extern "C" fn step(input:*const u8,n:usize,out:*mut u8,m:usize,budget:usize)->u32{
 match JOB.step(core::slice::from_raw_parts(input,n),core::slice::from_raw_parts_mut(out,m),budget){Ok(n)=>n as u32,Err(RenderError::Input)=>0x80000001,Err(RenderError::Output)=>0x80000002}
}
#[no_mangle]pub unsafe extern "C" fn memset(p:*mut u8,v:i32,n:usize)->*mut u8{for i in 0..n{core::ptr::write_volatile(p.add(i),v as u8);}p}
#[no_mangle]pub unsafe extern "C" fn memcpy(p:*mut u8,q:*const u8,n:usize)->*mut u8{for i in 0..n{core::ptr::write_volatile(p.add(i),core::ptr::read_volatile(q.add(i)));}p}
'''
with tempfile.TemporaryDirectory(prefix='chaos-render-') as tmp:
 t=Path(tmp);src=t/'harness.rs';src.write_text(harness.replace('@@MODULE@@',(R/'supervisor/src/n67/backdrop_render.rs').as_posix()))
 subprocess.run(['rustc','--edition=2021','--crate-type=staticlib','--target','thumbv7em-none-eabi','-C','opt-level=2','-C','panic=abort',str(src),'-o',str(t/'core.a')],check=True,capture_output=True)
 sysroot=subprocess.check_output(['rustc','--print','sysroot'],text=True).strip();lld=next((Path(sysroot)/'lib/rustlib').glob('*/bin/rust-lld*'))
 subprocess.run([str(lld),'-flavor','gnu','--gc-sections','-Ttext=0x100000','-Tdata=0x20000000','-e','step','-u','reset','-u','done',str(t/'core.a'),'-o',str(t/'core.elf')],check=True,capture_output=True)
 elf=ELFFile(io.BytesIO((t/'core.elf').read_bytes()));u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS);u.mem_map(0x100000,0x100000);u.mem_map(0x20000000,0x400000);u.mem_map(0x1000000,4096)
 for section in elf.iter_sections():
  if section['sh_flags']&2 and section['sh_type']!='SHT_NOBITS' and section['sh_size']:u.mem_write(section['sh_addr'],section.data())
 syms={s.name:s['st_value'] for s in elf.get_section_by_name('.symtab').iter_symbols()}
 def call(name,*args):
  sp=0x200ff000;u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,0x1000001)
  for reg,value in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):u.reg_write(reg,value)
  if len(args)>4:u.mem_write(sp,args[4].to_bytes(4,'little'))
  u.emu_start(syms[name]|1,0x1000000,count=3000000)
  assert u.reg_read(UC_ARM_REG_PC)==0x1000000,'renderer exceeded bounded call budget'
  return u.reg_read(UC_ARM_REG_R0)
 inp,out=0x20100000,0x20200000
 def run(data,blur,budget=16):
  u.mem_write(inp,data);u.mem_write(out-16,b'G'*16);u.mem_write(out+SIZE,b'G'*16);call('reset',blur)
  count=0
  while not call('done'):
   assert call('step',inp,SIZE,out,SIZE,budget)<=16;count+=1;assert count<2000
  assert bytes(u.mem_read(out-16,16))==b'G'*16 and bytes(u.mem_read(out+SIZE,16))==b'G'*16
  return bytes(u.mem_read(out,SIZE))
 for blur in [0,1]:
  result=run(bytes([10,20,30,255])*(W*H),blur)
  assert result==bytes([6,12,18,255] if blur else [10,20,30,255])*(W*H)
 # Transparent mode must preserve high-frequency opaque pixels exactly.
 sharp=bytes(v for y in range(H) for x in range(W) for v in ([255,0,91,255] if (x+y)%2 else [0,239,17,255]))
 assert run(sharp,0)==sharp,'transparent mode downsampled or blurred original pixels'
 assert run(sharp,0,7)==sharp,'transparent row batching changed image'
 # Input impulse occupies exactly one reduced-resolution sample.
 data=bytearray(bytes([0,0,0,255])*(W*H));cx,cy=42,60
 for y in range(cy*4,cy*4+4):
  for x in range(cx*4,cx*4+4):data[(y*W+x)*4]=255
 result=run(bytes(data),1);kernel=[1,6,15,20,15,6,1]
 for dy in range(-3,4):
  for dx in range(-3,4):
   horizontal=(255*kernel[dx+3]+32)//64;expected=((horizontal*kernel[dy+3]+32)//64)*160//255
   at=(((cy+dy)*4)*W+(cx+dx)*4)*4;assert result[at:at+4]==bytes([expected,0,0,255])
 assert run(bytes(data),1,7)==result,'batch size changed output'
 corner=bytearray(bytes([0,0,0,255])*(W*H))
 for y in range(4):
  for x in range(4):corner[(y*W+x)*4]=255
 edge=run(bytes(corner),1);v=(255*42+32)//64;v=(v*42+32)//64
 assert edge[:4]==bytes([v*160//255,0,0,255]),'clamped edge weights are incorrect' 
 assert run(bytes([255,0,0,0])*(W*H),0)==bytes([0,0,0,255])*(W*H),'transparent input leaked color'
 call('reset',1);u.mem_write(out,b'Q'*SIZE)
 assert call('step',inp,SIZE-1,out,SIZE,16)==0x80000001
 assert call('step',inp,SIZE,out,SIZE-1,16)==0x80000002
 assert call('step',inp,SIZE,out,SIZE,0)==0 and not call('done')
 assert bytes(u.mem_read(out,SIZE))==b'Q'*SIZE
 assert call('step',inp,SIZE,out,SIZE,100)==16,'row budget cap missing'
 print('PASS rewritten renderer ARM: normalized constants, separable binomial impulse, batch-independent output, alpha composition, zero/invalid budget, exact bounds/canaries')
