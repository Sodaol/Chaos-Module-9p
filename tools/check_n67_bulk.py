from pathlib import Path
import json,random
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2
r=Path(__file__).resolve().parents[1]/'n67/generated'
meta=json.loads((r/'bridge.json').read_text()); blob=(r/'bridge.bin').read_bytes()
u=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
for a,n in [(0x1d700000,0x2000),(0x3d100000,0x100000),(0x3d300000,0x100000),(0x200e0000,0x20000),(0x100000,4096),(0x07ffa000,0x3000)]:u.mem_map(a,n)
u.mem_write(0x1d700000,blob)
u.hook_add(UC_HOOK_CODE,lambda uc,a,n,data:uc.emu_stop(),begin=0x100000,end=0x100002)
writes=[]
u.hook_add(UC_HOOK_MEM_WRITE,lambda uc,access,a,size,value,data:writes.append((a,value)),begin=0x07ffa000,end=0x07ffd000)
def call(name,*args):
 u.reg_write(UC_ARM_REG_SP,0x200ff000);u.reg_write(UC_ARM_REG_LR,0x100001)
 for reg,val in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2),args):u.reg_write(reg,val)
 u.emu_start((0x1d700000+meta['functions'][name]['offset'])|1,0x100002,count=5000000)
 return u.reg_read(UC_ARM_REG_R0)
for n in (1,2,3,127,128,8192,136592):
 src,dst=0x3d100040,0x3d300040
 data=random.Random(n).randbytes(n)
 u.mem_write(src,data);u.mem_write(dst-4,b'HEAD'+bytes(n)+b'TAIL')
 assert call('bt_copy_bytes',dst,src,n)==dst
 assert bytes(u.mem_read(dst-4,n+8))==b'HEAD'+data+b'TAIL'
 assert bytes(u.mem_read(src,n))==data
for args in [(0x3d300040,0x3d100040,0),(0x3d300040,0x3d100040,0x100001),(0x3efffff0,0x3d100040,128),(0x3d300040,0x20000000,128)]:
 assert call('bt_copy_bytes',*args)==0
for p,n in [(0x3d300040,1),(0x3d300043,35),(0x3d300040,136592)]:
 writes.clear();assert call('bt_sync_code',p,n)==n
 lines=list(range(p&~31,((p+n-1)&~31)+1,32))
 expected=[(0x07ffc080,x) for x in lines]+[(0x07ffa018,x-0x20000000) for x in lines]
 assert writes==expected,(len(writes),len(expected))
writes.clear();assert call('bt_sync_code',0x3d300040,0)==0 and not writes
print('PASS actual ARM bridge: byte copies including full payload, canaries, source preservation, invalid bounds, exact cache register order and aliases')
