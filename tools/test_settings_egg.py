"""Five-tap native About entry and actual registrar suppression; separate build profile."""
from test_native_entries import NativeBand
from unicorn.arm_const import *
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];G=R/'n67/generated'
EGG=json.loads((R/'n67/manifest.json').read_text('utf8')).get('profile')=='settings-egg'
class EggBand(NativeBand):
 def hook(self,u,a,n,ud):
  if a==0xc1610b8:u.reg_write(UC_ARM_REG_R0,self.now);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  super().hook(u,a,n,ud)
 def about(self):
  page,root,content=self.native_page('关于本机',0x16001b)
  label=self.obj(content,label=True,cls=0x2c6834b0);p=self.alloc(16);self.u.mem_write(p,b'3.1.190\0');self.w32(label+36,p)
  self.w32(0x200cd0bc,label);self.sync(content);self.top=page;return page,root,content,label
 def tap(self,target,cb,code=7):
  e=self.alloc(24);self.w32(e,target);self.w32(e+4,target);self.w8(e+8,code);self.sym['egg_click']=cb;self.call('egg_click',e)
for base in (0x1d100000,0x1d340000,0x1c900000):
 b=EggBand(base);b.call('chaos_n67_init',0x3d800000,65536,131072,8192)
 b.goto=None; p,root,content,target=b.about();b.drive()
 hooks=[cb for o,cb,f,ctx in b.events if o==target and f==0]
 if not EGG:
  assert not hooks,'standard build unexpectedly enabled hidden entry';continue
 assert len(hooks)==1;cb=hooks[0];n=len(b.events);b.drive();assert len(b.events)==n
 for _ in range(4):b.now+=100;b.tap(target,cb)
 assert not b.goto
 b.now+=1300;b.tap(target,cb);assert not b.goto,'tap timeout failed'
 for _ in range(3):b.now+=100;b.tap(target,cb)
 assert not b.goto
 b.tap(target,cb);assert b.goto==(0xe7d40000,0)
 b.goto=None
 b.tap(target,cb);b.tap(target,cb)
 wrong,_,_=b.native_page('系统版本',0x160005);b.top=wrong;b.drive();b.top=p
 for _ in range(4):b.tap(target,cb)
 assert not b.goto,'page exit retained the previous tap count'
 b.tap(target,cb);assert b.goto==(0xe7d40000,0)
 b.tap(target,cb,35);b.goto=None
 for _ in range(6):b.tap(target,cb)
 assert not b.goto,'deleted native target retained its callback state'
 settings,_,sc=b.native_page('设置',0x160000);b.top=settings;b.drive();assert not b.rows(sc),'egg build exposed Settings button'
 b.create(15);assert not any('系统设置入口'.encode() in t or '应用列表显示'.encode() in t for t in b.live_text())
 # Execute the actual compiled bridge from its launcher_half stage. A launcher
 # API call is a hard failure, even if an old config requests launcher display.
 meta=json.loads((G/'bridge.json').read_text());code=(G/'bridge.bin').read_bytes();bridge=0x1d700000
 b.u.mem_map(bridge,(len(code)+4095)&~4095);b.u.mem_write(bridge,code)
 node=b.alloc(60);b.w32(node+16,0xe7d4)
 b.sym['reg_tick']=bridge+meta['functions']['bt_reg_tick']['offset']
 r=b.alloc(96);timer=b.alloc(24);b.w32(timer+12,r)
 for off,value in {0:0x52474554,4:2,8:2,16:0xc4467b5,24:0xc2a47a1,28:node,40:0xe7d4,56:0x200a3938}.items():b.w32(r+off,value)
 trampoline=0x1d7ff000;b.u.mem_map(trampoline,4096)
 b.u.mem_write(trampoline,b'\x00\x48\x70\x47'+node.to_bytes(4,'little'));b.w32(r+16,trampoline|1)
 b.call('reg_tick',timer)
 assert b.r32(r+4)==3 and b.r32(r+64)==0 and b.r32(r+72)==0
 print(f'PASS egg {base:08x}: five taps, timeout, page exit, deletion reset, no visible Settings/launcher option, native registrar succeeds without a desktop icon')
if not EGG:print('PASS standard profile: hidden About trigger is disabled')
