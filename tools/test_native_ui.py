"""Native row/switch event contract: execute the original firmware handlers.
Allocation, rendering, event transport and style services are explicit doubles.
"""
from test_port_pages import PortBand
from unicorn.arm_const import *
import struct

class NativeUiBand(PortBand):
    def __init__(self,base):
        self.sent=[];super().__init__(base)
    def hook(self,u,a,n,ud):
        if 0xc26f6e4<=a<0xc26f71c or 0xc43375c<=a<0xc4337d0:return
        x,y,z=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
        if a==0xc24098c:ret=1 if x==0x2c68da78 else 0
        elif a==0xc239f7a:ret=0
        elif a in (0xc23ef54,0xc23ef78):
            state=struct.unpack('<H',u.mem_read(x+0x20,2))[0]
            u.mem_write(x+0x20,struct.pack('<H',state|y if a==0xc23ef54 else state&~y));ret=0
        elif a==0xc240ad4:self.sent.append((x,y,z));ret=0
        else:return super().hook(u,a,n,ud)
        u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def native(self,fn,cls,target,code):
        e=self.alloc(24);self.w32(e,target);self.w32(e+4,target);self.w8(e+8,code)
        self.sym['native_control_handler']=fn;self.call('native_control_handler',cls,e)
        return e

for base in (0x1d100000,0x1d340000,0x1c900000):
    b=NativeUiBand(base);b.call('chaos_n67_init',0x3d800000,65536,131072,8192)
    b.create(8)
    switch=next(o for o,v in b.objects.items() if o not in b.deleted and v.get('native')=='switch')
    row=b.objects[switch]['parent']
    assert b.r32(row)==0x2c68da78 and b.r32(row+0x60)==switch
    assert b.u.mem_read(row+0x71,1)==b'\x01'
    b.native(0xc26f6e5,0x2c68da78,row,7)
    assert [(o,c) for o,c,p in b.sent]==[(switch,7)],'native row did not delegate one click'
    b.sent.clear();b.w32(switch+0x1c,8)
    b.native(0xc43375d,0x2c68daf8,switch,7)
    assert [(o,c) for o,c,p in b.sent]==[(switch,29)]
    assert struct.unpack('<H',b.u.mem_read(switch+0x20,2))[0]&1
    cb=next(cb for o,cb,f,ud in b.events if o==switch and f==0)
    def notify(code):
        e=b.alloc(24);b.w32(e,switch);b.w32(e+4,switch);b.w8(e+8,code)
        b.sym['native_switch_callback']=cb;b.call('native_switch_callback',e)
    state=b.symbol("WF_SHOW_BUILTIN");before=b.r32(state)
    notify(29)
    after=b.r32(state);assert after!=before
    # A click notification after VALUE_CHANGED must not toggle the model again.
    notify(7)
    assert b.r32(state)==after,"native click toggled Chaos state twice"
    # Confirm the core doesn't interpret raw CLICKED as VALUE_CHANGED anymore.
    b.sent.clear();b.native(0xc43375d,0x2c68daf8,switch,7)
    assert not (struct.unpack('<H',b.u.mem_read(switch+0x20,2))[0]&1)
    assert len(b.sent)==1 and b.sent[0][1]==29
    # Display controls are native bar objects, with actual values retained.
    b.create(0)
    def px(o):
        face=b.objects[o]['props'].get(0x57,0)
        assert face,'missing explicit font'
        return b.r32(b.r32(face+28)+8)&65535
    rows=[o for o,v in b.objects.items() if o not in b.deleted and v.get('native')=='row' and not v.get('flags',0)&1]
    for row in rows:
        body=b.r32(row+0x4c);label=b.r32(row+0x50);sub=b.r32(row+0x54)
        assert b.objects[body]['x']==16 and b.objects[label]['x']==0,'double horizontal inset'
        assert px(label)==28 and b.objects[label]['w'] in (208,272)
        if sub:assert px(sub)==22 and b.objects[sub]['x']==0
        h=b.objects[row]['h'];assert h>=88
        assert b.objects[body]['y']+b.objects[body]['h']<=h
    titles=[o for o,v in b.objects.items() if o not in b.deleted and v.get('native')=='title']
    assert titles
    for title in titles:
        label=b.r32(title+0x28);clock=b.r32(title+0x30)
        assert px(label)==28 and px(clock)==18
        assert b.objects[label].get("long_mode")==1 and b.objects[clock].get("long_mode")==1,"header marquee still enabled"
        assert b.objects[label]['x']+b.objects[label]['w']<=b.objects[clock]['x']
        assert b.objects[clock]['x']+b.objects[clock]['w']<=320
    bars=[v for o,v in b.objects.items() if o not in b.deleted and v.get('native')=='bar']
    assert len(bars)>=2 and all(0<=v['value']<=100 for v in bars)
    b.create(5)
    checks=[o for o,v in b.objects.items() if o not in b.deleted and v.get('native')=='check']
    assert checks
    parent=b.objects[checks[-1]]['parent'];assert b.u.mem_read(parent+0x71,1)==b'\x00'
    b.sent.clear();b.native(0xc26f6e5,0x2c68da78,parent,7)
    assert not b.sent,'checkbox click would be dispatched twice'
    b.create(3)
    assert any(v.get('native')=='button' for o,v in b.objects.items() if o not in b.deleted)
    print(f'PASS native UI ARM {base:08x}: real firmware row delegation, native switch toggles and event 29, explicit 28/22px typography, nested label bounds, title/clock separation, native controls')
