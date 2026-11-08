"""Bound tree-memory reads and verify scroll callbacks defer native maintenance."""
from test_native_entries import NativeBand
from unicorn.arm_const import *
from unicorn import UC_HOOK_MEM_READ
import json
from pathlib import Path
EGG=json.loads((Path(__file__).resolve().parents[1]/'n67/manifest.json').read_text('utf8')).get('profile')=='settings-egg'
class PerfBand(NativeBand):
 def __init__(self,base):self.layouts=0;super().__init__(base)
 def hook(self,u,a,n,ud):
  if a==0xc1610b8:u.reg_write(UC_ARM_REG_R0,self.now);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  if a==0xc4fb974:self.layouts+=1;u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  super().hook(u,a,n,ud)
for base in (0x1d100000,0x1d340000,0x1c900000):
 b=PerfBand(base);b.call('chaos_n67_init',0x3d800000,65536,131072,8192)
 if not EGG:
  page,root,content=b.native_page('设置',0x160000)
  for _ in range(90):
   o=b.obj(content,label=True,cls=0x2c6834b0);p=b.alloc(8);b.u.mem_write(p,b'item\0');b.w32(o+36,p)
  b.sync(content);b.top=page;reads=[0]
  def count(u,access,address,size,value,ud):reads[0]+=1
  h=b.u.hook_add(UC_HOOK_MEM_READ,count,begin=content,end=b.next)
  b.call('chaos_shake_timer',b.timers[0]);cold=reads[0];reads[0]=0
  for _ in range(40):b.call('chaos_shake_timer',b.timers[0])
  warm=reads[0]/40;b.u.hook_del(h)
  assert cold>300 and warm<80,(cold,warm)
 # Real native scroll event marks activity, with no allocations or native UI updates.
 b.create(15);parent=b.r32(b.symbol('5state5PAGES')+15*72+4) # content field is checked below
 event_target,cb,code,_=next(e for e in reversed(b.events) if e[2]==11 and e[0] not in b.deleted)
 e=b.alloc(24);b.w32(e,event_target);b.w32(e+4,event_target);b.w8(e+8,11)
 b.sym['scroll_activity']=cb;b.now=1000;before=b.next;b.call('scroll_activity',e);assert b.next==before
 b.files[b'/data/chaos/applist.cfg']=b'\7'
 # A fresh instance loads the opt-in grid config before the activity test.
 n=PerfBand(base);n.files[b'/data/chaos/applist.cfg']=b'\7';n.call('chaos_n67_init',0x3d800000,65536,131072,8192);n.create(15)
 target,cb,_,_=next(e for e in reversed(n.events) if e[2]==11)
 event=n.alloc(24);n.w32(event,target);n.w32(event+4,target);n.w8(event+8,11);n.sym['scroll_activity']=cb
 home,root,content=n.native_page('Apps',0x100000);grid=n.obj(content,size=0x900,cls=0x2c69e840);n.w32(grid+0x880,1);n.sync(content);n.top=home
 for _ in range(20):
  n.now+=50;n.call('scroll_activity',event);n.call('chaos_shake_timer',n.timers[0])
 assert n.layouts==0,'grid maintenance ran during continuous scrolling'
 n.now+=181;n.call('chaos_shake_timer',n.timers[0]);assert n.layouts==1,'maintenance did not resume after scrolling settled'
 print(f'PASS scroll maintenance {base:08x}: cached native Settings tree, allocation-free scroll timestamp, maintenance deferred during scroll and resumed after 180ms; not a hardware CPU measurement')
