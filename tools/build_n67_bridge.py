"""Standalone native bridge builder; no commands modify the device."""
from pathlib import Path
import subprocess,sys,os,shutil
R=Path(__file__).resolve().parents[1];S=R/'build-support';G=R/'n67/generated';G.mkdir(parents=True,exist_ok=True)
zig=os.environ.get('CHAOS_ZIG') or shutil.which('zig') or 'zig'
src=G/'bridge.nocomment.c';obj=G/'bridge.o'
subprocess.run([sys.executable,str(S/'work/wasm/cnocomment.py'),str(R/'n67/bridge.c'),str(src)],check=True)
cmd=[zig,'cc','-c','-target','thumb-freestanding-eabi','-mcpu=cortex_m33','-Oz','-fno-jump-tables','-nostdlib','-fno-stack-protector','-fno-builtin','-ffreestanding',str(src),'-o',str(obj)]
for attempt in range(60):
 obj.unlink(missing_ok=True)
 with open(os.devnull,'wb') as null:result=subprocess.run(cmd,stdout=null,stderr=null)
 if result.returncode==0 and obj.exists():break
else:raise RuntimeError('Zig did not finish in 60 attempts')
subprocess.run([sys.executable,str(S/'native/elfpack.py'),str(obj),str(G/'bridge.bin'),'--json',str(G/'bridge.json')],check=True)
print('Bridge compiled on attempt',attempt+1)
