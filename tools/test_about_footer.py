from pathlib import Path
import struct
from unicorn.arm_const import *
p=Path(__file__).with_name('test_system_custom.py');ns={'__file__':str(p)};exec(compile(p.read_text('utf8').split('\nfor base in ')[0],str(p),'exec'),ns);CustomBand=ns['CustomBand']
class AboutBand(CustomBand):
 def hook(self,u,a,n,ud):
  if a==0xc23c8b8:
   x,y,align,dx=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)];gap=struct.unpack('<i',u.mem_read(u.reg_read(UC_ARM_REG_SP),4))[0]
   self.native_alignments.append((x,y,align,dx));bx,by,br,bb=struct.unpack('<4h',u.mem_read(y+0x14,8));w=self.objects[x]['w'];h=self.objects[x]['h'];bh=self.objects[y]['h']
   left=bx if align==13 else bx+(br-bx+1-w)//2;top=by+bh+gap
   u.mem_write(x+0x14,struct.pack('<4h',left,top,left+w-1,top+h-1));self.objects[x]['y']=top
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  return super().hook(u,a,n,ud)
for base in (0x1d100000,0x1d340000,0x1c900000):
 b=AboutBand(base);b.start();b.create(24);b.click(3);b.create(27);b.key(0x102)
 for c in b'ddssaasdhhutftp09jhudrccddfqa':b.key(c)
 b.key(0x103);labels=b.about();content=b.objects[labels[0x44]]['parent'];button=b.obj(content,cls=0x2c68da78);b.objects[button].update(w=304,h=64);b.u.mem_write(button+0x14,struct.pack('<4h',16,400,319,463));b.w32(0x200cd0d0,button);b.drive()
 value=b.objects[labels[0x28]];assert b'\n' in value['text'] and value['h']>=80
 assert b.objects[button]['y']>=b.objects[labels[0x44]]['y']+b.objects[labels[0x44]]['h']+15
 n=len(b.native_alignments)
 for _ in range(20):b.drive()
 assert len(b.native_alignments)==n,'stable layout repeated'
 b.u.mem_write(button+0x16,struct.pack('<h',400))
 for _ in range(12):b.drive()
 assert b.objects[button]['y']>=b.objects[labels[0x44]]['y']+b.objects[labels[0x44]]['h']+15
 print(f'PASS About wrap ARM {base:x}: long system text grows and shifts version/serial/footer, native footer below final line; stable layout cached, native footer reset repaired')

