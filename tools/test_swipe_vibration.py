"""Deferred scroll feedback, cooldown, screen gating and return-to-home transitions."""
from test_native_entries import NativeBand
from unicorn.arm_const import *
class SwipeBand(NativeBand):
    def hook(self,u,a,n,ud):
        if a==0xc1610b8:
            u.reg_write(UC_ARM_REG_R0,self.now);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        return super().hook(u,a,n,ud)
    def tick(self):self.call('chaos_shake_timer',self.timers[0])
    def scroll(self,content,cb):
        e=self.alloc(16);self.w32(e,content);self.w32(e+4,content);self.w8(e+8,11)
        self.sym['scroll_callback']=cb;self.call('scroll_callback',e)
for base in (0x1d100000,0x1d340000,0x1c900000):
    b=SwipeBand(base);b.now=1000
    b.call('chaos_n67_init',0x3d800000,65536,131072,8192)
    b.create(20);b.click_and_drive(2)
    home,root,content=b.native_page('主页',0x100000)
    b.w32(content+0x1c,16)
    image=b.obj(content,cls=0x2c6825bc);p=b.alloc(80)
    b.u.mem_write(p,b'/resource/app/heartrate/launcher.bin\0');b.w32(image+36,p)
    b.sync(content);b.top=home;b.tick()
    cb=next(cb for o,cb,f,ctx in b.events if o==content and f==0)
    b.vibrations.clear()
    b.scroll(content,cb);assert not b.vibrations
    b.tick();assert len(b.vibrations)==1 and b.vibrations[0]==bytes([3])+bytes(11)
    b.now+=1;b.scroll(content,cb);b.tick();assert len(b.vibrations)==1
    b.now+=250;b.scroll(content,cb);b.tick();assert len(b.vibrations)==2
    before=len(b.events)
    for _ in range(10):b.tick()
    assert len(b.events)==before,'duplicated launcher listeners'
    b.w8(0x200ca360+0x19,0);b.now+=1000;b.scroll(content,cb);b.tick()
    assert len(b.vibrations)==2
    b.w8(0x200ca360+0x19,2)
    b.create(20);b.click_and_drive(2) # disable scroll
    b.top=home;b.now+=1000;b.scroll(content,cb);b.tick();assert len(b.vibrations)==2
    b.create(20);b.click_and_drive(3) # enable return-to-home
    b.top=home;b.now+=1000;b.tick();assert len(b.vibrations)==3
    b.tick();assert len(b.vibrations)==3,'stationary home generated feedback'
    assert b.files[b'/data/chaos/swipe_vib.cfg']==b'\0\1'
    print(f'PASS swipe ARM {base:08x}: native scroll event, deferred motor request, 200-ms cooldown, listener dedup, screen gate, independent saved switches, home transition')
