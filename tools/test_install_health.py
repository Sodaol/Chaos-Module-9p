"""Execute read-only installer health against relocated ARM with explicit registry doubles."""
from pathlib import Path
import json
from test_port_pages import PortBand
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_PC,UC_ARM_REG_LR
class HealthBand(PortBand):
    missing_page=False
    def hook(self,u,a,n,ud):
        if a==0xc448748 and self.missing_page:
            u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        return super().hook(u,a,n,ud)
for base in (0x1d100000,0x1d340000,0x1c900000):
    b=HealthBand(base)
    b.call('chaos_n67_init',0x3d800000,65536,131072,8192)
    b.registrar()
    g=Path(__file__).resolve().parents[1]/'n67/generated'
    meta=json.loads((g/'bridge.json').read_text())
    b.sym['health']=0x1d700000+meta['functions']['bt_install_health']['offset']
    check=lambda:b.call('health',0xc4467b5,0xe7d4)
    assert check()==31
    node=b.registered;arr=b.r32(node+0x2c);page=b.page(0)
    before=bytes(b.u.mem_read(node,60))
    assert check()==31 and bytes(b.u.mem_read(node,60))==before
    b.w32(node+0x2c,0);assert check()==1;b.w32(node+0x2c,arr)
    b.w32(arr,0);assert check()==1;b.w32(arr,31)
    b.w32(arr+8,0);assert check()==3;b.w32(arr+8,page)
    b.missing_page=True;assert check()==23;b.missing_page=False
    cb=b.r32(page+0x48);b.w32(page+0x48,0);assert check()==15;b.w32(page+0x48,cb)
    record=b.alloc(32);b.w32(record,0xe7d4);b.w32(0x200a393c,record);b.w32(0x200a3940,record)
    assert check()==63
    b.w8(node+0x38,1);assert check()==127
    assert b.call('health',0xc4467b7,0xe7d4)==0
    assert b.call('health',0xc4467b5,0xe7d5)==0
    print(f'PASS installer health ARM {base:08x}: ID-only false success, missing array/default page/page-manager entry/callback, desktop/hidden distinction, read-only guards')
