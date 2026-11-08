"""Log record order, UTF-8, geometry bound and explicit WRAP under ARM GUI doubles."""
from test_port_pages import PortBand,LOG
for base in (0x1d100000,0x1d340000,0x1c900000):
 b=PortBand(base);b.call('chaos_n67_init',0x3d800000,65536,131072,8192)
 b.files[LOG]='old 第一条\nsecond 第二条\nnew 最新记录\n'.encode();b.create(16)
 expected='new 最新记录\nsecond 第二条\nold 第一条'.encode()
 assert expected in b.live_text()
 b.files[LOG]=('long '+('汉字ABC '*120)+' end\n').encode();b.click_and_drive(0)
 txt=b.files[LOG].rstrip(b'\n');assert txt in b.live_text()
 label=next(v for k,v in b.objects.items() if k not in b.deleted and v['text']==txt)
 assert label['h']>36*10 and label['h']<32767
 b.files[LOG]=b''.join(('record%03d 中文\n'%i).encode() for i in range(300));b.click_and_drive(0)
 txt=next(t for t in b.live_text() if t.startswith(b'record299'))
 assert len(txt.split(b'\n'))==200 and txt.endswith('record100 中文'.encode())
 assert txt.decode('utf-8')
 b.files[LOG]=b'\xffbroken\n';b.click_and_drive(0)
 assert '日志不是 UTF-8，请用文件管理查看'.encode() in b.live_text()
 print(f'PASS logs {base:x}: newest-first records, long Chinese text retained with full-height wrap, 200-record i16 geometry bound, corrupt UTF-8 handled')
