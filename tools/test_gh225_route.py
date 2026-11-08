"""Run actual GH225 route and pulse timing; native I/O and clock are doubles."""
from test_vibration_errors import VibrationBand
from unicorn.arm_const import *
import struct
class GHBand(VibrationBand):
 def __init__(self,base):
  self.commands=[];self.closes=0;self.stop_fail=0;self.fail=0;super().__init__(base)
  self.low=self.alloc(16);upper=self.alloc(4);inode=self.alloc(32);self.file=self.alloc(20)
  self.w32(self.low,0x2c6f6754);self.w32(upper,self.low);self.w32(inode+28,upper);self.w32(self.file+16,inode)
 def hook(self,u,a,n,ud):
  x,y,z=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)];ret=0
  if a==0xc37e30c and self.s(x)==b'/dev/lra0':ret=77
  elif a==0xc37c0d0:self.w32(y,self.file)
  elif a==0xc37dba4 and x==77:self.closes+=1
  elif a==0xc37e1b4:
   self.commands.append((y,z,bytes(u.mem_read(z,12)) if y in (0x3105,0x3109) else None))
   ret=-19 if y==self.fail else 0
   if y==0x3102 and self.stop_fail:self.stop_fail-=1;ret=-19
  else:return super().hook(u,a,n,ud)
  u.reg_write(UC_ARM_REG_R0,ret&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def setup(self):self.call('chaos_n67_init',0x3d800000,65536,131072,8192);self.create(20)
for base in (0x1d100000,0x1d340000,0x1c900000):
 b=GHBand(base);b.setup();b.click(0);b.drive()
 assert [x[0] for x in b.commands][:4]==[0x3109,0x3108,0x3105,0x3101]
 assert struct.unpack('<IfI',b.commands[2][2])==(0,0.25,0)
 assert b.driver_calls==0
 for _ in range(5):b.call('chaos_gh225_tick')
 assert b.commands[-1][0]==0x3102 and b.closes==1
 b=GHBand(base);b.setup();b.w8(b.low+8,1);b.w32(b.low+12,struct.unpack('<I',struct.pack('<f',0.1))[0]);b.click(0);b.drive()
 assert b.commands[0][0]==0x3108 and abs(struct.unpack('<IfI',b.commands[1][2])[1]-0.1)<0.00001
 print(f'PASS GH225 ARM {base:x}: mode4 parameter/start, timer stop without delay, native service not duplicated, existing strength limit respected')
for disabled,busy,mode in [(1,0,0),(0,1,0),(0,0,2)]:
 b=GHBand(0x1d100000);b.setup();b.w8(0x200cbb6d,disabled);b.w8(0x200d6de4,busy);b.w8(0x200cc6bc,mode);b.click(0);b.drive();assert not b.commands and b.closes==1
for table in (0x2c6f6000,):
 b=GHBand(0x1d100000);b.setup();b.w32(b.low,table);b.click(0);b.drive();assert not b.commands and b.driver_calls==1
b=GHBand(0x1d100000);b.setup();b.fail=0x3105;b.click(0);b.drive();assert [v[0] for v in b.commands]==[0x3109,0x3108,0x3105,0x3102] and b.closes==1
b=GHBand(0x1d100000);b.setup();b.stop_fail=3;b.click(0);b.drive()
for _ in range(10):b.call('chaos_gh225_tick')
assert b.closes==1 and sum(x[0]==0x3102 for x in b.commands)==4
print('PASS GH225 guards: system disable/mode/busy, unknown driver native fallback, failure stop and repeated stop failure recovery')
for base in (0x1d100000,0x1d340000,0x1c900000):
 for table in (0x2c6f66ac,0x2c6f6754):
  for button,strength in ((0,0.25),(1,0.125)):
   b=GHBand(base);b.setup();b.w32(b.low,table);b.click(button);b.drive()
   assert [c[0] for c in b.commands][:4]==[0x3109,0x3108,0x3105,0x3101]
   assert struct.unpack('<IfI',b.commands[2][2])==(0,strength,0)
   for _ in range(6):b.call('chaos_gh225_tick')
   assert b.commands[-1][0]==0x3102 and b.closes==1 and b.driver_calls==0
 print(f'PASS dual motor ARM {base:x}: AW86225 and GH225, both pulse strengths, no duplicate native effect, timer stop and descriptor close')
for disabled,busy,mode in [(1,0,0),(0,1,0),(0,0,2)]:
 b=GHBand(0x1d100000);b.setup();b.w32(b.low,0x2c6f66ac);b.w8(0x200cbb6d,disabled);b.w8(0x200d6de4,busy);b.w8(0x200cc6bc,mode);b.click(0);b.drive();assert not b.commands and b.closes==1
b=GHBand(0x1d100000);b.setup();b.w32(b.low,0x2c6f66ac);b.w8(b.low+8,1);b.w32(b.low+12,struct.unpack('<I',struct.pack('<f',0.1))[0]);b.click(0);b.drive();assert abs(struct.unpack('<IfI',b.commands[1][2])[1]-0.1)<0.00001
for failed_command in (0x3109,0x3108,0x3105,0x3101):
 b=GHBand(0x1d100000);b.setup();b.w32(b.low,0x2c6f66ac);b.fail=failed_command;b.click(0);b.drive();assert b.closes==1 and b.commands[-1][0]==0x3102
print('PASS AW guards: system disable/busy/mode, existing lower strength limit, stop/close after any setup/start failure')
