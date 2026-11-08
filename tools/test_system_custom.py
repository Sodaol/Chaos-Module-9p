"""N67 1.0.8 display settings: real relocated ARM, explicit LVGL/VFS doubles."""
from test_native_entries import NativeBand
from unicorn.arm_const import *
import struct

CFG=b'/data/chaos/n67-system-about.bin'
class CustomBand(NativeBand):
 def __init__(self,base):
  self.rename_fail=False;self.native_alignments=[];super().__init__(base)
 def hook(self,u,a,n,ud):
  x,y,z,w=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
  if a==0xc37e30c and y&8:
   name=self.s(x)
   if name in self.files:self.files[name]=b''
  if a==0xc37f490 and self.rename_fail:
   u.reg_write(UC_ARM_REG_R0,0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  if a==0xc23c8b8:
   self.native_alignments.append((x,y,z,w));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  super().hook(u,a,n,ud)
  if a==0xc2644d8:self.w8(x+0x50,(self.u.mem_read(x+0x50,1)[0]&~7)|(y&7))
  if a==0xc263e08:
   text=self.s(y);p=self.alloc(len(text)+1);u.mem_write(p,text+b'\0');self.w32(x+36,p)
 def start(self):self.call('chaos_n67_init',0x3d800000,65536,131072,8192)
 def key(self,code):
  obj,cb,_,_=next(e for e in reversed(self.events) if e[3]==code and e[2]==7 and e[0] not in self.deleted)
  event=self.alloc(16);self.w32(event,obj);self.w32(event+4,obj);self.w8(event+8,7);self.w32(event+12,code)
  self.sym['keyboard_action']=cb;self.call('keyboard_action',event)
 def about(self):
  page,root,content=self.native_page('关于本机',self.r32(0xc7dfb3c+0x14));labels={}
  originals={0x10:b'Original Band',0x18:b'OriginalModel',0x20:b'01:23:45:67:89:ab',0x28:b'Xiaomi HyperOS',0x34:b'3.1.190',0x44:b'SERIAL-123'}
  for offset in (0x0c,0x10,0x14,0x18,0x1c,0x20,0x24,0x28,0x30,0x34,0x40,0x44):
   label=self.obj(content,label=True,cls=self.r32(0xc25ebd4));text=originals.get(offset,b'Field')
   p=self.alloc(len(text)+1);self.u.mem_write(p,text+b'\0');self.w32(label+36,p)
   self.u.mem_write(label+0x14,struct.pack('<4h',16,56,319,91));self.w32(0x200cd088+offset,label)
   self.objects[label]['text']=text;labels[offset]=label
  self.sync(content);self.sync(root);self.top=page;return labels

for base in (0x1d100000,0x1d340000,0x1c900000):
 b=CustomBand(base);b.start();b.create(15);b.click(10);assert b.goto==(0xe7d40016,0)
 b.create(22)
 for i in range(4):b.click(i);assert b.goto==(0xe7d40017+i,0)
 # Four presets stored independently, with a checksummed atomic commit.
 for page,choice in [(23,2),(24,2),(25,1),(26,2)]:b.create(page);b.click_and_drive(choice)
 assert CFG in b.files and len(b.files[CFG])==144
 labels=b.about();b.drive()
 for offset,text in [(0x34,b'4.103.022'),(0x28,b'HarmonyOS'),(0x10,'小米手环9 Pro'.encode()),(0x18,b'M2553B1')]:assert b.objects[labels[offset]]['text']==text
 assert b.objects[labels[0x20]]['text']==b'01:23:45:67:89:ab'
 assert b.objects[labels[0x44]]['text']==b'SERIAL-123'
 assert len(b.native_alignments)==11
 before=len(b.native_alignments);b.drive();assert len(b.native_alignments)==before,'unchanged About must not redraw every tick'
 # Reset restores the captured native value, not a P67 preset.
 b.create(23);b.click_and_drive(0);b.top=next(d for d in [] ) if False else b.top
 b.top=b.alloc(112);b.w32(b.top+0x14,0x16001b);b.w32(b.top+0x2c,b.objects[labels[0x34]]['parent']);
 # Use the same actual root (parent is content).
 content=b.objects[labels[0x34]]['parent'];b.w32(b.top+0x2c,b.objects[content]['parent']);b.drive()
 assert b.objects[labels[0x34]]['text']==b'3.1.190'
 # Full 42-key upstream keyboard, typed through real event callbacks.
 b.create(25);b.click(7);assert b.goto==(0xe7d4001b,0)
 root=b.create(27);events=[e for e in b.events if e[2]==7 and e[3] in list(range(48,58))+list(range(97,123))+[0x100,0x101,0x102,0x103,32,46]]
 assert len(events)==42
 count=len(b.objects);b.key(0x100);assert len(b.objects)==count,'shift rebuilt the viewport'
 b.key(ord('n'));b.key(ord('6'));b.key(ord('7'));b.key(32);b.key(ord('p'));b.key(0x101);b.key(ord('x'))
 b.key(0x103);assert b.back
 saved=b.files[CFG]
 # Failed save leaves the previous config and the editor intact.
 b.create(25);b.click(7);b.create(27);b.back=False;b.rename_fail=True;b.key(ord('z'));b.key(0x103)
 assert not b.back and b.files[CFG]==saved
 b.drive();assert any('保存失败'.encode() in text for text,ms in b.toasts)
 b.rename_fail=False
 # Settings and saved strings survive a fresh relocated module instance.
 resumed=CustomBand(base);resumed.files[CFG]=saved;resumed.start();labels=resumed.about();resumed.drive()
 assert resumed.objects[labels[0x10]]['text']==b'n67 x'
 resumed.create(25);resumed.click(7);resumed.create(27);resumed.key(0x102)
 for _ in range(31):resumed.key(ord('w'))
 resumed.key(0x103);labels=resumed.about();resumed.drive()
 name=resumed.objects[labels[0x10]]
 assert name['text'].replace(b'\n',b'')==b'W'*31 and b'\n' in name['text'] and name.get('long_mode')==0 and name['h']>40,'custom About text must wrap'

 # Exercise all four fields with a long unbroken token, not just device name.
 for page,custom_slot,offset,char in [(23,4,0x34,ord('8')),(24,3,0x28,ord('w')),(25,7,0x10,ord('w')),(26,4,0x18,ord('w'))]:
  resumed.create(page);resumed.click(custom_slot);resumed.create(27);resumed.key(0x102)
  for _ in range(31):resumed.key(char)
  resumed.key(0x103);labels=resumed.about();resumed.drive()
  value=resumed.objects[labels[offset]];expected=bytes([char]).upper()*31
  assert b'\n' in value['text'] and value['text'].replace(b'\n',b'')==expected,(page,value['text'])
  assert value.get('long_mode')==0 and value['w']==304 and value['h']>=120
  assert resumed.objects[labels[0x20]]['text']==b'01:23:45:67:89:ab'
  assert resumed.objects[labels[0x44]]['text']==b'SERIAL-123'
  # A firmware refresh of one label cannot permanently undo wrapping.
  value['text']=expected
  p=resumed.alloc(32);resumed.u.mem_write(p,expected+b'\0');resumed.w32(labels[offset]+36,p)
  for _ in range(12):resumed.call('chaos_shake_timer',resumed.timers[0])
  assert b'\n' in value['text'],'native refresh left this field on one line'
  # Newlines are never written into the saved 31-byte custom input.
  blob=resumed.files[CFG];kind=page-23
  assert blob[4+kind*34+2:4+kind*34+33]==expected
 # Stock About also wraps the serial; native refresh can replace it later.
 serial=CustomBand(base);serial.start();sl=serial.about();serial.drive()
 expected=b'0123456789ABCDEFGHIJKLMNOPQRST'
 value=serial.objects[sl[0x44]]
 ptr=serial.alloc(len(expected)+1);serial.u.mem_write(ptr,expected+b'\0');serial.w32(sl[0x44]+36,ptr)
 value['text']=expected;serial.w8(sl[0x44]+0x50,3)
 for _ in range(12):serial.call('chaos_shake_timer',serial.timers[0])
 assert b'\n' in value['text'] and value['text'].replace(b'\n',b'')==expected
 assert value['w']==304 and value['h']>36 and value['long_mode']==0
 assert serial.objects[sl[0x20]]['text']==b'01:23:45:67:89:ab'
 count=len(serial.native_alignments)
 for _ in range(20):serial.call('chaos_shake_timer',serial.timers[0])
 assert len(serial.native_alignments)==count,'stable serial must not cause repeated relayout'
 assert CFG not in serial.files,'serial formatting must never save identity'
 # Malformed persisted values never modify stock labels or identity fields.
 broken=CustomBand(base);broken.files[CFG]=b'NSC1broken';broken.start();labels=broken.about();broken.drive()
 assert broken.objects[labels[0x10]]['text']==b'Original Band'
 print(f'PASS N67 system-custom ARM {base:08x}: six routes, atomic settings, native About-only fields, reset, 42-key input/case/backspace, failure retention, reboot restore, corrupt-config rejection')
