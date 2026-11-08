"""Validate current artifacts and bundle the complete corresponding source."""
from pathlib import Path
import subprocess,json,hashlib,zipfile,shutil,sys,datetime
R=Path(__file__).resolve().parents[1];G=R/'n67/generated'
OUT=R.parent/'release/chaos-9pro-v2.1';OUT.mkdir(parents=True,exist_ok=True)
tests={}
for name,cmd in [('packed_lua',['node','tools/check_n67_runtime.cjs']),('arm_mock',[sys.executable,'tools/test_n67.py']),('resource_files_arm',[sys.executable,'tools/test_n67_extensions.py']),('file_core',[sys.executable,'tools/test_n67_files.py'])]:
 p=subprocess.run(cmd,cwd=R,capture_output=True,text=True,encoding='utf-8',check=True)
 tests[name]=p.stdout.strip();print(p.stdout.strip())
installer=OUT/'Chaos-9Pro-3.1.190-v2.1.bin';shutil.copy2(G/'resource.bin',installer)
for src,dst in [('n67/README-9Pro.md','使用说明.md'),('n67/PORTING.md','移植技术记录.md'),('LICENSE','LICENSE'),('n67/manifest.json','manifest.json'),('n67/assets/installer-preview.png','安装表盘预览.png'),('n67/icon-mapping.json','icon-mapping.json'),('n67/system-icon-mapping.json','system-icon-mapping.json')]:shutil.copy2(R/src,OUT/dst)
files=set(subprocess.check_output(['git','ls-files'],cwd=R,text=True).splitlines())
files.update(str(p.relative_to(R)).replace('\\','/') for p in (R/'supervisor/src').rglob('*.rs'))
files.update(str(p.relative_to(R)).replace('\\','/') for p in (R/'build-support').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
files.update('tools/'+n for n in ['build_n67.py','build_n67_bridge.py','pack_n67.py','make_n67_installer.py','n67.ld','n67_inspect.py','test_n67.py','check_n67_runtime.cjs','prepare_n67_assets.py','release_n67.py','build_n67_files.py','test_n67_files.py','test_n67_extensions.py'])
files.update(str(p.relative_to(R)).replace('\\','/') for p in (R/'n67').rglob('*') if p.is_file() and p.suffix in ('.rs','.c','.md','.json','.png','.lua','.bin','.gpu','.in','.py','.cjs','.dat') and '__pycache__' not in p.parts)
srczip=OUT/'Chaos-9Pro-v2.1-完整源码.zip'
with zipfile.ZipFile(srczip,'w',zipfile.ZIP_DEFLATED) as z:
 for name in sorted(files):
  p=R/name
  if p.is_file():z.write(p,'Chaos-9Pro-Source/'+name)
 z.writestr('Chaos-9Pro-Source/README-9Pro.md',(R/'n67/README-9Pro.md').read_bytes())
receipt={'date_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'upstream':'https://github.com/WenHuaYiYang/Chaos-Module','upstream_commit':'3b5448db64d74ab7a544fba6ab1a6d3f94625c0e','firmware':'N67 CN 3.1.190','hardware_tested':False,'tests':tests,'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (installer,srczip)},'installer_bytes':installer.stat().st_size,'rust':json.loads((G/'chaos.json').read_text('utf-8'))['sha256'],'relocations':len(json.loads((G/'chaos.json').read_text('utf-8'))['relocations'])}
(OUT/'验证记录.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),'utf-8')
(OUT/'SHA256.txt').write_text(''.join(v+'  '+k+'\n' for k,v in receipt['sha256'].items()),'utf-8')
bundle=OUT.parent/'Chaos-9Pro-3.1.190-v2.1-发布包.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(OUT.iterdir()):
  if p.is_file():z.write(p,p.name)
print('RELEASE',bundle,installer.stat().st_size,'bytes; hardware_tested=false')
