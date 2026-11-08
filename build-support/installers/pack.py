from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'filemanager'))
from container import build
if __name__=='__main__':
 base=Path(sys.argv[1]);m=json.loads((base/'manifest.json').read_text(encoding='utf-8'))
 files={'_lua/_Lua/main.lua':(base/'generated/main.lua').read_bytes(),'_lua/_Lua/icon.bin':(base/'assets/icon.bin').read_bytes()}
 for asset in sorted((base/'generated').glob('chaos-*.dat')):files['_lua/_Lua/'+asset.name]=asset.read_bytes()
 out=build(files,(base/'assets/preview.gpu').read_bytes(),m['face_id'],m['name'])
 (base/'generated/resource.bin').write_bytes(out)
 print(f'Fresh {m["title"]} container: {len(out)} bytes, Lua {len(files["_lua/_Lua/main.lua"])} bytes')
