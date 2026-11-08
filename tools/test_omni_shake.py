from pathlib import Path
import struct
from unicorn.arm_const import *
p=Path(__file__).with_name('test_shake.py');ns={'__file__':str(p)};exec(compile(p.read_text('utf8').split('\nfor base in ')[0],str(p),'exec'),ns);ShakeBand=ns['ShakeBand']
class AccelBand(ShakeBand):
 def __init__(self,base):self.packets=[];self.accel_open=0;self.accel_close=0;self.stamp=1;super().__init__(base)
 def hook(self,u,a,n,ud):
  x,y,z=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)];ret=0
  if a==0xc104b9c and x==0x2c5eba9c:assert y==0;self.accel_open+=1;ret=88
  elif a==0xc37f458 and x==88:
   assert z==24
   if self.packets:data=self.packets.pop(0);u.mem_write(y,data);ret=len(data)
   else:ret=0xffffffff
  elif a==0xc37dba4 and x==88:self.accel_close+=1
  else:return super().hook(u,a,n,ud)
  u.reg_write(UC_ARM_REG_R0,ret&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def start(self):
  self.call('chaos_n67_init',0x3d800000,65536,131072,8192);self.setup();self.create(10);self.toggle()
  self.home,root,content=self.native_page('Home',0x100000);self.call('chaos_on_pause',self.page(10));self.top=self.home
 def feed(self,xyz,stamp=None):
  self.stamp+=100000;self.packets.append(struct.pack('<Qffff',stamp if stamp is not None else self.stamp,*xyz,20.0));self.call('chaos_shake_timer',self.timers[0])
for base in (0x1d100000,0x1d340000,0x1c900000):
 for axis in range(3):
  for sign in (-1,1):
   b=AccelBand(base);b.start();baseline=[0.,0.,9.8];b.feed(baseline)
   v=baseline.copy();v[axis]+=8*sign;b.feed(v);v[axis]-=16*sign;b.feed(v)
   assert len(b.switches)==1,(axis,sign,b.switches)
   for i in range(8):v[axis]=-v[axis];b.feed(v)
   assert len(b.switches)==1,'cooldown failed'
 print(f'PASS omni shake ARM {base:x}: X/Y/Z both directions trigger native face switch without gesture event; cooldown prevents repeated switching')
b=AccelBand(0x1d100000);b.start()
for _ in range(10):b.feed([0.,0.,9.8])
for i in range(10):b.feed([i*0.2,0.,9.8])
assert not b.switches
b.feed([20.,0.,9.8],stamp=1234567);b.feed([-20.,0.,9.8],stamp=1234567);assert not b.switches
b.feed([float('nan'),0.,9.8]);b.feed([0.,0.,9.8]);assert not b.switches
b.w8(0x200ca360+0x19,0);b.call('chaos_accel_tick');assert b.accel_close==1
b.w8(0x200ca360+0x19,2);settings,_,_=b.native_page('Settings',0x160000);b.top=settings
for _ in range(50):b.call('chaos_accel_tick')
assert b.accel_open==1,'foreign UI subscribed to accelerometer'
b.top=b.home;b.w8(b.manager+0x6c,1)
for _ in range(20):b.call('chaos_accel_tick')
assert b.accel_open==1,'AOD subscribed'
print('PASS motion filters: stationary/slow motion/duplicate timestamp/NaN do not switch; screen off closes subscription, settings and AOD do not subscribe')
