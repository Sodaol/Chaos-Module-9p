"""Run native-entry tree matching, duplicate suppression, toggles and dispatch in ARM."""
from test_port_pages import PortBand
from unicorn.arm_const import *
import struct
class NativeBand(PortBand):
    def __init__(self,base):
        super().__init__(base)
    def sync(self,parent):
        if parent not in self.objects:return
        kids=[o for o,v in self.objects.items() if v['parent']==parent and o not in self.deleted]
        oldspec=self.r32(parent+8)
        if oldspec:
            oldarr=self.r32(oldspec);oldn=self.r32(oldspec+4)
            old=[self.r32(oldarr+4*i) for i in range(oldn)] if oldarr and oldn<=160 else []
            kids=[o for o in old if o in kids]+[o for o in kids if o not in old]
        spec=self.r32(parent+8)
        if not spec:spec=self.alloc(32);self.w32(parent+8,spec)
        arr=self.alloc(max(4,len(kids)*4))
        for i,ch in enumerate(kids):self.w32(arr+i*4,ch)
        self.w32(spec,arr);self.w32(spec+4,len(kids))
    def hook(self,u,a,n,ud):
        x,y,z,w=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if a==0xc23c8b8:
            gap=struct.unpack('<i',u.mem_read(u.reg_read(UC_ARM_REG_SP),4))[0]
            self.objects[x]['native_anchor']=(y,z,w,gap)
            bx,by,br,bb=struct.unpack('<4h',u.mem_read(y+0x14,8));width=self.objects[x]['w'];height=self.objects[x]['h']
            if z==14:left=bx+(br-bx+1-width)//2;top=bb+1+gap
            elif z==7:left=bx+w;top=by+(bb-by+1-height)//2+gap
            else:left=bx;top=by
            u.mem_write(x+0x14,struct.pack('<4h',left,top,left+width-1,top+height-1))
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        if a==0xc24427c:
            u.reg_write(UC_ARM_REG_R0,self.objects[x]['props'].get(z,0));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        if a==0xc44840e:
            self.objects[x]['scaled_image']=(y,z);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        if a==0xc37f490:
            f,t=self.s(x),self.s(y)
            if f in self.files:self.files[t]=self.files.pop(f);ret=0
            else:ret=0xffffffff
            u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        super().hook(u,a,n,ud)
        if a in (0xc23f09c,0xc25ebbc,0xc2702b4,0xc275500,0xc43da64):
            obj=u.reg_read(UC_ARM_REG_R0)
            if a==0xc25ebbc:self.w32(obj,0x2c6834b0)
            self.sync(x)
        elif a==0xc241158:
            spec=self.r32(x+8)
            if not spec:spec=self.alloc(32);self.w32(x+8,spec)
            entries=[e for e in self.events if e[0]==x]
            arr=self.alloc(max(12,len(entries)*12))
            for i,(_,cb,code,ctx) in enumerate(entries):
                self.w32(arr+i*12,cb);self.w32(arr+i*12+4,ctx);self.w32(arr+i*12+8,code)
            self.w32(spec+12,arr);self.w8(spec+26,len(entries))
        elif a==0xc242784:self.sync(self.objects[x]['parent'])
    def native_page(self,title,key):
        root=self.obj(0);content=self.obj(root)
        label=self.obj(root,label=True,cls=0x2c6834b0)
        txt=title.encode()+b'\0';p=self.alloc(len(txt));self.u.mem_write(p,txt);self.w32(label+36,p)
        self.u.mem_write(content+0x14,struct.pack('<4h',0,56,335,479))
        self.sync(root);self.sync(content)
        d=self.alloc(112);self.w32(d+0x14,key);self.w32(d+0x2c,root)
        return d,root,content
    def rows(self,content):
        spec=self.r32(content+8);return [self.r32(self.r32(spec)+i*4) for i in range(self.r32(spec+4))]

def main():
    from pathlib import Path
    icon=(Path(__file__).resolve().parents[1]/'n67/assets/settings-icon.bin').read_bytes()
    assert len(icon)==4+64*64*4 and struct.unpack_from('<I',icon)[0]==5|(64<<10)|(64<<21)

    alpha=icon[7::4]
    assert all(alpha[y*64+x]==0 for x,y in [(0,0),(63,0),(0,63),(63,63)])
    assert alpha[32*64+32]>240
    for base in (0x1d100000,0x1d340000,0x1c900000):
        b=NativeBand(base);b.call('chaos_n67_init',0x3d800000,65536,131072,8192)
        main,root,content=b.native_page('设置',0x160000)
        stock=[]
        for top,bottom in [(8,95),(104,191),(200,287)]:
            o=b.obj(content,cls=0x2c68da78);b.objects[o].update(w=304,h=88,x=16,y=top)
            b.u.mem_write(o+0x14,struct.pack('<4h',16,top,319,bottom));stock.append(o)
            for offset,rect in [(0x48,(28,top+16,83,top+71)),(0x4c,(100,top+24,303,top+63))]:
                child=b.obj(o,cls=0x2c69c2e4 if offset==0x48 else 0)
                b.w32(o+offset,child);b.u.mem_write(child+0x14,struct.pack('<4h',*rect))
            label=b.obj(b.r32(o+0x4c),label=True,cls=0x2c6834b0);b.w32(o+0x50,label)
            b.objects[label]['props'][0x57]=0x3d700020
            if top==104:
                text='系统操作'.encode();ptr=b.alloc(len(text)+1);b.u.mem_write(ptr,text+b'\0');b.w32(label+0x24,ptr)
        b.sync(content)
        b.top=main;b.drive()
        rows=b.rows(content);assert len(rows)==4
        b.drive();assert b.rows(content)==rows
        row=rows[1];assert rows==[stock[0],row,stock[1],stock[2]]
        assert b.objects[row]["leading_icon"]==b"/data/chaos/chaos_settings_icon.bin"
        assert b.r32(row+0x60)==0,"Settings entry must not create a trailing arrow"
        assert b.objects[row]["w"]==304 and b.objects[row]["h"]==88,"entry must match stock dimensions"
        assert b.objects[row]['native_anchor']==(stock[0],14,0,8),'entry must match stock gap'
        assert not b.objects[row]['props'].get(0x57),'stock row must retain system typography' 
        im=b.objects[b.r32(row+0x48)];body=b.objects[b.r32(row+0x4c)]
        assert (im['w'],im['h'])==(56,56) and im['scaled_image']==(56,56)
        assert (body['w'],body['h'])==(204,40)
        assert im['native_anchor']==(row,7,12,0) and body['native_anchor']==(row,7,84,0)
        assert b.objects[b.r32(row+0x50)]['props'][0x57]==0x3d700020,'font must match stock label'
        assert im['flags']&(1<<15) and body['flags']&(1<<15)
        cb=next(cb for obj,cb,code,ctx in b.events if obj==row)
        e=b.alloc(16);b.w32(e,row);b.w32(e+4,row);b.w8(e+8,7)
        b.sym['entry_click']=cb;b.call('entry_click',e)
        assert b.goto==(0xe7d40000,0)
        b.create(15) # N67 has no update action
        update,_,uc=b.native_page('系统更新',0x160036);b.top=update;b.drive()
        assert not b.rows(uc),"N67 has no system-update entry"
        b.top=main;b.drive();assert b.rows(content)==rows,'cached page received duplicate entry'
        other,_,oc=b.native_page('显示与亮度',0x160005);b.top=other;b.drive()
        assert not b.rows(oc),'entry was injected into unrelated Settings subpage'
        b.create(15);b.click_and_drive(8) # disable main Settings entry
        b.top=main;b.drive();assert b.rows(content)==stock
        assert [struct.unpack('<4h',b.u.mem_read(o+0x14,8))[1:4:2] for o in stock]==[(8,95),(104,191),(200,287)],[struct.unpack('<4h',b.u.mem_read(o+0x14,8)) for o in stock] 
        print(f'PASS native entries ARM {base:08x}: Settings only, stock dimensions and gap, native theme, retired Update action, cached-page deduplication, stock page preservation, navigation')

if __name__=="__main__": main()
