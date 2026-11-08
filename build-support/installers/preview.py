from pathlib import Path
import struct,json,sys,os
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'filemanager'))
from container import rle,unrle

def make(base):
 base=Path(base);m=json.loads((base/'manifest.json').read_text(encoding='utf-8'))
 im=Image.new('RGB',(336,480),(28,28,30));d=ImageDraw.Draw(im)
 font=Path(os.environ['CHAOS_FONT'])
 def centered(s,y,size,color):
  f=ImageFont.truetype(str(font),size)
  for i,line in enumerate(s.split('\n')):
   w=d.textlength(line,font=f);d.text(((336-w)/2,y+i*(size+6)),line,font=f,fill=color,anchor='lt')
 centered('Chaos 安装器',9,32,(242,242,242))
 d.rounded_rectangle((16,56,319,123),radius=24,fill=(44,44,46),outline=(42,42,44),width=1)
 centered('准备就绪 · N67 3.1.190',80,18,(179,179,179))
 for y,text,kind in [(132,'运行','primary'),(210,'注入设置','ghost')]:
  bg=(37,99,235) if kind=='primary' else (62,34,34) if kind=='danger' else (28,28,30)
  fg=(255,69,58) if kind=='danger' else (242,242,242) if kind=='primary' else (179,179,179)
  d.rounded_rectangle((16,y,319,y+63),radius=24,fill=bg,outline=(42,42,44) if kind=='ghost' else bg,width=1)
  centered(text,y+20,24,fg)
 assets=base/'assets';assets.mkdir(exist_ok=True);im.save(assets/'installer-preview.png')
 # Settings is a separate screen, matching the installed Lua layout.
 settings=Image.new('RGB',(336,480),(28,28,30));old_draw=d;d=ImageDraw.Draw(settings)
 centered('注入设置',23,32,(242,242,242));centered('N67 · 3.1.190',79,18,(179,179,179))
 for y,text in [(170,'开机自动注入：关'),(286,'< 返回')]:
  d.rounded_rectangle((16,y,319,y+63),radius=24,fill=(28,28,30),outline=(42,42,44),width=1)
  centered(text,y+20,24,(179,179,179))
 centered('仅当前安装表盘开机时生效',380,18,(179,179,179));centered('关闭后下次开机不注入',408,18,(102,102,102))
 settings.save(assets/'installer-settings-preview.png');d=old_draw
 pal=im.quantize(colors=128);rgb=pal.getpalette();rgb+=[0]*(768-len(rgb));palette=bytearray()
 for i in range(256):
  r,g,b=rgb[i*3:i*3+3];palette+=bytes((b,g,r,255))
 raw=bytes(palette)+pal.tobytes();encoded=rle(raw);assert unrle(encoded)==raw
 (assets/'preview.gpu').write_bytes(struct.pack('<IHHI',0x410,336,480,len(encoded))+encoded)
 (assets/'preview.raw').write_bytes(raw)
 print(f'Minimal installer preview: {m["title"]}')
if __name__=='__main__':make(sys.argv[1])
