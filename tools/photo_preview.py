from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
r=Path('work/ui15/chaos-9pro');t=json.loads((r/'n67/photo-theme.json').read_text());font=Path('work/firmware/n67-3.1.190/MiSans-Regular.ttf')
if not font.exists():font=Path('C:/Windows/Fonts/msyh.ttc')
F=lambda n:ImageFont.truetype(str(font),n)
im=Image.new('RGB',(336,480),t['page_background']);d=ImageDraw.Draw(im)
d.text((16,8),'Chaos',font=F(28),fill='#f2f4f8');d.text((246,12),'02:51',font=F(26),fill='#f2f4f8')
for y in [64,184,304,424]:d.rounded_rectangle((12,y,323,y+111),radius=26,fill=t['card_background'])
d.text((28,76),'CPU占用',font=F(32),fill='#f2f4f8');d.text((28,122),'28.0%',font=F(28),fill='#d0d5dd')
for y,title,value,pct,color in [(184,'存储占用','259MB/89MB',26,t['storage_color']),(304,'内存占用','11MB/4MB',36,t['memory_color'])]:
 d.text((28,y+5),title,font=F(32),fill='#f2f4f8');d.text((28,y+43),value,font=F(28),fill='#d0d5dd')
 d.rounded_rectangle((28,y+86,307,y+103),radius=9,fill='#434a54');d.rounded_rectangle((28,y+86,28+int(280*pct/100)-1,y+103),radius=9,fill=color)
d.text((28,458),'文件管理',font=F(32),fill='#f2f4f8')
out=Path('outputs');out.mkdir(exist_ok=True);im.save(out/'ui15-photo1-layout-preview.png')
