"""Execute the actual prefix from Lua-string aliases, with exact cache writes."""
from pathlib import Path
import json,struct,re
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[1];G=R/'n67/generated'
b=(G/'bridge.bin').read_bytes();meta=json.loads((G/'bridge.json').read_text())
V=R/'n67/injection-v21'
assert b[:218]==(V/'bootstrap.bin').read_bytes(),'v2.1 bootstrap differs'
f=meta['functions']['bt_timer_bootstrap']
assert b[f['offset']:f['offset']+f['size']]==(V/'timer-bootstrap.bin').read_bytes(),'v2.1 timer bootstrap differs'
names=['bt_magic','bt_copy_bytes','bt_sync_code']
end=max(meta['functions'][n]['offset']+meta['functions'][n]['size'] for n in names)
md=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
for i in md.disasm(b[:end],0):
 assert 'pc' not in i.op_str or i.mnemonic=='pop','bootstrap accesses external PC-relative data'
 if i.mnemonic.startswith('b') and '#' in i.op_str:
  target=int(i.op_str.rsplit('#',1)[1],0);assert 0<=target<end,(i.address,target)
for src in [0x3d010010,0x3d01003c,0x3d010080]:
 u=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
 for p,n in [(0x1d010000,0x2000),(0x3d010000,0x2000),(0x3d100000,0x4000),(0x20000000,0x10000),(0x07ffa000,0x3000),(0x100000,0x1000)]:u.mem_map(p,n)
 u.mem_write(src,b);u.mem_write(src-0x20000000,b)
 dst=0x3d100024;u.mem_write(dst-4,b'HEAD');u.mem_write(dst+len(b),b'TAIL')
 writes=[]
 def cache(uc,access,p,size,value,data):
  if p in [0x07ffc080,0x07ffa018]:writes.append((p,value))
 u.hook_add(UC_HOOK_MEM_WRITE,cache)
 u.hook_add(UC_HOOK_CODE,lambda uc,a,n,d:uc.emu_stop(),begin=0x100000,end=0x100002)
 def call(name,args):
  u.reg_write(UC_ARM_REG_SP,0x2000f000);u.reg_write(UC_ARM_REG_LR,0x100001)
  for r,v in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2],args):u.reg_write(r,v)
  u.emu_start((src-0x20000000+meta['functions'][name]['offset'])|1,0,count=100000)
  assert u.reg_read(UC_ARM_REG_PC)==0x100000
  return u.reg_read(UC_ARM_REG_R0)
 assert call('bt_copy_bytes',[dst,src,len(b)])==dst
 assert bytes(u.mem_read(dst,len(b)))==b
 assert bytes(u.mem_read(dst-4,4))==b'HEAD' and bytes(u.mem_read(dst+len(b),4))==b'TAIL'
 assert call('bt_sync_code',[dst,len(b)])==len(b)
 lines=list(range(dst&~31,(dst+len(b)-1&~31)+1,32))
 assert writes==[(0x07ffc080,p) for p in lines]+[(0x07ffa018,p-0x20000000) for p in lines]
 writes.clear()
 assert call('bt_copy_bytes',[dst,src,0])==0
 assert call('bt_copy_bytes',[0x20001000,src,len(b)])==0
 assert call('bt_sync_code',[dst,0])==0 and not writes
 print(f'PASS bootstrap from Lua executable alias {src-0x20000000:08x}: exact copy, canaries, both cache aliases, invalid range rejection')
old_copy=(len(b)+3)//4;old_copy=(old_copy+47)//48
old_cache_lines=(len(b)+62)//32;old_sync=2*((old_cache_lines+47)//48)
new_boot=1+2+2+2 # source ABI dump, prefix synchronization, native copy, native sync
print(f'Bootstrap command estimate excluding unchanged allocation/magic: {old_copy+old_sync} -> {new_boot}; {end}-byte prefix / {len(b)}-byte bridge.')
