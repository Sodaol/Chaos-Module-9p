"""Actual ARM registrar recovery for N=0/P=0 with retained descriptors."""
from test_port_pages import PortBand
from pathlib import Path
import json
from unicorn.arm_const import *
class RecoveryBand(PortBand):
 def __init__(self,base):self.registrations=0;self.orphan=None;super().__init__(base)
 def hook(self,u,a,n,ud):
  if a==0xc4497cc:self.registrations+=1
  if a==0xc448748 and self.orphan==u.reg_read(UC_ARM_REG_R0):
   u.reg_write(UC_ARM_REG_R0,self.page(self.orphan&65535));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  return super().hook(u,a,n,ud)
 def setup(self):
  self.call('chaos_n67_init',0x3d800000,65536,131072,8192);self.registrar()
  meta=json.loads((Path(__file__).resolve().parents[1]/'n67/generated/bridge.json').read_text());self.sym['bt_install_health']=0x1d700000+meta['functions']['bt_install_health']['offset']
  self.u.mem_write(0x3d800280,b'com.chaos.manager\0');self.w32(0x3d800144,0x3d800001);self.w32(0x3d800140,0x3d800300)
  self.timer=self.alloc(24);self.w32(self.timer+12,0x3d8000f0)
 def detach(self):
  self.old=self.registered;self.registered=0;sent=self.r32(0x200a1dd0);self.w32(sent,sent);self.w32(sent+4,sent)
 def ticks(self,n=10):
  for _ in range(n):self.call('bt_reg_tick',self.timer)
for base in (0x1d100000,0x1d340000,0x1c900000):
 b=RecoveryBand(base);b.setup();b.detach();old=b.old;b.ticks()
 assert b.registered and b.registered!=old and b.registrations==2
 assert b.call('bt_install_health',0xc4467b5,0xe7d4)&31==31
 assert b.r32(old+0x10)&65535==0xe7d4,'fixture must retain detached E node as in device photo'
 # Three attempts during a reset storm, then stop; stable residency resets budget.
 for _ in range(2):b.detach();b.ticks()
 assert b.registrations==4
 b.detach();b.ticks(20);assert b.registered==0 and b.registrations==4
 print(f'PASS detached registrar ARM {base:x}: N=0/P=0/E intact, 31 descriptors revalidated and restored, current node replaced without stale-node reuse, native health recovered; bounded reset storm')
for fault in ('orphan','descriptor_id','callback','tag','package','occupied'):
 b=RecoveryBand(0x1d100000);b.setup();b.detach()
 if fault=='orphan':b.orphan=0xe7d40004
 if fault=='descriptor_id':b.w32(0x3d800010,0xe7d5)
 if fault=='callback':b.w32(b.page(3)+0x48,0)
 if fault=='tag':b.w32(0x3d800144,0x3d801001)
 if fault=='package':b.u.mem_write(0x3d800280,b'com.other.manager\0')
 if fault=='occupied':b.registered=b.alloc(60);b.w32(b.registered+0x10,0xe7d4)
 before=b.registrations;b.ticks(20);assert b.registrations==before,fault
print('PASS recovery guards: orphan subpage, altered ID/callback/package/tag, occupied app ID all prevent registration; no other app takeover')
b=RecoveryBand(0x1d100000);b.setup();b.detach();b.ticks();b.ticks(60);b.detach();b.ticks();assert b.registrations==3
print('PASS stable registry resets bounded recovery budget for later independent system refresh')

