"""Convert a desktop image to the N67 fixed-background file format."""
from pathlib import Path
import argparse,struct
from PIL import Image,ImageOps
p=argparse.ArgumentParser()
p.add_argument('source',type=Path);p.add_argument('output',type=Path)
a=p.parse_args()
if a.source.resolve()==a.output.resolve():p.error('output must differ from input')
im=ImageOps.fit(Image.open(a.source).convert('RGBA'),(336,480),method=Image.Resampling.LANCZOS)
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_bytes(struct.pack('<I',5+336*1024+480*2097152)+im.tobytes('raw','BGRA'))
print(f'Wrote {a.output}: 336x480 BGRA8888, 645124 bytes')
