"""Actual ARM background pipeline, with explicit snapshot/GPU/style service doubles."""
from test_native_entries import NativeBand
from unicorn.arm_const import *
import struct
W,H=336,480
BYTES=W*H*4
HEADER=struct.pack('<I',5+W*1024+H*2097152)
CACHE=b'/data/chaos/n67-background-cache.bin'
class BackgroundBand(NativeBand):
    def __init__(self,base):
        self.snapshots=0;self.large_allocations=0
        super().__init__(base)
    def hook(self,u,a,n,ud):
        x,y,z,w=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if a==0xc1610b8:ret=self.now
        elif a==0xc24427c:ret=self.objects[x]['props'].get(z,255 if z==0x29 else 0)
        elif a==0xc43479e:
            assert y==5
            ret=BYTES
        elif a==0xc43ad90:
            assert y==5 and self.r32(z)&31==5
            assert self.r32(u.reg_read(UC_ARM_REG_SP))==BYTES
            self.snapshots+=1
            u.mem_write(w,bytes([20,40,80,255])*(W*H));ret=1
        else:
            if a==0xc0f1170 and x>=BYTES:self.large_allocations+=1
            return super().hook(u,a,n,ud)
        u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def scene(self,path):
        d,root,content=self.native_page('主页',0x100000)
        self.u.mem_write(root+0x14,struct.pack('<4h',0,0,335,479))
        img=self.obj(content,cls=0x2c6825bc)
        self.u.mem_write(img+0x14,struct.pack('<4h',0,0,335,479))
        p=self.alloc(len(path)+1);self.u.mem_write(p,path+b'\0');self.w32(img+36,p)
        self.sync(content)
        self.objects[root]['props'][0x28]=0x12345678
        self.objects[root]['props'][0x29]=123
        return d,root,content
    def many(self,n=90):
        for _ in range(n):self.call('chaos_shake_timer',self.timers[0])

def main():
    for base in (0x1d100000,0x1d340000,0x1c900000):
        deferred=BackgroundBand(base)
        deferred.files[b'/data/chaos/n67-backdrop.cfg']=b'BG01\2\x0f\0\0'
        deferred.files[CACHE]=HEADER+bytes([10,20,30,255])*(W*H)
        deferred.call('chaos_n67_init',0x3d800000,65536,131072,8192);deferred.many(30)
        assert deferred.large_allocations==0 and deferred.snapshots==0,'saved blur must not start during injection'
        deferred.create(13);deferred.many(160)
        assert deferred.large_allocations==2 and deferred.u.mem_read(deferred.symbol('10background4HAVE'),1)[0]==1,'saved blur did not resume after opening Chaos'
        missing=BackgroundBand(base);missing.call('chaos_n67_init',0x3d800000,65536,131072,8192)
        missing.create(4);missing.click_and_drive(0);missing.click_and_drive(2)
        assert missing.u.mem_read(missing.symbol('10background5STAGE'),1)[0]==1,'missing cache must queue watchface capture'
        missing.click_and_drive(1)
        assert '请返回普通表盘并保持亮屏，等待背景生成'.encode() in [t for t,ms in missing.toasts], 'generate button gave no immediate toast'

        watch,_,_=missing.scene(b'/data/app/watchface/market/123/background.bin');missing.top=watch;missing.many(160)
        assert missing.snapshots==1 and CACHE in missing.files,'fresh install without background.bin cannot generate background'
        native=BackgroundBand(base);native.call('chaos_n67_init',0x3d800000,65536,131072,8192)
        native.create(4);native.click_and_drive(0)
        desc,root,content=native.scene(b'')
        native.w32(content,0x2c759314)
        native.top=desc;native.many(160)
        assert native.snapshots==1 and CACHE in native.files,'native memory-backed watchface not captured'
        b=BackgroundBand(base);b.call('chaos_n67_init',0x3d800000,65536,131072,8192)
        b.many(20)
        assert b.large_allocations==0 and b.snapshots==0,'default-off must not capture or allocate backgrounds'
        b.files[CACHE]=HEADER+bytes([10,20,30,255])*(W*H)
        b.create(4);b.click_and_drive(0);b.click_and_drive(2);b.many()
        # Starting another generation while scrolling defers processing.
        b.click_and_drive(2)
        stage=b.symbol('10background5STAGE');at=b.symbol('10background2AT')
        before=(bytes(b.u.mem_read(stage,1)),b.r32(at))
        target,cb,_,_=next(e for e in reversed(b.events) if e[2]==11 and e[0] not in b.deleted)
        event=b.alloc(24);b.w32(event,target);b.w32(event+4,target);b.w8(event+8,11)
        b.sym['background_scroll']=cb;b.now=1000;b.call('background_scroll',event);b.many(10)
        assert (bytes(b.u.mem_read(stage,1)),b.r32(at))==before,'background work ran while scrolling'
        b.now+=181;b.many()
        home,root,content=b.scene(b'/resource/app/heartrate/launcher.bin');b.top=home;b.drive()
        desc=b.objects[root]['props'][0x28]
        assert desc!=0x12345678
        assert b.r32(desc)==struct.unpack('<I',HEADER)[0] and b.r32(desc+4)==BYTES
        data=b.r32(desc+8);assert bytes(b.u.mem_read(data,4))==bytes([10,20,30,255])
        # Native grids can use in-memory icon descriptors, with no launcher paths.
        gridpage,gridroot,gc=b.native_page('Apps',0x100000)
        b.u.mem_write(gridroot+0x14,struct.pack('<4h',0,0,335,479))
        grid=b.obj(gc,size=0x900,cls=0x2c69e840);b.u.mem_write(grid+0x14,struct.pack('<4h',0,0,335,479));b.sync(gc)
        b.top=gridpage;b.drive();assert b.objects[gridroot]['props'].get(0x28),'descriptor-only grid missed backdrop'
        # Regression: opening notification/control-center must never snapshot,
        # replace native image sources, or write private battery-widget fields.
        nr,nroot,ncontent=b.scene(b'S:/system/image/notifications/default.bin')
        no=b.obj(ncontent,cls=0x2c6825bc);b.u.mem_write(no+0x14,struct.pack('<4h',100,160,179,239))
        path=b.alloc(80);b.u.mem_write(path,b'S:/system/image/notifications/no_message.bin\0');b.w32(no+36,path);b.sync(ncontent)
        before=b.snapshots;b.top=nr;b.many(25);assert b.snapshots==before and b.r32(no+36)==path
        cr,croot,ccontent=b.scene(b'S:/system/image/control_center/findphone_all.rle')
        battery=b.obj(ccontent,cls=0x2c699920);b.u.mem_write(battery+0x14,struct.pack('<4h',60,5,111,36))
        b.w32(battery+36,0x2c698bf4);b.w32(battery+40,0x2c698c20);b.w8(battery+0x38,78);b.sync(ccontent)
        raw=bytes(b.u.mem_read(battery,0x68));b.top=cr;b.many(25)
        assert b.snapshots==before and bytes(b.u.mem_read(battery,0x68))==raw
        b.create(21);b.click_and_drive(0);b.top=home;b.drive()
        assert b.objects[root]['props'][0x28]==0x12345678 and b.objects[root]['props'][0x29]==123
        b.create(21);b.click_and_drive(0)
        b.create(4);b.click_and_drive(0);b.many();b.top=home;b.drive()
        desc=b.objects[root]['props'][0x28];data=b.r32(desc+8)
        assert bytes(b.u.mem_read(data,4))==bytes([6,12,18,255]),'blur/dimming channel layout wrong'
        b.create(4);b.click_and_drive(0)
        assert b.objects[root]['props'][0x28]==0x12345678,'mode off did not restore cached native object'
        b.click_and_drive(0);b.click_and_drive(1)
        watch,wr,wc=b.scene(b'/data/app/watchface/market/123/background.bin')
        b.top=watch;b.many(125)
        assert b.snapshots==1
        assert len(b.files[CACHE])==BYTES+4
        assert b.objects[wr]['props'][0x28]==0x12345678,'watchface source was modified'
        b.create(4);b.click_and_drive(3) # automatic follow
        # The current-face pointer is read, never dereferenced by this module.
        from pathlib import Path
        import re
        state=(Path(__file__).resolve().parents[1]/'supervisor/src/state.rs').read_text('utf8')
        # Select the feature=n67 address, which is the first declaration.
        address=int(re.search(r'pub const WF_ENGINE_CUR: u32 = (0x[0-9A-Fa-f_]+)',state)[1].replace('_',''),16)
        b.w32(address,0x20000100);b.top=watch;b.many(125)
        assert b.snapshots==2
        assert b.large_allocations==3,'background buffers grew beyond one source/two output allocations'
        # Current node stays constant while the manager reuses its ID storage.
        manager=b.alloc(116);info=b.alloc(32);b.w32(0x200cacd0,manager);b.w32(manager+0x68,info)
        b.u.mem_write(info+8,b'123456789001');b.top=watch;b.many(160);assert b.snapshots==3
        b.u.mem_write(info+8,b'123456789002');b.many(160);assert b.snapshots==4,'same-node face ID update was missed'

        b.create(4);b.files[CACHE]=b'bad';b.click_and_drive(2)
        assert b.snapshots==4
        # The native mode restores an existing style rather than freeing native roots.
        assert root not in b.deleted and wr not in b.deleted
        print(f'PASS background ARM {base:08x}: fixed BGRA input, real software blur/channel layout, zone restoration, owned watchface capture, cache commit, automatic refresh, bounded buffers, invalid-file rejection')

if __name__=="__main__": main()
