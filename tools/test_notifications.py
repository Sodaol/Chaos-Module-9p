"""Execute native toast wrapper ARM and status-row behavior at three relocations.
The system drawing/service core is a double, not an actual screen test.
"""
from test_port_pages import PortBand,LOG
from unicorn.arm_const import *

class ToastBand(PortBand):
    def __init__(self,base):
        self.toast_ptrs=[];super().__init__(base)
    def hook(self,u,a,n,ud):
        if a in (0xc36f064,0xc36ef10):raise AssertionError('custom or plain toast used instead of system notification')
        if a==0xc4f1f28:
            p=u.reg_read(UC_ARM_REG_R0);w=self.r32(p+20);text=self.s(w);text.decode('utf8');assert text
            assert self.s(self.r32(p+12))==b'Chaos' and self.r32(p+80)==1
            self.toast_ptrs.append(w);self.toasts.append((text,0))
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        return super().hook(u,a,n,ud)
    def clear_log(self):
        self.create(16);self.files[LOG]=b'example\n'
        self.click_and_drive(1)
        count=len(self.toasts);self.click(2)
        assert len(self.toasts)==count,'toast executed in input event'
        self.drive()

def descendant(b,o,root):
    for _ in range(20):
        if o==root:return True
        if o not in b.objects:return False
        o=b.objects[o]['parent']
    return False

for base in (0x1d100000,0x1d340000,0x1c900000):
    b=ToastBand(base);b.call('chaos_n67_init',0x3d800000,65536,131072,8192)
    root=b.create(20)
    empty=[(o,v) for o,v in b.objects.items() if o not in b.deleted and descendant(b,o,root)
           and v.get('native')=='row' and not b.objects[b.r32(o+0x50)]['text']]
    assert not empty,'a status placeholder was still created'
    assert not b.toasts,'opening a page emitted a notification'
    # Normal information text remains readable but has no clickable card surface.
    root=b.create(0)
    info=[(o,v) for o,v in b.objects.items() if o not in b.deleted and descendant(b,o,root)
          and v.get('native')=='row' and b.r32(o+0x54)]
    assert info
    for o,v in info:
        # Data rows are composed information; the CPU display row uses the display builder.
        assert v['props'].get(0x21)==255,'information card lost its background'
    b.clear_log()
    assert b.toasts[-1][0]=='日志已清空'.encode()
    assert '日志已清空'.encode() not in b.live_text(),'result duplicated inline'
    pointer=b.toast_ptrs[-1];text=b.s(pointer);count=len(b.toasts)
    b.drive();b.create(16);b.drive()
    assert len(b.toasts)==count,'render/return repeated a notification'
    assert b.s(pointer)==text,'toast retained a temporary page buffer'
    # Sleeping must drop, rather than postpone, the toast.
    b.create(16);b.files[LOG]=b'new log';b.click_and_drive(1);b.w8(0x200ca360+0x19,0);b.click_and_drive(2)
    assert len(b.toasts)==count
    b.w8(0x200ca360+0x19,2);b.drive();assert len(b.toasts)==count
    # A foreign foreground application must not receive Chaos action toasts.
    b.create(16);b.files[LOG]=b'new log';b.click_and_drive(1);foreign=b.alloc(112);b.w32(foreign+0x14,0x160000);b.top=foreign
    b.click_and_drive(2);assert len(b.toasts)==count
    print(f'PASS notification ARM {base:08x}: zero-height hidden empty rows, plain information, actual native toast ABI, deferred delivery, stable UTF-8 text, no render spam, sleep/foreground gates')
