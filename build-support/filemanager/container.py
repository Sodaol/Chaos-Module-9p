"""N67 watchface resource protocol writer/reader, with a freshly built index.

Header Lua section is count/offset at 0xD8/0xDC. Entries are four u32:
resource UID, reserved, leaf offset, leaf length. A leaf is <HBB16x>, ASCII
name without NUL, exact payload. The preview has its own table and GPU blob.
No input container, fixed Lua slot, unused assets, or stale index copies.
"""
from pathlib import Path
import struct

MAGIC=0x1234A55A
HEADER_SIZE=0x148

def build(files,preview,face_id='990000000004',name='N67 Files Installer'):
 assert len(face_id)==12 and face_id.isdigit()
 assert len(name.encode())<32 and len(files)==len(set(files))
 header=bytearray(HEADER_SIZE)
 def w(off,n):struct.pack_into('<I',header,off,n)
 w(0,MAGIC);w(4,0x10000);w(0x10,0x800);w(0x14,0x10000);w(0x1C,1)
 header[0x28:0x34]=face_id.encode();header[0x68:0x68+len(name)]=name.encode()
 header[0x100:0x100+len('格式1'.encode())]='格式1'.encode();w(0xA8,0x80000000)
 preview_table=HEADER_SIZE;lua_table=preview_table+16
 end_table=lua_table+16*len(files);preview_record=end_table;preview_data=preview_record+16
 w(0x20,preview_data);w(0xAC,preview_data);w(0xB0,1);w(0xB4,preview_table)
 for off in [0xB8,0xC0,0xC8,0xD0,0xE0,0xE8,0xF0,0xF8]:w(off+4,end_table)
 w(0xD8,len(files));w(0xDC,lua_table)
 out=header+bytearray(16*(1+len(files)))
 struct.pack_into('<IIII',out,preview_table,0,0,preview_record,16)
 out+=struct.pack('<IIII',0x05000000,0,0,0)+preview
 for i,(name,data) in enumerate(files.items()):
  raw=name.encode('ascii');assert name.startswith('_lua/_Lua/') and 0<len(raw)<=120 and len(data)<=65535
  at=len(out);leaf=struct.pack('<HBB16x',len(data),0,len(raw))+raw+data
  struct.pack_into('<IIII',out,lua_table+i*16,0x05000000|i,0,at,len(leaf));out+=leaf
 assert read(bytes(out))==files
 return bytes(out)

def read(data):
 assert len(data)>=HEADER_SIZE and struct.unpack_from('<I',data)[0]==MAGIC
 count,table=struct.unpack_from('<II',data,0xD8)
 assert count<=128 and HEADER_SIZE<=table<=len(data)-count*16
 files={};spans=[]
 for i in range(count):
  uid,reserved,at,length=struct.unpack_from('<IIII',data,table+i*16)
  assert uid==0x05000000|i and reserved==0 and at>=table+count*16 and length>=21 and at+length<=len(data)
  size,pad,n=struct.unpack_from('<HBB',data,at)
  assert pad==0 and n>0 and data[at+4:at+20]==bytes(16) and length==20+n+size
  name=data[at+20:at+20+n].decode('ascii');assert name.startswith('_lua/_Lua/') and name not in files
  files[name]=data[at+20+n:at+length];spans.append((at,at+length))
 for (a,b),(c,d) in zip(sorted(spans),sorted(spans)[1:]):assert b<=c
 return files

def rle(raw):
 # Firmware 0x0C25D21E: low token repeats N units; high token copies N units.
 out=bytearray();i=0
 while i<len(raw):
  run=1
  while i+run<len(raw) and raw[i+run]==raw[i] and run<127:run+=1
  if run>=3:out.extend((run,raw[i]));i+=run;continue
  start=i;i+=run
  while i<len(raw) and i-start<127:
   run=1
   while i+run<len(raw) and raw[i+run]==raw[i] and run<3:run+=1
   if run>=3:break
   i+=min(run,127-(i-start))
  out.append(0x80|(i-start));out+=raw[start:i]
 return struct.pack('<II',0x5AA521E0,(len(raw)<<4)|1)+out

def unrle(data):
 magic,spec=struct.unpack_from('<II',data);assert magic==0x5AA521E0 and spec&15==1
 size=(spec>>4)&0xFFFFFF;out=bytearray();i=8
 while i<len(data):
  token=data[i];i+=1;n=token&127;assert n and len(out)+n<=size
  if token&128:assert i+n<=len(data);out+=data[i:i+n];i+=n
  else:assert i<len(data);out+=bytes([data[i]])*n;i+=1
 assert len(out)==size
 return bytes(out)

def main():
 base=Path(__file__).resolve().parent
 files={'_lua/_Lua/main.lua':(base/'generated/main.lua').read_bytes(),
        '_lua/_Lua/icon.bin':(base/'assets/icon.bin').read_bytes()}
 preview=(base/'assets/preview.gpu').read_bytes()
 out=build(files,preview);(base/'generated/resource.bin').write_bytes(out)
 print(f'Fresh container: {len(out)} bytes, {len(files)} assets, exact Lua length {len(files["_lua/_Lua/main.lua"])}')

if __name__=='__main__':main()
