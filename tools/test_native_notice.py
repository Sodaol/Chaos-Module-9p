"""Execute actual ARM message producer; native notification service is a double."""
from test_notifications import ToastBand
from unicorn.arm_const import *
class NativeNoticeBand(ToastBand):
 def __init__(self,base):self.messages=[];self.missing=None;super().__init__(base)
 def hook(self,u,a,n,ud):
  if a==0xc4f1f28:
   p=u.reg_read(UC_ARM_REG_R0);v=[self.r32(p+i*4) for i in range(22)]
   assert v[:2]==[0x41484301,0x4e37534f] and v[20]==1
   assert self.s(v[3])==self.s(v[4])==b'Chaos'
   assert self.s(v[7])==b'/data/chaos/chaos_icon.bin' and self.s(v[8])==b'/data/chaos/chaos_settings_icon.bin'
   self.messages.append((v[2],self.s(v[5])))
  if a==0xc448748 and u.reg_read(UC_ARM_REG_R0)==self.missing:
   u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  return super().hook(u,a,n,ud)
for base in (0x1d100000,0x1d340000,0x1c900000):
 b=NativeNoticeBand(base);b.call('chaos_n67_init',0x3d800000,65536,131072,8192);b.registrar();b.missing=0xe7d40004
 for _ in range(10):b.drive()
 assert not b.messages
 b.missing=None
 for _ in range(15):b.drive()
 assert b.messages==[(1,'Chaos 已安装！'.encode())]
 for _ in range(15):b.drive()
 assert len(b.messages)==1
 b.clear_log();assert b.messages[-1][1]=='日志已清空'.encode() and b.messages[-1][0]>=2
 first=b.messages[-1][0];b.clear_log();assert b.messages[-1][0]>first
 assert 'chaos_notice_draw' not in b.sym
 print(f'PASS system incoming-message ARM {base:x}: app/title/body/large+small icon/reminder ABI, no toast/custom drawer, ready-only once install, operation message unique IDs and native insertion')
