"""Real relocated event callback/UI switch/rotation, native event transport mocked."""
from test_native_entries import NativeBand
from unicorn.arm_const import *
TOPIC=0x2c67c708
class ShakeBand(NativeBand):
 def __init__(self,base,fail=False):
  self.subscriptions=[];self.fail_subscription=fail;self.switches=[];self.refreshes=[];self.nodes={};self.manager=0;self.direct=[];self.source_opens=0;self.source_closes=0;super().__init__(base)
 def hook(self,u,a,n,ud):
  x,y,z,w=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
  if a==0xc104b9c:
   if x==0x2c5eba9c:ret=0xffffffff
   else:assert x==TOPIC;self.source_opens+=1;ret=99
  elif a==0xc37f458 and x==99:
   assert z==16
   if self.direct:u.mem_write(y,self.direct.pop(0));ret=16
   else:ret=0xffffffff
  elif a==0xc37dba4 and x==99:self.source_closes+=1;ret=0
  elif a==0xc46a00a:
   assert x==TOPIC and self.s(self.r32(x))==b'quick_guesture' and self.r32(x+4)==16
   self.subscriptions.append(z);ret=0 if self.fail_subscription else self.alloc(32)
  elif a==0xc453b90:
   face=self.s(x);assert face in self.nodes;self.switches.append(face);self.w32(self.manager+0x44,self.nodes[face]);ret=0
  elif a==0xc30b8bc:
   assert x==1;node=self.r32(self.manager+0x44);self.refreshes.append(node);self.w32(0x200cea1c,node);ret=0
  else:return super().hook(u,a,n,ud)
  u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def toggle(self):
  row=self.r32(self.symbol('5state5PAGES')+10*72);control=self.r32(row+0x60)
  cb=next(cb for obj,cb,code,ctx in self.events if obj==control)
  e=self.alloc(24);self.w32(e,control);self.w32(e+4,control);self.w8(e+8,29)
  self.sym['shake_switch']=cb;self.call('shake_switch',e);self.drive()
 def setup(self):
  self.manager=self.alloc(0x100);self.w32(0x200cacd0,self.manager);last=0;first=0
  for i,name in enumerate([b'111111111111',b'222222222222']):
   node=self.alloc(0xc0);self.nodes[name]=node;self.u.mem_write(node+8,name+b'\0');self.u.mem_write(node+0x48,b'Face\0');self.w8(node+0x88,1)
   if last:self.w32(last+4,node)
   else:first=node
   self.w32(node,last);last=node
  self.w32(last+4,self.manager+0x70);self.w32(self.manager+0x74,first);self.w32(self.manager+0x44,first);self.w32(0x200cea1c,first)
  self.w8(self.manager+0x6d,1);self.w8(self.manager+0x6c,0)
 def emit(self,code=0x1c2,topic=TOPIC,length=16,sram=False):
  event=self.alloc(32);payload=0x200ef000 if sram else self.alloc(16)
  self.w32(event+4,topic);self.w32(event+0x18,payload);self.w32(event+0x1c,length);self.u.mem_write(payload+8,code.to_bytes(2,'little'))
  self.call('chaos_shake_cb',event,0)
 def get(self,name):return self.r32(self.symbol(name))
for base in (0x1d100000,0x1d340000,0x1c900000):
 b=ShakeBand(base);assert b.r32(0xc368148)==TOPIC,'topic must match actual native system subscriber literal'
 b.call('chaos_n67_init',0x3d800000,65536,131072,8192);b.setup();b.create(10)
 assert b.get('8SHAKE_EN')==0
 row=b.r32(b.symbol('5state5PAGES')+10*72);assert not b.objects[b.r32(row+0x60)]['selected'],'disabled runtime falsely displayed enabled'
 b.toggle();assert b.get('8SHAKE_EN')==1 and len(b.subscriptions)==1 and len(b.timers)==1
 home,root,content=b.native_page('Home',0x100000);b.call('chaos_on_pause',b.page(10));b.top=home
 for kwargs in [dict(code=0x1c3),dict(topic=0x2c67d0a4),dict(length=9)]:b.emit(**kwargs);assert b.get('13SHAKE_PENDING')==0
 b.emit();assert b.get('13SHAKE_PENDING')==1 and not b.switches,'callback must only enqueue'
 b.drive();assert b.switches==[b'222222222222'] and len(b.refreshes)==1
 b.emit();assert b.get('13SHAKE_PENDING')==0,'cooldown queued a delayed extra switch'
 for _ in range(10):b.drive()
 assert len(b.switches)==1
 b.emit();b.w8(0x200ca360+0x19,1);b.drive();assert len(b.switches)==1 and not b.get('13SHAKE_PENDING');b.w8(0x200ca360+0x19,2)
 b.w8(b.manager+0x6d,0);b.emit();assert not b.get('13SHAKE_PENDING');b.w8(b.manager+0x6d,1)
 b.w8(b.manager+0x6c,1);b.emit();assert not b.get('13SHAKE_PENDING');b.w8(b.manager+0x6c,0)
 settings,_,_=b.native_page('设置',0x160000);b.top=settings;b.emit();assert not b.get('13SHAKE_PENDING')
 b.top=home;b.w32(b.symbol('7FG_PAGE'),9);b.emit(sram=True);b.drive();assert b.switches[-1]==b'111111111111' and len(b.switches)==2
 for _ in range(10):b.drive()
 b.w32(b.symbol('12WF_DESEL_CNT'),1);b.w32(b.symbol('8WF_DESEL'),b.nodes[b'222222222222'])
 b.emit();b.drive();assert len(b.switches)==2,'only current eligible face must not reload itself'
 b.w32(b.symbol('12WF_DESEL_CNT'),0)
 for _ in range(10):b.drive()
 b.direct.append(bytes(8)+(0x1c2).to_bytes(2,'little')+bytes(6));b.top=home;b.drive()
 assert len(b.switches)==3 and b.source_opens==1,'direct native source must rotate without broker callback'
 b.create(10);b.drive()
 status=b.r32(b.symbol('5state5PAGES')+10*72+3*4);sub=b.r32(status+0x54)
 assert '事件：'.encode() in b.objects[sub]['text'] and '可见阻挡：2'.encode() in b.objects[sub]['text']
 assert '切换：3'.encode() in b.objects[sub]['text'],'diagnostic counter does not match actual refreshes'
 assert '直读：1'.encode() in b.objects[sub]['text']
 b.toggle();assert b.source_closes==1
 b.click_and_drive(4)
 status=b.r32(b.symbol('5state5PAGES')+10*72+3*4);sub=b.r32(status+0x54)
 assert '事件：0'.encode() in b.objects[sub]['text'] and '切换：0'.encode() in b.objects[sub]['text']
 failed=ShakeBand(base,True);failed.call('chaos_n67_init',0x3d800000,65536,131072,8192);failed.create(10);failed.toggle()
 assert any('订阅失败'.encode() in t for t,ms in failed.toasts)
 failed.fail_subscription=False;failed.toggle();failed.toggle();assert failed.get('9SHAKE_SUB')!=0 and len(failed.timers)==1
 print(f'PASS shake {base:08x}: actual N67 metadata/payload, native toggle, deferred two-face rotation, cooldown, screen/page/visibility/AOD gates, SRAM payload, subscription retry and single timer')
