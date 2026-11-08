"""32-bit hostile-FS/GUI tests compiled from the vendored production file core."""
from pathlib import Path
import sys,subprocess,os
R=Path(__file__).resolve().parents[1];D=R/'n67/files';G=D/'generated';G.mkdir(exist_ok=True)
zig=os.environ.get('CHAOS_ZIG','C:/dsh2/tools/zig-aarch64-windows-0.16.0/zig.exe')
cmd=[zig,'cc','-target','wasm32-freestanding','-Oz','-fno-jump-tables','-nostdlib','-fno-builtin','-ffreestanding','-Wl,--no-entry']
cmd+=['-Wl,--export='+n for n in ['run_test','test_state_size','test_debug','test_catalog','test_render','test_records','test_scroll_object','test_scroll_position','test_record_count','test_record_size']]
cmd+=[str(D/'test.c'),'-o',str(G/'test.wasm')]
for attempt in range(30):
 with (G/'build.log').open('w') as log:p=subprocess.run(cmd,stdout=log,stderr=log)
 if p.returncode==0:break
else:raise RuntimeError('file test compile failed')
subprocess.run(['node',str(D/'test.cjs')],check=True)
