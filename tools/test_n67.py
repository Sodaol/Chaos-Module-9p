"""Run the actual relocated ARM Rust image under Unicorn with explicit N67 API mocks.
Firmware calls/GUI/fonts are mocked: a pass is NOT a claim of hardware testing.
"""
import sys,json,struct,os
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
from pack_n67 import slide
R=Path(__file__).resolve().parents[1];G=R/'n67/generated'
META=json.loads((G/'chaos.json').read_text('utf-8'));IMAGE=(G/'chaos.bin').read_bytes()
class Band:
 def __init__(self,base):
  self.base=base;self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
  for a,n in [(base&~4095,(len(IMAGE)+8191)&~4095),(0x20000000,0x100000),(0x3d000000,0x1000000),(0xc080000,0x800000),(0x2c080000,0x800000),(0x100000,0x1000)]:self.u.mem_map(a,n)
  fw=Path(os.environ.get('CHAOS_FW',str(R.parent/'fw/data/ota/app/vela_ap.bin'))).read_bytes();self.u.mem_write(0xc080000,fw);self.u.mem_write(0x2c080000,fw)
  self.u.mem_write(base,bytes(slide(IMAGE,META,base)));self.u.mem_write(0x100000,b'\x00\xbe')
  self.next=0x3d010000;self.objects={};self.events=[];self.timers=[];self.files={};self.fds={};self.dirs={};self.calls=[];self.top=0;self.deleted=set()
  self.u.hook_add(UC_HOOK_CODE,self.hook,begin=0xc080000,end=0xc800000)
  self.u.hook_add(UC_HOOK_CODE,lambda uc,a,n,ud:uc.emu_stop(),begin=0x100000,end=0x100002)
  self.w8(0x200ca4e8+0x19,2);self.w32(0x200ca4e8+0x10,300)
  self.fm=self.alloc(0x300);self.w32(0x200bfc54,self.fm)
  for off,link in [(0,48),(12,32),(24,8)]:self.w32(self.fm+off,link)
  self.sym={}
  with (R/'supervisor/chaos-n67.elf').open('rb') as f:
   e=ELFFile(f)
   for s in e.get_section_by_name('.symtab').iter_symbols():
    if META['link_base']<=s['st_value']<META['link_base']+len(IMAGE):self.sym[s.name]=base+s['st_value']-META['link_base']
 def alloc(self,n):p=self.next;self.next+=(n+7)&~7;self.u.mem_write(p,bytes(n));return p
 def r32(self,p):return struct.unpack('<I',self.u.mem_read(p,4))[0]
 def w32(self,p,v):self.u.mem_write(p,struct.pack('<I',v&0xffffffff))
 def w8(self,p,v):self.u.mem_write(p,bytes([v]))
 def s(self,p):
  b=bytearray()
  for i in range(4096):
   c=self.u.mem_read(p+i,1)[0]
   if not c:return bytes(b)
   b.append(c)
  raise AssertionError('unterminated string')
 def symbol(self,part):
  a=[v for k,v in self.sym.items() if part in k];assert len(a)==1,(part,len(a));return a[0]
 def call(self,name,*args):
  fn=self.base+META['functions'][name] if name in META['functions'] else self.symbol(name)
  self.u.reg_write(UC_ARM_REG_SP,0x200ff000);self.u.reg_write(UC_ARM_REG_LR,0x100001)
  for reg,v in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):self.u.reg_write(reg,v)
  self.u.emu_start(fn|1,0,count=3000000)
  assert self.u.reg_read(UC_ARM_REG_PC)==0x100000,f'ARM call did not return: {name} PC={self.u.reg_read(UC_ARM_REG_PC):x}'
  return self.u.reg_read(UC_ARM_REG_R0)
 def list_add(self,head,node):
  link=self.r32(head);last=self.r32(head+8);self.w32(node+link,last);self.w32(node+link+4,0)
  if last:self.w32(last+link+4,node)
  else:self.w32(head+4,node)
  self.w32(head+8,node)
 def hook(self,u,a,n,ud):
  if 0xc43fa46<=a<0xc43fa6a:return # Execute the real N67 default-page helper.
  regs=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3];x,y,z,w=[u.reg_read(r) for r in regs];self.calls.append(a);ret=0
  if a in (0xc2401c4,0xc25c3bc):
   ret=self.alloc(0x100);self.w32(ret+4,x);self.objects[ret]={'parent':x,'props':{},'label':a==0xc25c3bc,'text':b'','w':100,'h':28,'x':0,'y':0}
  elif a==0xc2407b6:
   assert x in self.objects and x not in self.deleted,f'style stale object {x:x}'
   self.objects[x]['props'][y]=z
  elif a in (0xc23d26c,0xc23d2e2):assert x in self.objects
  elif a==0xc24087a:self.objects[x].update(w=y,h=z)
  elif a==0xc240806:self.objects[x]['w']=y
  elif a==0xc23b77e:
   self.objects[x].update(x=z,y=w);p=self.objects[x]['parent'];py=self.objects.get(p,{}).get('y',0)
   u.mem_write(x+0x14,struct.pack('<hhhh',z&32767,(w+py)&32767,(z+self.objects[x]['w']-1)&32767,(w+py+self.objects[x]['h']-1)&32767))
  elif a in (0xc23afd0,0xc23b080,0xc23b0bc):ret=getattr(self,"screen",0) if a==0xc23afd0 else 0
  elif a==0xc23d7e0:pass
  elif a==0xc261da4:
   assert x not in self.deleted
   self.objects[x]['text']=self.s(y)
  elif a==0xc243188:self.events.append((x,y,z,w));ret=self.alloc(24)
  elif a==0xc23f508:
   def drop(p):
    assert p not in self.deleted,'double object delete';self.deleted.add(p)
    for q,v in list(self.objects.items()):
     if v['parent']==p and q not in self.deleted:drop(q)
   drop(x)
  elif a==0xc267784:
   name=self.s(x);rec=self.alloc(56);f=self.alloc(32);ret=self.alloc(40)
   words=[0xc258325,0xc25884d,(y-4)<<16|y,0,self.alloc(64),0,0]
   u.mem_write(f,struct.pack('<7I',*words));u.mem_write(ret,struct.pack('<7I',*words));self.w32(ret+28,rec);self.w32(rec,f);self.w32(rec+4,x);self.w32(rec+8,y|(z<<16));self.list_add(self.fm,rec);self.list_add(self.fm+12,ret)
  elif a==0xc259b88:ret=self.alloc(24);self.w32(ret,y);self.w32(ret+8,x);self.w32(ret+12,z);self.timers.append(ret)
  elif a==0xc465788:ret=self.alloc(24)
  elif a==0xc44bbf8:ret=self.top
  elif a==0xc380398:
   path=self.s(x)
   if y&4 and path not in self.files:self.files[path]=b''
   if path in self.files:ret=len(self.fds)+3;self.fds[ret]=[path,0]
   else:ret=0xffffffff
  elif a==0xc37ebd0:pass
  elif a==0xc37f456:
   if x not in self.fds:ret=0xffffffff
   else:
    p,at=self.fds[x];data=self.files[p][at:at+min(z,getattr(self,'read_limit',z))];u.mem_write(y,data);self.fds[x][1]+=len(data);ret=len(data)
  elif a==0xc37f942:
   p,at=self.fds[x];data=bytes(u.mem_read(y,z));prev=self.files[p];self.files[p]=prev[:at]+data+prev[at+z:];self.fds[x][1]+=z;ret=z
  elif a==0xc0e4138:
   path=self.s(x);entries=self.dirs.get(path,[]);ret=self.alloc(16);self.dirs[ret]=[entries,0]
  elif a==0xc0e4198:
   entries,at=self.dirs[x]
   if at<len(entries):
    typ,name=entries[at];self.dirs[x][1]+=1;ret=self.alloc(264);u.mem_write(ret,bytes([typ])+name+b'\0')
  elif a==0xc0e4170:pass
  elif a==0xc0e4120:ret=0x20000000
  elif a in (0xc37f490,0xc37f834):self.files.pop(self.s(x),None)
  elif a==0xc0f1170:ret=self.alloc(x)
  elif a in (0xc0f0790,0xc243ca4):pass
  elif a==0xc256b4c:ret=self.alloc(self.r32(x)+8);self.list_add(x,ret)
  elif a==0xc440be4:self.goto=(x,y)
  elif a==0xc44ae64:self.back=True
  elif a==0xc2a5760:pass
  elif a==0xc44d9d0:self.w32(0x200ca4e8+0x10,x)
  elif a==0xc44da58:self.w8(0x200ca4e8+4,self.u.mem_read(0x200b5be0+0x1a5,1)[0])
  elif a==0xc44fafc:self.setface=self.s(x)
  elif a==0xc306440:pass
  elif a==0xc43fa00:ret=getattr(self,'registered',0)
  elif a==0xc44a428:ret=self.page(x&65535) if getattr(self,'registered',0) and x>>16==0xe7d4 else 0
  elif a==0xc443be0:
   assert z==15,'registrar did not provide 15 pages'
   self.registered=self.alloc(60);u.mem_write(self.registered,bytes(u.mem_read(x,60)))
   arr=self.alloc(8+z*4);self.w32(arr,z);u.mem_write(arr+8,bytes(u.mem_read(y,z*4)));self.w32(self.registered+0x2c,arr)
  else:raise AssertionError(f'unmocked firmware call {a:08x}; LR={u.reg_read(UC_ARM_REG_LR):08x}')
  u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def page(self,pid):
  return 0x3d800040 if pid==0 else 0x3d801000+(pid-1)*112
 def create(self,pid):
  p=self.page(pid);root=self.alloc(0x100);self.objects[root]={'parent':0,'props':{},'label':False,'text':b'','w':336,'h':480,'x':0,'y':0};self.w32(p+0x2c,root);self.top=p
  self.call('chaos_on_create',p,root,0);self.call('chaos_on_resume',p);return root
 def click(self,idx):
  e=self.alloc(16);self.w8(e+8,7);self.call('chaos_row_ev'+str(idx),e)
def scenario(base):
 b=Band(base);assert b.call('chaos_n67_init',0x3d800000,65536,131072,8192)==0x4e363743
 for pid in range(14):
  p=b.page(pid);assert b.r32(0x3d800800+pid*4)==p and b.r32(p+0x14)==0xe7d40000|pid
  for off in (0x30,0x48,0x4c,0x54,0x60):assert base<=b.r32(p+off)<base+len(IMAGE) and b.r32(p+off)&1
 b.dirs[b'/']=[(4,b'data'),(8,'中文文件.txt'.encode())]
 b.files[b'/proc/meminfo']=b'Total: 10485760\nUsed: 2097152\n';b.files[b'/proc/fs/usage']=b'/data 256M 32M 224M /data\n'
 for repeat in range(2):
  for pid in range(14):
   root=b.create(pid);b.call('chaos_shake_timer',b.timers[0]);b.call('chaos_on_ui_destroy',b.page(pid));b.w32(b.page(pid)+0x2c,0);b.call('chaos_shake_timer',b.timers[0])
   # Firmware owns root deletion. Never call the module's delete on this root.
   assert root not in b.deleted
   def drop(p):
    b.deleted.add(p)
    for q,v in list(b.objects.items()):
     if v['parent']==p and q not in b.deleted:drop(q)
   drop(root)
 assert len(b.timers)==1,'duplicate persistent timers'
 b.create(0);b.click(3);assert b.goto[0]==0xe7d4000e
 b.call('chaos_on_pause');b.call('chaos_on_resume',b.page(0));assert b.r32(b.symbol('6APP_FG'))==1
 b.create(11);b.click(2);b.call('chaos_shake_timer',b.timers[0]);assert b.r32(0x200ca4e8+0x10)==300
 print(f'PASS relocation {base:08x}: 14 descriptors, 28 page lifecycles, single timer, navigation, brightness, resume')
 return b
def safety(b):
 def var(module,name):return b.symbol(f'{len(module)}{module}{len(name)}{name}')
 # Actual ARM reader: repeated short reads must stop at the 2047-byte buffer.
 path=var('state','VIEW_PATH');buf=var('state','FILE_VIEW')
 b.u.mem_write(path,b'/data/test.txt\0');b.files[b'/data/test.txt']=b'A'*6000;b.read_limit=73
 b.w32(var('state','VIEW_BLK'),0);b.u.mem_write(buf+2048,b'SAFE')
 b.call('file_read_view');assert b.r32(var('state','FILE_VIEW_N'))==2047
 assert bytes(b.u.mem_read(buf+2047,5))==b'\0SAFE'
 b.w32(var('state','VIEW_BLK'),2);b.call('file_read_view');assert b.r32(var('state','FILE_VIEW_N'))==1906
 b.read_limit=0xffffffff
 # Device nodes must be displayed without ever opening a blocking driver.
 b.w32(var('state','VIEW_LOADED'),0);b.w32(var('state','VIEW_DT'),2)
 before=b.calls.count(0xc380398);b.create(7);assert b.calls.count(0xc380398)==before
 # Font replacement must preserve record ownership; malformed lists block revert.
 b.create(0);original=b.r32(b.fm+4);font=b.r32(original);saved=bytes(b.u.mem_read(font,28))
 b.files[b'/data/chaos/font/st1.ttf']=b'\0\1\0\0\0\1'+bytes(6)
 b.w32(var('font_apply','PENDING'),1)
 for _ in range(30):b.call('chaos_shake_timer',b.timers[0])
 assert b.r32(var('font_apply','LIVE'))==1
 assert bytes(b.u.mem_read(font,28))!=saved,'original font was never replaced'
 w=b.r32(b.fm+16);owner=b.r32(w+28);tail=b.r32(b.fm+20)
 b.w32(b.fm+20,1);b.w32(var('font_apply','REVERT'),1)
 b.call('chaos_shake_timer',b.timers[0]);assert b.r32(var('font_apply','LIVE'))==1
 b.w32(b.fm+20,tail);b.call('chaos_shake_timer',b.timers[0])
 assert bytes(b.u.mem_read(font,28))==saved and b.r32(w+28)==owner
 assert b.r32(var('font_apply','LIVE'))==0
 b.files[b'/data/chaos/font/st1.ttf']=b'not a font';b.w32(var('font_apply','PENDING'),1)
 b.call('chaos_shake_timer',b.timers[0]);assert b.r32(var('font_apply','LIVE'))==0
 # Genuine N67 registry paths (.rle and launcher.bin), including ID 69 which
 # must NOT be treated as the P67 perpetual-calendar special case.
 head=b.alloc(8);nodes=[];paths=[]
 for i,p in enumerate([b'/resource/app/heartrate/launcher.bin',b'/resource/app/launcher/interconnect.rle']):
  s=b.alloc(len(p)+1);b.u.mem_write(s,p+b'\0');node=b.alloc(60);b.w32(node+12,s);b.w32(node+16,[15,69][i]);nodes.append(node);paths.append(s)
 b.w32(head+4,nodes[0]);b.w32(nodes[0]+4,nodes[1]);b.w32(nodes[1]+4,head);b.w32(0x200a1d74,head)
 image=struct.pack('<I',5+100*1024+100*2097152)+bytes(40000)
 for stem in ('heartrate','interconnect'):b.files[f'/data/chaos/icons/01/{stem}.bin'.encode()]=image
 b.w32(var('icon_apply','IC_PACK'),1);b.w32(var('icon_apply','IC_REQ'),1)
 for _ in range(8):b.call('chaos_shake_timer',b.timers[0])
 for node,stem in zip(nodes,('heartrate','interconnect')):assert b.s(b.r32(node+12))==f'/data/chaos/icons/01/{stem}.bin'.encode()
 # Resource assets load one per GUI tick. The UI rejects a second request
 # while that batch is running; wait for the full bounded batch first.
 for _ in range(60):b.call('chaos_shake_timer',b.timers[0])
 assert b.r32(var('icon_apply','IC_STATE'))==1
 b.w32(var('icon_apply','IC_PACK'),0)
 b.w32(var('icon_apply','IC_REQ'),2)
 for _ in range(8):b.call('chaos_shake_timer',b.timers[0])
 assert [b.r32(n+12) for n in nodes]==paths
 b.files[b'/data/chaos/icons/01/heartrate.bin']=image[:50];b.files.pop(b'/data/chaos/icons/01/interconnect.bin')
 b.w32(var('icon_apply','IC_PACK'),1)
 b.w32(var('icon_apply','IC_REQ'),1)
 for _ in range(8):b.call('chaos_shake_timer',b.timers[0])
 assert [b.r32(n+12) for n in nodes]==paths,'truncated icons were published'
 print('PASS ARM safety: short reads, buffer guards, device exclusion, fonts/ownership/corrupt lists, N67 icon mapping/restore/truncation')
def bridge_check(b):
 image=(G/'bridge.bin').read_bytes();meta=json.loads((G/'bridge.json').read_text('utf-8'));base=0x1d700000
 b.u.mem_map(base,4096);b.u.mem_write(base,image)
 for name in ('bt_reg_tick','bt_install_check'):b.sym[name]=base+meta['functions'][name]['offset']
 sent=0x200a1d38;b.w32(0x200a1d74,sent);b.w32(sent,sent);b.w32(sent+4,sent)
 b.w32(0x200a1d84,0x3d001000);b.w32(0x200a28b4,0x200a0898);b.w32(0x200a28c0,0xc443ed5)
 assert b.call('bt_install_check',0xc43fa01,0xe7d4)==0
 guards=json.loads((G/'firmware-fingerprints.json').read_text('utf-8'))
 for guard in guards:
  addr=int(guard['address'],16);orig=bytes(b.u.mem_read(addr,8));b.u.mem_write(addr,bytes([orig[0]^1])+orig[1:])
  assert b.call('bt_install_check',0xc43fa01,0xe7d4)==guard['error']
  b.u.mem_write(addr,orig)
 b.call('chaos_n67_init',0x3d800000,65536,131072,8192);app=0x3d800000;b.w32(app+0x10,0xe7d4);b.w32(app+8,app+0x280)
 r=app+0xf0
 values={0:0x52474554,8:1,12:0xc443be1,16:0xc43fa01,20:0xc44a429,24:0xc2a554d,28:app,32:b.page(0),36:app+0x800,40:0xe7d4,44:0xe7d40000,56:0x200a3900,60:0x200a1d8c}
 for off,val in values.items():b.w32(r+off,val)
 timer=b.alloc(24);b.w32(timer+12,r);b.w32(0x200a3900,24)
 b.call('bt_reg_tick',timer);assert b.r32(r+4)==2
 b.sym['firmware_default_page']=0xc43fa47
 assert b.call('firmware_default_page',0xe7d4)==b.page(0),'launcher did not select Chaos home'
 print(f'PASS real bridge ARM: {len(guards)} mismatched entry guards, 15-page registration, actual firmware default-page selection')
if __name__=='__main__':
 for base in (0x1d100000,0x1d340000,0x1c900000):
  b=scenario(base);safety(b);bridge_check(b)
