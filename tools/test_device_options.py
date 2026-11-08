"""Actual N67 rotation body + Bluetooth wrappers; devices/GUI callbacks are doubles."""
from test_port_pages import PortBand
from unicorn.arm_const import *
import struct

class DeviceBand(PortBand):
 def __init__(self,base):
  self.bt_name=b'Xiaomi Band 9 Pro';self.accept=True;self.name_calls=[];self.launches=[];self.resize_events=[]
  super().__init__(base)
  self.api=self.alloc(0x100);self.adapter=self.alloc(24);lower=self.alloc(0x40)
  self.w32(0x200bad94,self.api);self.w32(0x200bad90,self.adapter)
  self.w32(self.api+0x14,0xc3bd211);self.w32(self.api+0x18,0xc3bd25d)
  self.w32(self.adapter+8,lower);self.w32(lower+0x14,0xc080201);self.w32(lower+0x18,0xc080211)
  self.nameptr=self.alloc(64);self.u.mem_write(self.nameptr,self.bt_name+b'\0')
  self.display=self.alloc(0x180);self.driver=self.alloc(0x80);self.root=self.obj(0)
  self.screenlist=self.alloc(4);self.w32(self.screenlist,self.root)
  self.w32(self.display,self.driver);self.w32(self.display+0xc,self.screenlist);self.w32(self.display+0x24,1)
  self.w32(self.display+0x10,self.root);self.w32(0x200b3750,self.display)
  self.u.mem_write(self.driver,struct.pack('<HH',336,480));self.w8(self.driver+0x10,0)
 def hook(self,u,a,n,ud):
  # Execute the real btm wrappers and in-ROM LVGL setter body / resolution getters.
  if 0xc3bd210<=a<0xc3bd29e or 0xc46c756<=a<0xc46c83c or 0xc2578fc<=a<0xc257944:return
  x,y,z=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)];ret=0
  if a==0xc080200:
   assert x==self.adapter;name=self.s(y);assert z==len(name)+1
   self.name_calls.append(name)
   if self.accept:self.bt_name=name;self.u.mem_write(self.nameptr,name+b'\0')
   else:ret=1
  elif a==0xc080210:assert x==self.adapter;ret=self.nameptr
  elif a==0xc3c13d0:ret=0
  elif a==0xc23a580:u.mem_write(x,bytes(u.mem_read(y,8)))
  elif a==0xc0e6740:u.mem_write(x,bytes(y));ret=x
  elif a in (0xc23b38a,0xc24090c):pass
  elif a==0xc240ad4:self.resize_events.append((x,y,bytes(u.mem_read(z,8))))
  else:return super().hook(u,a,n,ud)
  u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def start(self):self.call('chaos_n67_init',0x3d800000,65536,131072,8192)
 def key(self,code):
  obj,cb,_,_=next(e for e in reversed(self.events) if e[3]==code and e[2]==7 and e[0] not in self.deleted)
  event=self.alloc(16);self.w32(event,obj);self.w32(event+4,obj);self.w8(event+8,7);self.w32(event+12,code)
  self.sym['keyboard_action']=cb;self.call('keyboard_action',event)

for base in (0x1d100000,0x1d340000,0x1c900000):
 b=DeviceBand(base);b.start();b.create(15);b.click_and_drive(4);assert b.goto==(0xe7d40020,0)
 b.create(32);assert b.bt_name in b.live_text()
 before=bytes(b.u.mem_read(b.driver,0x80));b.click(1);assert bytes(b.u.mem_read(b.driver,0x80))==before
 b.drive();assert (b.u.mem_read(b.driver+0x10,1)[0]>>4)&3==2
 assert b.resize_events and b.resize_events[-1][1]==0x2b
 assert struct.unpack('<HH',b.u.mem_read(b.root+0x18,4))==(335,479)
 b.click_and_drive(1);assert b.u.mem_read(b.driver+0x10,1)==b'\0'
 # Verify the handoff restores callee-saved registers and stack via the actual ROM epilogue.
 regs=[UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8]
 for i,reg in enumerate(regs):b.u.reg_write(reg,0x12340000+i)
 b.call('chaos_n67_rotate_display',b.display,2)
 assert [b.u.reg_read(reg) for reg in regs]==[0x12340000+i for i in range(5)]
 assert b.u.reg_read(UC_ARM_REG_SP)==0x200ff000
 b.create(32);b.click_and_drive(0);assert b.goto==(0xe7d4001b,0);b.create(27)
 b.key(0x102)
 for c in b'meowl 9p':b.key(c)
 b.key(0x103);assert not b.name_calls,'setter ran inside keyboard event dispatch'
 b.create(32);b.drive();b.drive();assert b.name_calls==[b'MEOWL 9P'] and b.bt_name==b'MEOWL 9P'
 # Failed native requests must not display a success message or alter the old name.
 b.accept=False;b.create(32);b.click_and_drive(0);b.create(27);b.key(0x102);b.key(ord('x'));b.key(0x103);b.create(32);b.drive()
 assert b.bt_name==b'MEOWL 9P'
 # Unknown/null manager and corrupt display never call into their native services.
 old=len(b.name_calls);b.w32(0x200bad90,0);b.w32(0x200b3750,0);b.create(32);b.click_and_drive(0);b.click_and_drive(1);assert len(b.name_calls)==old
 print(f'PASS devices {base:x}: deferred Bluetooth setter through real btm vtable wrapper/readback; native 180/0 rotation, root resize event, ARM callee registers+SP; unavailable guards')
