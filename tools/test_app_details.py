"""Run the relocated v1.1.0 pages. GUI/FS/native uninstall are explicit doubles.
Native launcher list instructions remain real firmware, as in test_app_manager.
"""
from test_app_manager import AppBand,APPS,ALL,POLICY
from unicorn.arm_const import *
import json
class DetailBand(AppBand):
 def __init__(self,base):
  self.uninstall_requests=[];self.pending={};self.refuse=False;self.uninstall_done=[]
  super().__init__(base)
 def hook(self,u,a,n,ud):
  x=u.reg_read(UC_ARM_REG_R0)
  if a==0xc0f0790:ret=0
  elif a==0xc2c0140:
   pkg=self.s(x);ident=next((i for i,p in APPS if p==pkg),None);ret=self.app_nodes.get(ident,0)
  elif a==0xc4b5190:
   pkg=self.s(x);ident=next((i for i,p in APPS if p==pkg),None)
   assert ident is not None and ident>0x51 and ident!=0xe7d4,'protected package reached uninstall API'
   self.uninstall_requests.append(pkg)
   if not self.refuse:self.pending[pkg]=ident
   ret=0
  else:return super().hook(u,a,n,ud)
  u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def complete_uninstalls(self):
  for pkg,ident in list(self.pending.items()):
   node=self.app_nodes.pop(ident)
   prev,nxt=self.r32(node),self.r32(node+4);self.w32(prev+4,nxt);self.w32(nxt,prev)
   for head in (0x200a3938,0x200a4034):
    for p in self.chain(head):
     same=(self.r32(p)&65535)==ident if head==0x200a3938 else self.s(p)==pkg
     if same:
      link=self.r32(head);pr,nx=self.r32(p+link),self.r32(p+link+4)
      if pr:self.w32(pr+link+4,nx)
      else:self.w32(head+4,nx)
      if nx:self.w32(nx+link,pr)
      else:self.w32(head+8,pr)
   self.uninstall_done.append(pkg);del self.pending[pkg]
 def page_action(self,row):self.click_and_drive(row)

def text(b):return b'\n'.join(b.live_text())
for base in (0x1d100000,0x1d340000,0x1c900000):
 b=DetailBand(base);b.start()
 registry=b'{"custom":17,"InstalledApps":[{"package":"com.test.alpha","name":"Alpha user","versionName":"7.2"}],"order":["com.test.beta","com.test.alpha"]}'
 b.files[b'/data/quickapp/apps.json']=registry
 b.dirs[b'/data/app/com.test.alpha']=[(8,('f%03d'%i).encode()) for i in range(100)]
 for i in range(100):b.files[('/data/app/com.test.alpha/f%03d'%i).encode()]=b'x'*13
 b.create(1);b.page_action(6);assert b.goto==(0xe7d4001d,0)
 b.create(29);assert b'Alpha user' in text(b) and b'7.2' in text(b)
 b.drive();assert '计算中'.encode() in text(b),'size walk blocked the entire GUI tick'
 for _ in range(25):b.drive()
 assert '1300 字节'.encode() in text(b)
 assert b.files[b'/data/quickapp/apps.json']==registry
 b.page_action(5);assert 100 not in b.shown;b.check_order()
 b.page_action(5);assert 100 in b.shown;b.check_order()
 b.page_action(6);assert not b.uninstall_requests
 b.create(1);b.page_action(6);b.create(29)
 b.page_action(6);assert not b.uninstall_requests,'confirmation survived leaving details'
 b.page_action(6);assert b.uninstall_requests==[b'com.test.alpha']
 b.complete_uninstalls();b.drive();assert 100 not in b.app_nodes and 100 not in b.shown
 assert b.files[b'/data/quickapp/apps.json']==registry,'Chaos itself rewrote user registry'
 print(f'PASS details {base:x}: user registry name/version, chunked size, hide/show order, confirmation cancellation, native-only uninstall')

 b=DetailBand(base);b.start();b.create(1);b.page_action(5);assert b.goto==(0xe7d4001e,0);b.create(30)
 b.page_action(7) # alpha only
 b.page_action(2)
 for _ in range(8):b.drive()
 assert b.shown==ALL-{100};b.check_order()
 b.page_action(0) # clear
 b.page_action(0) # all eligible
 b.page_action(3)
 for _ in range(10):b.drive()
 assert b.shown==ALL;b.check_order()
 b.page_action(0);b.page_action(7);b.page_action(4)
 assert not b.uninstall_requests
 b.page_action(7);b.page_action(4);assert not b.uninstall_requests,'changing selection did not disarm deletion'
 b.page_action(7);b.page_action(4);assert not b.uninstall_requests
 b.page_action(4)
 for _ in range(3):b.drive()
 assert b.uninstall_requests==[b'com.test.alpha']
 b.complete_uninstalls()
 for _ in range(8):b.drive()
 assert b.shown==ALL-{100} and not b.pending
 assert not (set(b.uninstall_requests)&{p for i,p in APPS if i<=81})
 print(f'PASS selection {base:x}: stable package selection, select/clear, show/hide, two-click deletion, protected native apps')

# Firmware re-registration creates a fresh node: hidden policy must be replayed.
for base in (0x1d100000,0x1d340000,0x1c900000):
 b=DetailBand(base);b.start();b.create(1);b.app_action(6)
 for _ in range(140):b.call('chaos_shake_timer',b.timers[0])
 assert 100 not in b.shown
 old=b.app_nodes[100];fresh=b.alloc(60);b.u.mem_write(fresh,bytes(b.u.mem_read(old,60)))
 previous,following=b.r32(fresh),b.r32(fresh+4);b.w32(previous+4,fresh);b.w32(following,fresh)
 b.app_nodes[100]=fresh;b.w8(fresh+0x38,0xa0)
 b.sym['native_add']=0xc2a47a0;b.call('native_add',100)
 assert 100 in b.shown
 for _ in range(25):b.call('chaos_shake_timer',b.timers[0])
 assert 100 not in b.shown;b.check_order()
 print(f'PASS re-registration {base:x}: new registry node re-hidden by package, original order intact')
