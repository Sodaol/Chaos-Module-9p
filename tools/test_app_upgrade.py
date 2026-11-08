"""ARM regression for staged rows, in-place selection, launch ABI and capacity bounds."""
import test_app_manager as am
from test_app_manager import AppBand,APPS,ORDER,ALL
from unicorn.arm_const import *
from test_n67 import META
from pathlib import Path

class LaunchBand(AppBand):
 def __init__(self,base):
  self.lookups=[];self.launches=[];self.available=True
  super().__init__(base);self.info=self.alloc(64);self.w32(self.info,0x12345678)
 def hook(self,u,a,n,ud):
  if 0xc4fb558<=a<0xc4fb59a:return # Execute the stock launch request producer.
  x,y,z=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)];ret=0
  if a==0xc2c1268:
   pkg=self.s(x);assert y==0,'optional URI was not NULL';self.lookups.append(pkg)
   assert pkg in dict(APPS).values();ret=self.info if self.available else 0
  elif a==0xc44e76c:assert self.s(x)==b'com.test.alpha' and y==24
  elif a==0xc44a850:
   payload=bytes(u.mem_read(x,44));assert int.from_bytes(payload[16:20],'little')==0x12345678
   self.launches.append(payload)
  else:return super().hook(u,a,n,ud)
  u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))

def content(b,root):return next(k for k,v in b.objects.items() if k not in b.deleted and v['parent']==root and v['w']==336 and v['h']==424)
def rows(b):return [k for k,v in b.objects.items() if k not in b.deleted and v.get('native')=='row']

for base in (0x1d100000,0x1d340000,0x1c900000):
 b=LaunchBand(base);b.start();root=b.create(1);c=content(b,root)
 assert len(rows(b))==6,'first paint should be four actions and only two application rows'
 b.drive();assert len(rows(b))==10 and c not in b.deleted
 b.click_and_drive(6);b.create(29);b.click_and_drive(5);assert 100 not in b.shown
 before=b.files[am.POLICY];order=b.ordered.copy();b.click(8);assert not b.launches
 b.drive();assert len(b.launches)==1 and 100 not in b.shown and b.ordered==order and b.files[am.POLICY]==before
 b.available=False;b.click_and_drive(8);assert len(b.launches)==1 and 100 not in b.shown
 b.create(1);b.click_and_drive(5);root=b.create(30);c=content(b,root);deleted=set(b.deleted)
 b.click_and_drive(7);assert c not in b.deleted and b.deleted==deleted,'single selection rebuilt native object tree'
 b.click_and_drive(0);b.click_and_drive(0);assert b.deleted==deleted,'select-all rebuilt native object tree'
 b.click_and_drive(3);b.drive();assert c not in b.deleted
 print(f'PASS app upgrade {base:x}: two-row first paint, deferred fill, in-place selection/select-all/batch, real launch producer pkg+NULL, hidden policy/order unchanged, unavailable launch rejected')

old_apps,old_order=am.APPS,am.ORDER
try:
 for count in (192,193):
  am.APPS=[(100+i,('com.capacity.app%03d'%i).encode()) for i in range(count)];am.ORDER=[i for i,_ in am.APPS]
  b=AppBand(0x1d100000);b.start();b.create(1);b.drive()
  if count==192:
   seen=set()
   for page in range(32):
    texts=b.live_text()
    for _,pkg in am.APPS:
     if any(t.endswith(pkg) for t in texts):seen.add(pkg)
    if page<31:b.click_and_drive(4);b.drive()
   assert len(seen)==192,len(seen)
  else:
   assert any('超过192'.encode() in t for t in b.live_text())
   b.click_and_drive(0);assert not b.hide_calls,'overflow list allowed a bulk mutation'
 # A realistic mixed registry must still leave all system apps visible after hiding 64 user apps.
 am.APPS=[(i,('com.native.%02d'%i).encode()) for i in range(1,81)]+[(100+i,('com.user.%02d'%i).encode()) for i in range(64)]
 am.ORDER=[i for i,_ in am.APPS]
 b=AppBand(0x1d100000);b.start();b.create(1);b.click_and_drive(5);b.create(30);b.click_and_drive(0);b.click_and_drive(2)
 for _ in range(28):b.drive()
 assert b.shown==set(range(1,81));b.check_order()
 assert int.from_bytes(b.files[am.POLICY][4:6],'little')==64
 print('PASS mixed capacity: 80 native + 64 user apps, batch hides all 64 user apps, all native apps protected and ordering retained')
 print('PASS capacity: all 192 packages accessible, 193rd visible registry node gives explicit overflow and blocks mutations')
finally:am.APPS,am.ORDER=old_apps,old_order

# Exercise the compiled ARM metadata parser through application details at 64 KiB.
# A maximum-size metadata file needs a larger instruction budget than small UI fixtures.
class LargeMetadataBand(AppBand):
 def hook(self,u,a,n,ud):
  if a==0xc0f0790:u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  return super().hook(u,a,n,ud)
 def call(self,name,*args):
  fn=self.base+META['functions'][name] if name in META['functions'] else self.symbol(name)
  self.u.reg_write(UC_ARM_REG_SP,0x200ff000);self.u.reg_write(UC_ARM_REG_LR,0x100001)
  for reg,v in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):self.u.reg_write(reg,v)
  self.u.emu_start(fn|1,0,count=30000000)
  assert self.u.reg_read(UC_ARM_REG_PC)==0x100000,'metadata instruction budget exceeded'
  return self.u.reg_read(UC_ARM_REG_R0)
for size in (65536,65537):
 b=LargeMetadataBand(0x1d100000);b.start()
 head=b'{"package":"com.test.alpha","name":"Capacity Name","versionName":"9.0","padding":"'
 b.files[b'/data/quickapp/apps.json']=head+b'x'*(size-len(head)-2)+b'"}'
 b.create(1);b.click_and_drive(6);b.create(29)
 assert (b'Capacity Name' in b.live_text())==(size==65536)
 assert len(b.files[b'/data/quickapp/apps.json'])==size
print('PASS 64-KiB metadata boundary: exact limit accepted, over-limit rejected, source JSON never rewritten')
