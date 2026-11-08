from pathlib import Path
p=Path(__file__).with_name('test_system_custom.py');ns={'__file__':str(p)};exec(compile(p.read_text('utf8').split('\nfor base in ')[0],str(p),'exec'),ns);CustomBand=ns['CustomBand']
for base in (0x1d100000,0x1d340000,0x1c900000):
 b=CustomBand(base);b.start();b.create(25);b.click(7);b.create(27)
 keys={code:obj for obj,cb,event,code in b.events if event==7 and code in list(range(48,58))+list(range(97,123))+[0x100,0x101,0x102,0x103,32,46] and obj not in b.deleted}
 assert len(keys)==42
 board=b.objects[keys[ord('q')]]['parent'];viewport=b.objects[board]['parent'];content=b.objects[viewport]['parent']
 assert b.objects[board]['w']==594 and b.objects[viewport]['w']==320 and b.objects[viewport]['x']==8
 assert b.objects[viewport]['scroll_dir']==3 and b.objects[viewport]['flags']&16
 assert not b.objects[viewport]['flags']&(65536|32|768)
 assert not b.objects[board].get('flags',0)&16
 for code in list(range(48,58))+list(range(97,123)):
  v=b.objects[keys[code]];assert v['w']==54 and v['h']==50 and v['parent']==board
  assert 0<=v['x'] and v['x']+v['w']<=594
 for code in (0x100,0x101,0x102,0x103,32,46):
  v=b.objects[keys[code]];assert v['parent']==content and v['x']>=0 and v['x']+v['w']<=336 and v['y']+v['h']<=392
 # Scroll ownership changes geometry only; rightmost characters still dispatch.
 before=len(b.objects);b.key(0x100);assert len(b.objects)==before
 b.key(ord('p'));b.key(ord('0'));b.key(ord('m'));b.key(0x101);b.key(32);b.key(ord('l'));b.key(0x103)
 saved=b.files[b'/data/chaos/n67-system-about.bin'];assert b'p0 l' in saved
 print(f'PASS large keyboard ARM {base:x}: 54px keys, 594px horizontally scrollable QWERTY, fixed input/actions within screen, no gesture/scroll chaining, case update without rebuild, edge-key typing/backspace/save')
