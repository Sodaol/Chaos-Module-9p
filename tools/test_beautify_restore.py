"""N67 saved choice persistence, reload, corrupt/missing assets and save failure."""
from test_native_entries import NativeBand
from unicorn.arm_const import *
class CustomBand(NativeBand):
 def hook(self,u,a,n,ud):
  if a==0xc37e30c:
   path=self.s(u.reg_read(UC_ARM_REG_R0));flags=u.reg_read(UC_ARM_REG_R1)
   if flags&12==12 and path in self.files:
    u.reg_write(UC_ARM_REG_R0,0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  if a==0xc37f0fc and getattr(self,'fail_writes',False):
   u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  if a==0xc257e94:
   head=u.reg_read(UC_ARM_REG_R0);p=self.alloc(self.r32(head)+8);self.list_add(head,p)
   u.reg_write(UC_ARM_REG_R0,p);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  super().hook(u,a,n,ud)
import struct
PATHS=[b'/data/chaos/n67-beautify-a.bin',b'/data/chaos/n67-beautify-b.bin']
def record(c,gen):
 b=b'NBR1'+bytes(c)+struct.pack('<I',gen);h=2166136261
 for v in b:h=((h^v)*16777619)&0xffffffff
 return b+struct.pack('<I',h)
def init(b):b.call('chaos_n67_init',0x3d800000,65536,131072,8192)
def var(b,module,name):return b.symbol(str(len(module))+module+str(len(name))+name)
def toggle(b,slot):
 from unicorn.arm_const import UC_ARM_REG_R0
 row=b.r32(b.symbol('5state5PAGES')+13*72+slot*4);o=b.r32(row+0x60)
 cb=next(cb for obj,cb,code,ctx in b.events if obj==o);e=b.alloc(24);b.w32(e,o);b.w32(e+4,o);b.w8(e+8,29)
 b.sym['restore_toggle']=cb;b.call('restore_toggle',e);b.drive()
for base in (0x1d100000,0x1d340000,0x1c900000):
 b=CustomBand(base);init(b);b.create(13);toggle(b,3)
 data=next(b.files[p] for p in PATHS if p in b.files)
 assert data==record([0,255,0,1],1)
 assert "背景模糊".encode() in b.live_text()
 # Reusing both existing twins must succeed (NuttX O_EXCL used to fail here).
 for c in (1,0,1,0):
  toggle(b,3)
 assert not b.toasts
 assert max(struct.unpack_from('<I',b.files[p],8)[0] for p in PATHS)==5
 # Reload takes the newest intact generation; a torn newer record is ignored.
 n=CustomBand(base);n.files[PATHS[0]]=record([1,1,0,0],5);n.files[PATHS[1]]=record([0,2,0,1],6)[:-1]
 n.files[b'/data/chaos/font/st1.ttf']=b'\0\1\0\0\0\1'+bytes(6)
 init(n);n.drive()
 assert n.r32(var(n,'font_apply','PENDING'))==1 or n.r32(var(n,'font_apply','LIVE'))==1
 # No file and invalid header remain on native font, rather than applying a missing face.
 bad=CustomBand(base);bad.files[PATHS[0]]=record([1,8,0,1],1);init(bad);bad.drive()
 assert bad.r32(var(bad,'font_apply','LIVE'))==0 and bad.r32(var(bad,'font_apply','PENDING'))==0
 disabled=CustomBand(base);disabled.files[PATHS[0]]=record([0,1,0,0],1);disabled.files[b'/data/chaos/font/st1.ttf']=n.files[b'/data/chaos/font/st1.ttf'];init(disabled);disabled.drive()
 assert disabled.r32(var(disabled,'font_apply','LIVE'))==0 and disabled.r32(var(disabled,'font_apply','PENDING'))==0
 # Explicit user selection is recorded and survives a fresh ARM instance.
 b.files[b'/data/chaos/font/st2.ttf']=n.files[b'/data/chaos/font/st1.ttf']
 b.files[b'/data/chaos/font/index.txt']=b'02 test        '+b'\n'+b' '*112
 b.create(5);b.click_and_drive(0)
 assert any(b.files.get(p,bytes(16))[5]==2 for p in PATHS)
 # A transient write failure retries without a false failure toast.
 transient=CustomBand(base);init(transient);transient.create(13)
 transient.fail_writes=True;toggle(transient,3)
 assert not transient.toasts
 transient.fail_writes=False
 for _ in range(18):transient.drive()
 assert any(transient.files.get(p)==record([0,255,0,1],1) for p in PATHS)
 assert not transient.toasts
 # Broken write cannot claim to have changed the persistent preference.
 fail=CustomBand(base);init(fail);fail.create(13)
 fail.files[PATHS[0]]=b'broken' # force a later real write path; open failure below
 fail.fail_writes=True;toggle(fail,3)
 for _ in range(40):fail.drive()
 assert '选择未保存，下次载入可能恢复旧设置'.encode() in [t for t,ms in fail.toasts]
 print(f'PASS restore {base:08x}: persistent switches, twin generations/checksum, valid font reload, missing assets, disabled restore, manual choice, failed save rollback')
