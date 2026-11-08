"""Actual ARM hidden-debug gate and bounded native-image/descriptor export."""
from test_native_entries import NativeBand
from test_n67 import IMAGE
from unicorn.arm_const import *
import struct
class DiagnosticBand(NativeBand):
    def hook(self,u,a,n,ud):
        x,y=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1)]
        if a==0xc25eba0:
            obj=self.obj(x,cls=0x2c68260c);self.sync(x);ret=obj
        elif a==0xc2617d8:
            self.w32(x+36,y);ret=0
        else:return super().hook(u,a,n,ud)
        u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
for base in (0x1d100000,0x1d340000,0x1c900000):
    b=DiagnosticBand(base);b.call('chaos_n67_init',0x3d800000,65536,131072,8192)
    about_root=b.create(17)
    text=b.live_text()
    for t in ['Chaos','运行固件','文华逸洋','IKUN_CXKPRO','谦虚的海鸥','@wzx','许可证','meowl','移植']:
        assert t.encode() in text,'missing upstream About field: '+t
    for row,page in [(7,18),(8,19)]:
        b.click(row)
        assert b.goto==(0xe7d40000|page,0),'About license route'
    for _ in range(4):b.click_and_drive(0)
    assert b'A 25%' not in b.live_text()
    b.click_and_drive(0)
    assert all(t in b.live_text() for t in (b'A 25%',b'B 75%',b'C 100%',b'D 0%'))
    b.click_and_drive(1)
    assert b'/data/chaos/n67-diagnostic.bin' not in b.files
    b.click_and_drive(1)
    for _ in range(50):b.call('chaos_shake_timer',b.timers[0])
    data=b.files[b'/data/chaos/n67-diagnostic.bin']
    header=struct.unpack('<8I',data[:32])
    assert header[0]==0x4744494e and header[2]==base
    assert len(IMAGE)-4<=header[3]<=len(IMAGE)
    assert header[4:6]==(0x3d800000,8192)
    assert len(data)==32+header[3]+8192
    assert data[32:96]==bytes(b.u.mem_read(base,64))
    b.retire(17,about_root);b.create(0);b.create(17)
    assert b'A 25%' not in b.live_text(),'debug mode did not reset on returning home'
    print(f'PASS diagnostics ARM {base:08x}: upstream About information and license routes, five-tap gate, native bitmap render, two-step export, exact relocated image/descriptor bounds, reset')
