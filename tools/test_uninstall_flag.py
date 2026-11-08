from pathlib import Path
import struct
from test_port_pages import PortBand
from unicorn.arm_const import *
# Reuse only the real-native-launcher fixture, not its unrelated test cases.
p=Path(__file__).with_name('test_app_manager.py');ns={'__file__':str(p)};exec(compile(p.read_text('utf8').split('\nfor base in ')[0],str(p),'exec'),ns);AppBand=ns['AppBand']
blob=(Path(__file__).resolve().parents[1]/'n67/generated/protected-resident-test.bin').read_bytes()
for base in (0x1d100000,0x1d340000,0x1c900000):
 b=AppBand(base);b.sym['native_load_info']=0xc2a308d
 src=b.alloc(60);b.u.mem_write(src,blob[:60]);b.w32(src+8,b.r32(b.app_nodes[100]+8));b.w32(src+12,b.r32(b.app_nodes[100]+12));b.w32(src+0x1c,0xc080101)
 before={i:bytes(b.u.mem_read(n,60)) for i,n in b.app_nodes.items()}
 protected=b.call('native_load_info',src);assert protected and b.u.mem_read(protected+0x14,1)[0]&2
 regular=b.call('native_load_info',b.app_nodes[100]);assert regular and not b.u.mem_read(regular+0x14,1)[0]&2
 assert b.r32(protected)&65535==0xe7d4 and not b.u.mem_read(src+0x38,1)[0]&1
 assert before=={i:bytes(b.u.mem_read(n,60)) for i,n in b.app_nodes.items()}
 print(f'PASS native launcher ARM {base:x}: stock load_app_info copies Chaos cannot-uninstall into launcher flag bit1, still visible, normal app remains uninstallable; all other nodes untouched')
