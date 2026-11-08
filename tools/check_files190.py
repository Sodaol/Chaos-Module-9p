"""Execute the linked file engine ARM; hardware/OS/LVGL calls are mocked."""
import json,struct
from pathlib import Path
from test_n67 import Band
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[1]
mapping={int(v,16)&~1:int(k,16)&~1 for k,v in json.loads((R/'n67/generated/file-engine-3.1.190.json').read_text())['mappings'].items() if int(k,16)<0x10000000}
mapping[0xc46a00a]=0xc465788
mapping[0xc43da64]=0xc2401c4 # Native button creation is an explicit LVGL double here.
class FilesBand(Band):
 def __init__(self,base):
  self.jobs=[];self.now=0;self.scroll={};self.bound=[]
  super().__init__(base)
  self.w32(0x200bfc6c,self.fm)
 def hook(self,u,a,n,ud):
  regs=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
  x,y,z,w=[u.reg_read(r) for r in regs];ret=0
  self.bound.append(a)
  if a==0xc0bb094:u.mem_write(y,struct.pack('<qI',1792800000,0))
  elif a==0xc0f12d4:u.mem_write(y,struct.pack('<11i',0,30,12,24,9,126,6,296,0,0,0));ret=y
  elif a==0xc37e1f4:
   off=struct.unpack('<q',struct.pack('<II',z,w))[0];whence=self.r32(u.reg_read(UC_ARM_REG_SP));p,at=self.fds[x]
   at=off+(len(self.files[p]) if whence==2 else at if whence==1 else 0);self.fds[x][1]=max(0,at);ret=max(0,at);u.reg_write(UC_ARM_REG_R1,0)
  elif a==0xc0c00a2:
   self.jobs.append((x,w));ret=50+len(self.jobs)
  elif a==0xc1610b8:self.now+=50;ret=self.now
  elif a==0xc37fc38:
   path=self.s(x);u.mem_write(y,bytes(96))
   if path in self.files:self.w32(y+8,0x8000);self.w32(y+24,len(self.files[path]))
   elif path in self.dirs:self.w32(y+8,0x4000)
   else:ret=0xffffffff
  elif a==0xc23bd02:ret=self.scroll.get(x,0)
  elif a==0xc242ca0:self.scroll[x]=y
  elif a in [0xc23ea14,0xc239f2c]:
   if a==0xc239f2c:u.mem_write(y,bytes(4))
  elif a==0xc242840:
   assert x in self.objects and y in self.objects;self.objects[x]['parent']=y;self.w32(x+4,y)
  else:
   old=mapping.get(a)
   assert old is not None, f'unmapped file-engine firmware call {a:x}, LR={u.reg_read(UC_ARM_REG_LR):x}'
   return super().hook(u,old,n,ud)
  u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def ptrcall(self,fn,*args):
  self.sym['test_direct_call']=fn
  return self.call('test_direct_call',*args)
 def workers(self):
  while self.jobs:
   name,fn=self.jobs.pop(0);argv=self.alloc(8);self.w32(argv,name)
   assert self.ptrcall(fn,1,argv)==0
 def tick(self,t):
  self.ptrcall(self.r32(t+8),t);self.workers()

for base in [0x1d100000,0x1d340000,0x1c900000]:
 b=FilesBand(base);assert b.call('chaos_n67_init',0x3d800000,65536,131072,8192)==0x4e363743
 p=0x3d801000+13*112;root=b.alloc(0x100)
 b.objects[root]={'parent':0,'props':{},'label':False,'text':b'','w':336,'h':480,'x':0,'y':0}
 b.w32(p+0x2c,root)
 b.dirs[b'/data']=[(8,b'readme.txt'),(4,b'example')];b.dirs[b'/data/example']=[]
 b.files[b'/data/readme.txt']=b'Hello N67 3.1.190\n'
 b.call('chaos_files_open',0)
 assert b.call('chaos_files_create',p,root,0)==0
 ui=b.r32(p+4)
 for repeat in range(2):
  assert b.call('chaos_files_resume',p)==0
  assert b.r32(ui+0x7c)==100,'initial file UI must be complete before the first timer tick'
  assert b.objects[b.r32(ui+0x38)]['text']!=b'Text','default label leaked into initial paint'
  b.workers()
  if repeat==0:
   # Drop every callback from the independent file timer. Existing Chaos
   # heartbeat must still publish the completed directory worker result.
   for _ in range(60):b.call('chaos_files_poll')
  else:
   for _ in range(60):b.tick(next(t for t in b.timers if b.r32(t+8)==b.sym["bt_app_tick"]))
  assert b.r32(ui+0x7c)==100,f'file UI not built: {b.r32(ui+0x7c)}'
  labels={o['text'] for o in b.objects.values() if o.get('label')}
  assert any(b'readme.txt' in s for s in labels),'directory listing not rendered'
  assert any(b'/data' in s for s in labels),'directory heading not rendered'
  assert len(b.timers)==2,'expected one Rust maintenance timer and one file timer'
  assert b.call('chaos_files_pause',p)==0
 assert b.call('chaos_files_destroy',p)==0
 before=len(b.objects)
 for _ in range(3):b.tick(next(t for t in b.timers if b.r32(t+8)==b.sym["bt_app_tick"]));b.call('chaos_files_poll')
 assert len(b.objects)==before,'destroyed page created objects'
 assert root not in b.deleted,'file engine deleted firmware root'
 print(f'PASS file engine ARM at {base:08x}: synchronous initial paint, worker directory listing, dropped timer callback recovery, pause/resume, single timer, destroy safety; {len(set(b.bound))} mocked firmware entries')
