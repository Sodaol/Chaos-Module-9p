"""Create N67 files locally; transfer the output tree with a file-transfer app.
No device connection, firmware mutation, automatic overwrite or bundled fonts.
"""
from pathlib import Path
import argparse,json,struct,shutil
from PIL import Image
R=Path(__file__).resolve().parents[1]
def index_bytes(previous,slot,name):
 raw=bytearray(Path(previous).read_bytes() if previous else b' '*128)
 if len(raw)!=128:raise ValueError('index must contain exactly 128 bytes')
 records=[raw[i:i+16] for i in range(0,128,16)]
 if any(r[:2]==f'{slot:02}'.encode() for r in records):raise ValueError('slot already occupied; use an empty slot')
 at=next((i for i,r in enumerate(records) if not r[:2].isdigit()),None)
 if at is None:raise ValueError('all eight slots occupied')
 n=name.encode('utf-8')
 if not n or len(n)>12 or any(c.isspace() or ord(c)<32 for c in name):raise ValueError('name must fit 12 UTF-8 bytes without spaces')
 raw[at*16:at*16+16]=f'{slot:02} '.encode()+n.ljust(12,b' ')+b'\n'
 return bytes(raw)
def validate_ttf(path):
 b=Path(path).read_bytes()
 if len(b)<12 or b[:4]!=b'\0\1\0\0':raise ValueError('requires a standalone TrueType sfnt font, not TTC/WOFF/OTF')
 count=struct.unpack_from('>H',b,4)[0]
 if not 1<=count<=256 or len(b)<12+16*count:raise ValueError('invalid table directory')
 tables={}
 for i in range(count):
  tag,checksum,off,size=struct.unpack_from('>4sIII',b,12+i*16)
  if tag in tables or off<12+16*count or off+size>len(b):raise ValueError('invalid or duplicate sfnt table')
  tables[tag]=b[off:off+size]
 if any(t not in tables for t in (b'cmap',b'head',b'hhea',b'hmtx',b'maxp',b'glyf',b'loca')):raise ValueError('missing TrueType outlines/metrics')
 if len(tables[b'head'])<54 or struct.unpack_from('>I',tables[b'head'],12)[0]!=0x5f0f3cf5:raise ValueError('invalid head magic')
 return b
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('kind',choices=['font','icons']);p.add_argument('--source',required=True);p.add_argument('--out',required=True);p.add_argument('--slot',type=int,choices=range(1,9),required=True);p.add_argument('--name',required=True);p.add_argument('--index',help='existing index.txt copied from the band, preserving other slots')
 a=p.parse_args();index=index_bytes(a.index,a.slot,a.name);dst=Path(a.out)/'data/chaos'/('font' if a.kind=='font' else 'icons');dst.mkdir(parents=True,exist_ok=True)
 if (dst/'index.txt').exists():raise ValueError('output already has an index; choose a fresh directory')
 if a.kind=='font':(dst/f'st{a.slot}.ttf').write_bytes(validate_ttf(a.source))
 else:
  mapping=json.loads((R/'n67/icon-mapping.json').read_text('utf-8'))+json.loads((R/'n67/system-icon-mapping.json').read_text('utf-8'));folder=dst/f'{a.slot:02}';folder.mkdir(exist_ok=True);found=[]
  for item in mapping:
   stem=item['stem'];src=next((Path(a.source)/f'{stem}.{ext}' for ext in ('png','webp','jpg') if (Path(a.source)/f'{stem}.{ext}').is_file()),None)
   if src is None:continue
   w,h=item.get('width',100),item.get('height',100)
   im=Image.open(src).convert('RGBA');im.thumbnail((w,h),Image.Resampling.LANCZOS)
   canvas=Image.new('RGBA',(w,h));canvas.alpha_composite(im,((w-im.width)//2,(h-im.height)//2));im=canvas
   data=struct.pack('<I',5+w*1024+h*2097152)+im.tobytes('raw','BGRA');(folder/f'{stem}.bin').write_bytes(data);found.append(stem)
  if not found:raise ValueError('no matching images; see n67/icon-mapping.json')
  print('Converted',len(found),'of',len(mapping),'icons; missing icons remain original')
 (dst/'index.txt').write_bytes(index);print('Prepared local tree:',Path(a.out).resolve())
if __name__=='__main__':main()
