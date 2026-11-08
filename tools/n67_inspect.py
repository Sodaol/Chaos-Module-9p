import sys,struct
from pathlib import Path
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
b=Path('C:/dsh2/fw/data/ota/app/vela_ap.bin').read_bytes()
c=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);c.detail=True
def dis(a,n):
 for i in c.disasm(b[a-0x0c080000:a-0x0c080000+n],a):
  extra=''
  if i.mnemonic.startswith('ldr') and '[pc,' in i.op_str:
   try:
    q=((i.address+4)&~3)+i.operands[1].mem.disp
    v=struct.unpack_from('<I',b,q-0x0c080000)[0];extra=f' ; [{q:08x}]={v:08x}'
    if 0x2c080000<=v<0x2c080000+len(b):
     s=b[v-0x2c080000:].split(b'\0')[0][:100]
     extra+=' '+repr(s)
   except (IndexError,struct.error):pass
  print(f'{i.address:08x} {i.mnemonic} {i.op_str}{extra}')
if sys.argv[1]=='dis':dis(int(sys.argv[2],16),int(sys.argv[3],16))
elif sys.argv[1]=='table':
 a=int(sys.argv[2],16)
 for j in range(int(sys.argv[3])):
  v=struct.unpack_from('<I',b,a-0x0c080000+4*j)[0];print(j,f'{v:08x}')
elif sys.argv[1]=='str':
 s=sys.argv[2].encode();p=b.find(s)
 while p>=0:
  start=b.rfind(b'\0',0,p)+1;v=start+0x2c080000;pat=struct.pack('<I',v)
  refs=[f'{i+0x0c080000:08x}' for i in range(0,len(b)-4,2) if b[i:i+4]==pat]
  print(hex(v),repr(b[start:].split(b'\0')[0][:150]),refs)
  p=b.find(s,p+len(s))
elif sys.argv[1]=='bl':
 target=int(sys.argv[2],16)
 for o in range(0,min(len(b)-4,0x480000),2):
  hi,lo=struct.unpack_from('<HH',b,o)
  if hi&0xf800!=0xf000 or lo&0xd000!=0xd000:continue
  s=(hi>>10)&1;i1=1^((lo>>13)&1)^s;i2=1^((lo>>11)&1)^s
  d=(s<<24)|(i1<<23)|(i2<<22)|((hi&1023)<<12)|((lo&2047)<<1)
  if s:d-=1<<25
  a=0xc080000+o
  if a+4+d==target:print(f'{a:08x}')
