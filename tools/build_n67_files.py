"""Compile the vendored N67 file engine, independent of other workspace apps."""
from pathlib import Path
import os,subprocess,shutil,sys
R=Path(__file__).resolve().parents[1];G=R/'n67/generated'
def compile_files():
 zig=os.environ.get('CHAOS_ZIG') or shutil.which('zig') or 'zig'
 src=G/'files.c';obj=G/'files.o'
 text=(R/'n67/files/integration.c').read_text('utf-8')
 for name in ['platform_n67.c.in','core.c','honeycomb.c']:
  text=text.replace('#include "'+name+'"',(R/'n67/files'/name).read_text('utf-8'))
 src.write_text(text,'utf-8')
 subprocess.run([sys.executable,str(R/'build-support/work/wasm/cnocomment.py'),str(src),str(G/'files.stripped.c')],check=True)
 cmd=[zig,'cc','-c','-target','thumb-freestanding-eabi','-mcpu=cortex_m33','-Xclang','-target-feature','-Xclang','+no-movt','-Oz','-fno-jump-tables','-fno-stack-protector','-fno-exceptions','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-builtin','-ffreestanding','-ffunction-sections','-fdata-sections','-nostdlib',str(G/'files.stripped.c'),'-o',str(obj)]
 for attempt in range(60):
  obj.unlink(missing_ok=True)
  with (G/'files-build.log').open('w') as log:p=subprocess.run(cmd,stdout=log,stderr=log)
  if p.returncode==0 and obj.exists():break
 else:raise RuntimeError('file engine build failed; see files-build.log')
 print('File engine compiled',attempt+1);return obj
