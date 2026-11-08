"""Actual ARM native setter path: environment, persistence, resource refresh and event."""
from test_port_pages import PortBand
from unicorn.arm_const import *
class LanguageBand(PortBand):
 def __init__(self,base):self.env=b'zh_CN';self.actions=[];self.support=True;self.accept=True;super().__init__(base)
 def hook(self,u,a,n,ud):
  x,y,z=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)];ret=0
  if 0xc4ab7f4<=a<0xc4ab874 or 0xc368620<=a<0xc368654:return
  if a==0xc0be244:
   assert self.s(x)==b'LANG';ret=self.alloc(len(self.env)+1);u.mem_write(ret,self.env+b'\0')
  elif a==0xc36a1cc:ret=x if self.support else 0
  elif a==0xc0e6590:ret=0 if self.s(x)==self.s(y) else 1
  elif a==0xc4df08c:
   assert self.s(x)==b'LANG';self.actions.append(('environment',self.s(y)))
   if self.accept:self.env=self.s(y)
  elif a==0xc497d3a:assert self.s(x)==b'persist.locale';self.actions.append(('persist',self.s(y)))
  elif a==0xc3686b0:self.actions.append(('resources',self.s(x)))
  elif a==0xc241c88:self.actions.append(('images',))
  elif a in (0xc434314,0xc436c90):assert self.s(x)==b'/data/cache/';self.actions.append(('native_cache',a))
  elif a==0xc43466c:self.actions.append(('event',x,y,z))
  elif a==0xc0eb0e8:pass
  else:return super().hook(u,a,n,ud)
  u.reg_write(UC_ARM_REG_R0,ret&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def start(self):self.call('chaos_n67_init',0x3d800000,65536,131072,8192)
for base in (0x1d100000,0x1d340000,0x1c900000):
 b=LanguageBand(base);b.start();b.create(15);b.click(1);assert b.goto==(0xe7d4001f,0)
 for slot,code in ((1,b'zh_TW'),(2,b'en_US'),(0,b'zh_CN')):
  b.create(31);b.actions=[];b.click(slot);assert not b.actions,'event callback called native setter'
  b.drive();assert b.env==code and ('persist',code) in b.actions and ('resources',code) in b.actions and ('event',3,0,1) in b.actions
 b.create(31);b.actions=[];b.click(0);b.drive();assert not b.actions,'same language needlessly rewrote system state'
 b.support=False;b.click(1);b.drive();assert not b.actions and b.env==b'zh_CN'
 assert any('不支持'.encode() in t for t,_ in b.toasts)
 print(f'PASS language ARM {base:x}: Settings navigation, all three choices, deferred stock setter instructions update LANG+persist.locale+resources+system event; same choice no-op, unsupported choice blocked')
b=LanguageBand(0x1d100000);b.start();b.accept=False;b.create(31);b.click(1);b.drive();assert any('未接受'.encode() in t for t,_ in b.toasts)
print('PASS system-language readback failure reports rejection, not false success')
