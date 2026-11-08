"""Execute relocated adapter and original N67 affine constructor/consumer."""
from test_native_entries import NativeBand
from unicorn.arm_const import *
import struct,math
class GridBand(NativeBand):
 def __init__(self,base):
  self.relayouts=[];super().__init__(base)
  self.u.reg_write(UC_ARM_REG_C1_C0_2,0xf00000);self.u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
 def hook(self,u,a,n,ud):
  if 0xc29ec00<=a<0xc29ec3c or 0xc2a04f6<=a<0xc2a071c or 0xc2a07a0<=a<0xc2a080c or 0xc2a0868<=a<0xc2a08d4 or 0xc2a1f68<=a<0xc2a1fa8:return
  if a==0xc4fb974:
   self.relayouts.append(u.reg_read(UC_ARM_REG_R0));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  super().hook(u,a,n,ud)
 def grid(self,mode=1):
  p,root,content=self.native_page('Apps',0x100000)
  o=self.obj(content,size=0x900,cls=0x2c69e840);self.sync(content)
  # Run the real constructor's three-column affine initialization loops, not
  # a test-generated interpretation of table origins. Stop before list mode.
  self.u.reg_write(UC_ARM_REG_SP,0x200fef00);self.u.reg_write(UC_ARM_REG_R7,0x200fef00)
  self.u.reg_write(UC_ARM_REG_R4,o);self.u.emu_start(0xc2a04f7,0xc2a05da,count=200000)
  assert self.u.reg_read(UC_ARM_REG_PC)==0xc2a05da
  self.w32(o+0x880,mode);self.top=p
  return o,p
 def affine(self,ptr,value):
  self.sym['original_affine']=0xc2a1f69;self.call('original_affine',ptr,int(value))
  return struct.unpack('<f',struct.pack('<I',self.u.reg_read(UC_ARM_REG_S0)))[0]
 def bank(self,o,mode=1):return bytes(self.u.mem_read(o+(0x64 if mode==1 else 0x25c),0x1f8))
for base in (0x1d100000,0x1d340000,0x1c900000):
 fresh=GridBand(base);fresh.call('chaos_n67_init',0x3d800000,65536,131072,8192)
 grid,_=fresh.grid();stock=fresh.bank(grid);fresh.drive();assert fresh.bank(grid)==stock,'new installation enabled grid effects'
 b=GridBand(base);b.files[b'/data/chaos/applist.cfg']=b'\7';b.call('chaos_n67_init',0x3d800000,65536,131072,8192)
 o,p=b.grid();original=b.bank(o);edit_original=b.bank(o,0x10001)
 assert abs(b.affine(o+0x64+0xa8,219)-276)<.001
 b.drive();assert b.relayouts==[o]
 assert abs(b.affine(o+0x64+3*24+0xa8,219)-240)<.001
 assert abs(b.affine(o+0x64+24,73)-70)<.001
 assert abs(b.affine(o+0x64+24+0x150,240-193*96/112)-170.667)<1
 b.drive();assert len(b.relayouts)==1,'rewrote unchanged grid every tick'
 b.create(13);b.click(5);assert b.goto==(0xe7d4001c,0)
 b.create(28)
 # Real switch VALUE_CHANGED (29) uses the regular dispatch.
 def switch(slot):
  rows=b.symbol('5state5PAGES')+28*72
  # Use event bindings and row callback, as native controls do.
  row=b.r32(rows+slot*4);control=b.r32(row+0x60)
  cb=next(cb for obj,cb,code,ctx in b.events if obj==control)
  e=b.alloc(24);b.w32(e,control);b.w32(e+4,control);b.w8(e+8,29)
  b.sym['toggle_grid']=cb;b.call('toggle_grid',e);b.drive()
 for slot in (0,1,2):switch(slot)
 assert b.files[b'/data/chaos/applist.cfg']==b'\0'
 b.top=p;b.drive();assert b.bank(o)==original,'off must restore exact native constructor bytes'
 assert b.bank(o,0x10001)==edit_original,'inactive edit table was touched'
 # Re-enable all, then verify edit mode uses its own table origin.
 b.create(28)
 for slot in (0,1,2):switch(slot)
 b.w32(o+0x880,0x10001);b.top=p;b.drive()
 assert b.bank(o,0x10001)!=edit_original
 # Every switch combination must restore disabled axes byte-for-byte in both modes.
 b.w32(o,0x2c69e840)
 current=7
 for mode,baseline in [(1,original),(0x10001,edit_original)]:
  for mask in range(8):
   b.create(28)
   for slot in range(3):
    if ((mask^current)>>slot)&1:switch(slot)
   current=mask;b.w32(o+0x880,mode);b.top=p;b.drive()
   actual=b.bank(o,mode)
   for axis,bit in [(0,2),(1,1),(2,0)]:
    if not mask&(1<<bit):assert actual[axis*168:(axis+1)*168]==baseline[axis*168:(axis+1)*168],(mode,mask,axis)
   assert all(math.isfinite(v) for v in struct.unpack('<126f',actual))
   if not mask&2 and mask&1:
    for q in range(6):
     y=b.affine(o+(0x64 if mode==1 else 0x25c)+q*24+0xa8,q*73)
     size=b.affine(o+(0x64 if mode==1 else 0x25c)+q*24+0x150,int(y))
     assert abs(size-[0,170.667,256.667,256.667,256.667,170.667][q])<2
 # Foreign class and list mode must never be patched.
 before=b.bank(o);b.w32(o+0x880,3);b.drive();assert b.bank(o)==before
 b.w32(o+0x880,1);b.w32(o,0x2c683310);before=b.bank(o);b.drive();assert b.bank(o)==before
 print(f'PASS grid {base:08x}: original N67 constructor and affine consumer, 3 switches, saved choices, exact default restoration, mode/class gates, no repeated redraw')
