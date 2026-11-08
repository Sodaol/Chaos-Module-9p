"""Actual relocated ARM UI logic; OS/LVGL/font/clock calls are test doubles, not a device test."""
import json,struct
from pathlib import Path
from test_n67 import Band,IMAGE
from page_layout import PAGE_COUNT
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[1]
mapping={int(v,16)&~1:int(k,16)&~1 for k,v in json.loads((R/'tools/fixtures/file-engine-3.1.190.json').read_text())['mappings'].items() if int(k,16)<0x10000000}
mapping.update({0xc23c880:0xc23d7e0,0xc242784:0xc23f508,0xc46a00a:0xc465788,0xc44a5ac:0xc44bbf8,0xc2665f0:0xc267784,0xc239b68:0xc23afd0,0xc239c18:0xc23b080,0xc239c54:0xc23b0bc,0xc44a5c4:0xc440be4,0xc4490b8:0xc44ae64,0xc241c88:0xc243ca4})
class UiBand(Band):
 def __init__(self,base):
  self.now=0;self.pickers={};self.vibrations=[];self.toasts=[]
  super().__init__(base)
  self.w32(0x200bfc6c,self.fm);self.w8(0x200ca360+0x19,2);self.w32(0x200ca360+0x10,300)
 def obj(self,parent,label=False,size=0x100,cls=0):
  o=self.alloc(size);self.w32(o,cls);self.w32(o+4,parent)
  self.objects[o]={'parent':parent,'props':{},'label':label,'text':b'','w':100,'h':28,'x':0,'y':0};return o
 def hook(self,u,a,n,ud):
  x,y,z,w=[u.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];ret=0
  if a==0xc104b9c:ret=0xffffffff
  elif a==0xc2702b4:
   ret=self.obj(x,size=0x100,cls=0x2c68da78);self.objects[ret].update(w=304,h=112,native='row');self.objects[ret]['props'][0x21]=255;self.w8(ret+0x71,1)
  elif a==0xc275ad4:
   self.objects[x]["leading_icon"]=self.s(y) if y else b""
   sel,tr=struct.unpack('<2I',u.mem_read(u.reg_read(UC_ARM_REG_SP)+4,8))
   if y:self.w32(x+0x48,self.obj(x,cls=0x2c69c2e4))
   frame=self.obj(x);self.w32(x+0x38,frame)
   body=self.obj(x);self.w32(x+0x4c,body)
   for off,text in ((0x50,z),(0x54,w)):
    if text:
     label=self.obj(body,True);self.objects[label]['text']=self.s(text);self.w32(x+off,label)
   if tr:
    control=self.obj(x,cls=0x2c68daf8 if tr==1 else 0x2c68dad8);self.w32(x+0x60,control)
    self.objects[control]['native']='switch' if tr==1 else 'check';self.objects[control]['selected']=bool(sel)
   self.objects[x]['trailing']=tr;ret=x
  elif a==0xc276ae4:
   for off,text in ((0x50,z),(0x54,w)):
    if text and self.r32(x+off):self.objects[self.r32(x+off)]['text']=self.s(text)
   ctrl=self.r32(x+0x60)
   if ctrl:self.objects[ctrl]['selected']=bool(self.r32(u.reg_read(UC_ARM_REG_SP)+4)&255)
  elif a==0xc275500:
   ret=self.obj(x,size=0x100);self.objects[ret].update(w=336,h=56,native='title')
   label=self.obj(ret,True);self.objects[label]['text']=self.s(y);self.w32(ret+0x28,label)
   clock=self.obj(ret,True);self.objects[clock]['text']=b'12:30';self.w32(ret+0x30,clock)
   if z:
    back=self.obj(ret);self.events.append((back,w or 0xc26f6d9,7,self.r32(u.reg_read(UC_ARM_REG_SP))))
  elif a==0xc23ef90:
   assert x==0x2c683310;ret=self.obj(y,size=0x100,cls=x);self.objects[ret]['native']='bar'
  elif a==0xc23e908:pass
  elif a==0xc25bc38:
   assert self.r32(x)==0x2c683310;self.objects[x]['value']=y
  elif a==0xc271d6c:
   assert self.r32(y+0x2c)==x;ret=self.obj(x,size=0x100);self.objects[ret].update(w=336,h=480,native='dialog')
  elif a==0xc274f60:
   assert y==5
   text=self.obj(x,True);self.objects[text]['text']=self.s(w)
   table=self.r32(u.reg_read(UC_ARM_REG_SP)+4);count=self.r32(u.reg_read(UC_ARM_REG_SP)+8)
   for i in range(count):
    button=self.obj(x,cls=0x2c68da18);self.objects[button]['native']='button'
    self.events.append((button,self.r32(table+i*20),7,0))
  elif a==0xc43da64:
   ret=self.obj(x,size=0x100,cls=0x2c68da18);self.objects[ret]['native']='button'
  elif a==0xc25eba0:ret=self.obj(x,cls=0x2c68260c)
  elif a==0xc2617d8:self.w32(x+36,y)
  elif a==0xc4349d4:
   ret=self.obj(x,size=0x300,cls=0x2c6ed248);self.w8(ret+0x2db,1);self.pickers[ret]=(0,0)
  elif a==0xc434a54:
   assert x in self.pickers and w>0;count=(z-y)//w+1;total=count*5;arr=self.alloc(total*8)
   for i in range(total):
    t=str(y+(i%count)*w).encode()+b'\0';p=self.alloc(len(t));u.mem_write(p,t);self.w32(arr+i*8,p)
   self.w32(x+0x2d0,arr);u.mem_write(x+0x2d4,struct.pack('<hh',count,total))
   self.pickers[x]=(y,z)
  elif a==0xc373b20:ret=0
  elif a==0xc43ba44:
   count=struct.unpack('<h',u.mem_read(x+0x2d4,2))[0];index=struct.unpack('<h',u.mem_read(x+0x80,2))[0]%count
   ret=self.r32(self.r32(x+0x2d0)+index*8)
  elif a==0xc4349f0:
   count=struct.unpack('<h',u.mem_read(x+0x2d4,2))[0];u.mem_write(x+0x80,struct.pack('<h',y+2*count));self.w8(x+0xb5,0)
  elif a in [0xc258cfc,0xc25eba0]:ret=self.obj(x)
  elif a==0xc25ebbc:ret=self.obj(x,True,cls=0x2c6834b0)
  elif a==0xc0bb094:u.mem_write(y,struct.pack('<qI',1792800000,0))
  elif a in [0xc0f12d4,0xc0ee72c]:u.mem_write(y,struct.pack('<11i',0,30,12,24,9,126,6,296,0,0,0));ret=y
  elif a==0xc1610b8:self.now+=50;ret=self.now
  elif a==0xc37e1f4:
   off=struct.unpack('<q',struct.pack('<II',z,w))[0];whence=self.r32(u.reg_read(UC_ARM_REG_SP));p,at=self.fds[x]
   at=off+(len(self.files[p]) if whence==2 else at if whence==1 else 0);self.fds[x][1]=max(0,at);ret=max(0,at);u.reg_write(UC_ARM_REG_R1,0)
  elif a==0xc45dc68:self.vibrations.append(bytes(u.mem_read(x,12)))
  elif a==0xc23ea14:self.objects[x]['scroll_dir']=y
  elif a in [0xc23ef76,0xc2617d8,0xc43da96,0xc23b38a]:pass
  elif a==0xc25a288:
   ret=self.alloc(24);self.w32(ret,y);self.w32(ret+8,x);self.w32(ret+12,z);self.timers.append(ret)
  elif a==0xc23afe2:
   self.objects[x]['align']=y
   return super().hook(u,mapping[a],n,ud)
  elif a in (0xc23ba44,0xc23baba):
   old_flags=self.objects[x].get('flags',0)
   self.objects[x]['flags']=old_flags|y if a==0xc23ba44 else old_flags&~y
   return super().hook(u,mapping[a],n,ud)
  elif a==0xc36f064:self.toasts.append((self.s(x),y))
  elif a==0xc36ef10:self.toasts.append((self.s(w),y))
  elif a==0xc4f1f28:self.toasts.append((self.s(self.r32(x+20)),0))
  elif a==0xc2644d8:self.objects[x]['long_mode']=y
  elif a==0xc23913a:self.objects[x]['w']=y
  elif a in [0xc2a47a0,0xc2a47ec]:pass
  else:
   old=mapping.get(a)
   if old is None:raise AssertionError(f'unmocked .190 call {a:x}, page={getattr(self,"test_pid",-1)}, LR={u.reg_read(UC_ARM_REG_LR):x}')
   return super().hook(u,old,n,ud)
  u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def retire(self,pid,root):
  self.call('chaos_on_ui_destroy',self.page(pid));self.w32(self.page(pid)+0x2c,0)
  assert root not in self.deleted,'application deleted firmware root'
  def drop(p):
   self.deleted.add(p)
   for q,v in list(self.objects.items()):
    if v['parent']==p and q not in self.deleted:drop(q)
  drop(root)

if __name__=='__main__':
 for base in [0x1d100000,0x1d340000,0x1c900000]:
  b=UiBand(base);assert b.call('chaos_n67_init',0x3d800000,65536,131072,8192)==0x4e363743
  for pid in range(PAGE_COUNT):
   p=b.page(pid);assert b.r32(0x3d800800+pid*4)==p and b.r32(p+0x14)==0xe7d40000|pid
  for cycle in range(2):
   for pid in range(14):
    b.test_pid=pid;root=b.create(pid);pages=b.symbol('5state5PAGES')
    assert b.r32(pages+pid*72+68)==1,f'page {pid} failed render'
    b.call('chaos_shake_timer',b.timers[0]);b.call('chaos_on_pause');b.call('chaos_on_resume',b.page(pid))
    b.retire(pid,root);b.call('chaos_shake_timer',b.timers[0])
  assert len(b.timers)==1
  b.create(0);b.click(3);assert b.goto[0]==0xe7d4000e,'file-manager page restored'
  live=[v for k,v in b.objects.items() if k not in b.deleted]
  rows=[v for v in live if v.get('native')=='row' and not v.get('flags',0)&1]
  assert len(rows)>=5 and all(v['h']>=88 for v in rows)
  assert any(v.get('native')=='title' for v in live),'native title missing'
  assert any(v['text']==b'12:30' for v in live),'native header clock missing'
  b.create(8)
  assert any(v.get('native')=='switch' for k,v in b.objects.items() if k not in b.deleted),'native switch missing'
  print(f'PASS ARM {base:08x}: {PAGE_COUNT} page descriptors, 28 original Rust page lifecycles, file-manager route, native list rows, title/clock, native trailing switches; OS/LVGL/clock mocked')
