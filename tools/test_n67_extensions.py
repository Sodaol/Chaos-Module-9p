"""Actual slid ARM image: N67 resource journal and linked file/terminal adapter.
Explicit mocked firmware is used; this does not constitute device acceptance.
"""
import json,struct
from pathlib import Path
from test_n67 import Band,IMAGE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[1]
RULES=json.loads((R/'n67/system-icon-mapping.json').read_text('utf-8'))
class Extended(Band):
 def __init__(self,base):
  super().__init__(base);self.jobs=[];self.clock=1
 def hook(self,u,a,n,ud):
  regs=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3];x,y,z,w=[u.reg_read(r) for r in regs]
  ret=0
  if a==0xc2607d8:
   # LVGL copies file paths and references image descriptors as is.
   if self.u.mem_read(y,1)[0] in (ord('/'),ord('S')):
    data=self.s(y)+b'\0';p=self.alloc(len(data));u.mem_write(p,data);y=p
   self.w32(x+36,y)
  elif a==0xc243188:
   self.events.append((x,y,z,w));spec=self.r32(x+8)
   if not spec:spec=self.alloc(32);self.w32(x+8,spec)
   count=self.u.mem_read(spec+26,1)[0]&63;old=self.r32(spec+12);arr=self.alloc((count+1)*12)
   if count:u.mem_write(arr,bytes(u.mem_read(old,count*12)))
   u.mem_write(arr+count*12,struct.pack('<III',y,w,z));self.w32(spec+12,arr);self.w8(spec+26,count+1);ret=arr+count*12
  elif a==0xc0c009e:
   assert y==80 and z==8192 and self.base<=w<self.base+len(IMAGE),'file worker ABI or slide'
   self.jobs.append((self.s(x),w));ret=200+len(self.jobs)
  elif a==0xc167544:self.clock+=50;ret=self.clock
  elif a==0xc37f834:
   p=self.s(x)
   if p in self.files:self.w32(y+8,0x8000|0o640);self.w32(y+24,len(self.files[p]))
   elif p in self.dirs:self.w32(y+8,0x4000|0o750)
   else:self.w32(0x20000000,2);ret=0xffffffff
  elif a==0xc258324:
   # Font glyph advance data, derived from the production callback ABI.
   u.mem_write(y,struct.pack('<HHHH',0,0,5 if z==105 else 16 if z==87 else 10 if z<128 else 18,0));ret=1
  elif a in (0xc23b968,0xc23ea5c,0xc242da4,0xc23f418):ret=0
  elif a==0xc25c3a0:
   ret=self.alloc(0x100);self.w32(ret,0x2c68260c);self.w32(ret+4,x)
   self.objects[ret]={'parent':x,'props':{},'label':False,'text':b'','w':100,'h':100,'x':0,'y':0}
  else:return super().hook(u,a,n,ud)
  self.calls.append(a);u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def obj(self,parent=0,image=False):
  p=self.alloc(0x100);self.w32(p,0x2c68260c if image else 0x2c67d7bc);self.w32(p+4,parent)
  self.objects[p]={'parent':parent,'props':{},'label':False,'text':b'','w':336,'h':480,'x':0,'y':0}
  self.w32(p+8,self.alloc(32));return p
 def children(self,p,children):
  spec=self.r32(p+8);arr=self.alloc(len(children)*4)
  for i,ch in enumerate(children):self.w32(arr+i*4,ch)
  self.w32(spec,arr);self.w32(spec+4,len(children))
 def resource(self,parent,row):
  p=self.obj(parent,True);src=self.alloc(len(row['path'])+1);self.u.mem_write(src,row['path'].encode()+b'\0');self.w32(p+36,src)
  self.u.mem_write(p+44,struct.pack('<HH',row['width'],row['height']));return p
 def worker(self,index=0):
  name,cb=self.jobs.pop(index);p=self.alloc(len(name)+1);self.u.mem_write(p,name+b'\0');argv=self.alloc(4);self.w32(argv,p)
  key='bt_app_worker' if name[-1:]!=b't' else 'bt_term_worker'
  assert self.call(key,1,argv)==0
 def set_pack(self,p):self.w32(self.symbol('10icon_apply7IC_PACK'),p)
 def event(self,o,code):
  p=self.alloc(16);self.w32(p,o);self.w32(p+4,o);self.w8(p+8,code);self.call('chaos_n67_resource_event',p)

def resources(base):
 b=Extended(base);b.call('chaos_n67_init',0x3d800000,32768,16384,8192);b.screen=b.obj()
 objects=[b.resource(b.screen,r) for r in RULES];b.children(b.screen,objects)
 old=[b.s(b.r32(o+36)) for o in objects]
 for r in RULES:
  w,h=r['width'],r['height'];b.files[('/data/chaos/icons/01/'+r['stem']+'.bin').encode()]=struct.pack('<I',5|(w<<10)|(h<<21))+b'\xAA\xCC\x11\xFF'*(w*h)
 # Corrupt/missing resources never publish a partial image.
 bad=RULES[-1];b.files[('/data/chaos/icons/01/'+bad['stem']+'.bin').encode()]=b'bad'
 b.read_limit=17;b.set_pack(1)
 for _ in range(len(RULES)+2):b.call('chaos_n67_resources_tick')
 for o,r,path in zip(objects,RULES,old):
  src=b.r32(o+36)
  if r is bad:assert b.s(src)==path;continue
  assert b.r32(src)==5|(r['width']<<10)|(r['height']<<21)
  assert b.r32(src+4)==r['width']*r['height']*4
 before=b.calls.count(0xc380398)
 for o in objects:b.event(o,21)
 assert b.calls.count(0xc380398)==before,'IO occurred in DRAW_MAIN_BEGIN'
 b.set_pack(2);b.call('chaos_n67_resources_tick')
 assert [b.s(b.r32(o+36)) for o in objects]==old,'missing next pack did not restore exact paths'
 b.set_pack(1)
 for _ in range(len(RULES)+2):b.call('chaos_n67_resources_tick')
 journal=b.symbol('7JOURNAL');b.event(objects[0],35)
 assert all(b.r32(journal+i*172)!=objects[0] for i in range(128)),'DELETE retained stale object'
 # The firmware removes deleted objects from the live tree; never walk the
 # destroyed mock object as if it were still a valid visible image.
 b.children(b.screen,objects[1:])
 b.set_pack(0);b.call('chaos_n67_resources_tick')
 assert [b.s(b.r32(o+36)) for o in objects[1:]]==old[1:]
 print(f'PASS {base:x} resource ARM: 54 verified paths/dimensions, short reads, corrupt/missing fallback, no draw IO, pack switching, restore, DELETE')

def files(base):
 b=Extended(base);b.call('chaos_n67_init',0x3d800000,32768,16384,8192);p=b.page(14)
 for off in (0x30,0x48,0x4c,0x54,0x60):assert base<=b.r32(p+off)<base+len(IMAGE)
 root=b.obj();b.w32(p+44,root);b.dirs[b'/data']=[(8,b'demo.txt')];b.files[b'/data/demo.txt']=b'hello\n'
 assert b.call('chaos_files_create',p,root,0)==0
 ui=b.r32(p+4);state=b.r32(ui+132);assert b.r32(state)==0x314d464e
 assert b.r32(state+44)==32768 and b.r32(state+48)==8192
 assert b.r32(state+156)==12 and b.r32(state+204)==9 and b.r32(state+208)==64,'actual firmware gesture/scroll constants'
 for off in (8,16,24,28):assert base<=b.r32(state+off)<base+len(IMAGE),'slid C function binding'
 b.call('chaos_files_resume',p);assert len(b.jobs)==1;b.worker()
 timer=b.timers[-1]
 for _ in range(50):b.call('bt_app_tick',timer)
 assert b.r32(ui+124)==100 and root not in b.deleted,'complete native GUI build'
 assert any(v['text'].startswith('上一级目录'.encode()) for v in b.objects.values()),'parent row'
 b.call('chaos_files_pause',p);b.call('chaos_files_destroy',p)
 assert b.r32(ui+52)==0,'destroy left stale root'
 b.call('bt_app_tick',timer);assert b.u.mem_read(timer+20,1)[0]&1,'idle file timer not paused'
 # Terminal entry queues a real FIFO/session worker through the same state.
 b.call('chaos_files_open',1);root=b.obj();b.w32(p+44,root);b.call('chaos_files_create',p,root,0);b.call('chaos_files_resume',p)
 assert b.r32(state+224)==5,'terminal mode did not select V_TERM'
 b.call('bt_app_tick',timer);assert b.jobs,'terminal did not request FIFO job'
 print(f'PASS {base:x} linked file ARM: C callback slides, resident ABI, genuine Lua flags/events, worker handoff, complete UI/parent row, pause/destroy cleanup, terminal entry')
if __name__=='__main__':
 for base in (0x1d100000,0x1d340000,0x1c900000):resources(base);files(base)
