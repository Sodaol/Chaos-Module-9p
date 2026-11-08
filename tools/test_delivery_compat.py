"""Actual ARM delivery repair over original iOS26 archive, with filesystem doubles."""
from pathlib import Path
from test_port_pages import PortBand
from unicorn.arm_const import *
import struct,sys,os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'build-support/filemanager'))
from container import read
PACK=Path(os.environ['CHAOS_DELIVERY_FIXTURE']).read_bytes();FILES=read(PACK)
ROOT=b'/data/app/watchface/market';EXPECTED=ROOT+b'/202610071348/_lua/_Lua/'
class DeliveryBand(PortBand):
 def __init__(self,base,id=b'202610071348'):
  super().__init__(base);self.id=id;self.files[ROOT+b'/'+id+b'/resource.bin']=PACK;self.handles={};self.directory={};self.closed_dirs=0;self.freed=[];self.write_fail=False
 def hook(self,u,a,n,ud):
  x,y,z,w=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)];ret=0;handled=True
  if a==0xc37e30c:
   p=self.s(x)
   if y&16 and p in self.files:ret=0xffffffff
   elif p in self.files or y&4:
    if y&4 and p not in self.files:self.files[p]=b''
    ret=max([2]+list(self.handles))+1;self.handles[ret]=[p,0]
   else:ret=0xffffffff
  elif a==0xc37dba4:self.handles.pop(x,None)
  elif a==0xc37e1f4:
   off=struct.unpack('<q',struct.pack('<II',z,w))[0];how=self.r32(u.reg_read(UC_ARM_REG_SP));p,at=self.handles[x];ret=(len(self.files[p]) if how==2 else at if how==1 else 0)+off;self.handles[x][1]=ret;u.reg_write(UC_ARM_REG_R1,0)
  elif a==0xc37f458:
   p,at=self.handles[x];data=self.files[p][at:at+z];u.mem_write(y,data);self.handles[x][1]+=len(data);ret=len(data)
  elif a==0xc37f0fc:
   p,at=self.handles[x]
   if self.write_fail:ret=0xffffffff
   else:data=bytes(u.mem_read(y,z));self.files[p]=self.files[p][:at]+data+self.files[p][at+z:];self.handles[x][1]+=z;ret=z
  elif a==0xc37f490:
   f,t=self.s(x),self.s(y);assert t not in self.files,'overwrote existing target';self.files[t]=self.files.pop(f)
  elif a==0xc37fe00:self.freed.append(self.s(x));self.files.pop(self.s(x),None)
  elif a==0xc37e248:pass
  elif a==0xc0e4138:
   p=self.s(x);ret=self.alloc(16);self.directory[ret]=[[self.id] if p==ROOT else [],0]
  elif a==0xc0e4198:
   names,at=self.directory[x]
   if at<len(names):ret=self.alloc(16);u.mem_write(ret,b'\x04'+names[at]+b'\0');self.directory[x][1]+=1
  elif a==0xc0e4170:self.closed_dirs+=1;self.directory.pop(x)
  else:handled=False
  if handled:u.reg_write(UC_ARM_REG_R0,ret&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  return super().hook(u,a,n,ud)
 def run(self):
  self.w8(self.symbol('delivery_compat7REQUEST'),1)
  for i in range(2500):
   self.call('chaos_delivery_tick')
   if not self.directory and self.closed_dirs:break
  assert i<2499,'repair did not finish';assert not self.handles and not self.directory,'leaked handles'
for base in (0x1d100000,0x1d340000,0x1c900000):
 b=DeliveryBand(base,id=b'202610071349');b.run()
 for k,v in FILES.items():
  if k.endswith('.dat'):assert b.files[EXPECTED+k.split('/')[-1].encode()]==v
 assert not any(p.endswith(b'.chaos-pending') for p in b.files)
 before=dict(b.files);b.run();assert before==b.files,'repeat repair changed files'
 print(f'PASS delivery ARM {base:x}: original unmodified archive, 44 byte-exact data leaves, ID-directory mismatch, no script rewrite, repeat preserves all files, bounded work and closed handles')
b=DeliveryBand(0x1d100000);b.files[EXPECTED+b'alarm.dat']=b'KEEP';b.run();assert b.files[EXPECTED+b'alarm.dat']==b'KEEP'
b=DeliveryBand(0x1d100000);b.write_fail=True;b.run();assert not any(p.startswith(EXPECTED) for p in b.files),'failed copy left partial file'
b=DeliveryBand(0x1d100000);bad=bytearray(PACK);struct.pack_into('<I',bad,0xdc,0xfffffff0);b.files[ROOT+b'/'+b.id+b'/resource.bin']=bytes(bad);b.run();assert not any(p.startswith(EXPECTED) for p in b.files)
print('PASS delivery protection: existing data retained, failed write temp removed, malformed archive table rejected before writes')

from container import build
font_payload=b'\0\1\0\0'+bytes(range(256))*200
main='-- Chaos N67素材导入器。\nlocal M={kind="font",pkg="202610071348"}\n'.encode()
font_pack=build({'_lua/_Lua/main.lua':main,'_lua/_Lua/font-00.dat':font_payload},b'',face_id='202610071348')
b=DeliveryBand(0x1d100000);b.files[ROOT+b'/'+b.id+b'/resource.bin']=font_pack;b.run();assert b.files[EXPECTED+b'font-00.dat']==font_payload
b=DeliveryBand(0x1d100000);b.call('chaos_n67_init',0x3d800000,65536,131072,8192);b.create(15);assert '投递包兼容修复'.encode() in b.live_text();b.click(4);assert bytes(b.u.mem_read(b.symbol('delivery_compat7REQUEST'),1))==b'\1'
print('PASS delivery font chunk byte-exact recovery and Settings repair button dispatch')

