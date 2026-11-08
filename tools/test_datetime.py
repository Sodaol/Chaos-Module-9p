"""Execute real ARM date editor and UTC conversion, with a simulated RTC."""
from test_port_pages import PortBand
from unicorn.arm_const import *
from datetime import datetime, timezone, timedelta
import struct

class ClockBand(PortBand):
    def __init__(self,base,offset=480):
        self.clock_error=False
        self.offset=offset
        self.epoch=int(datetime(2024,2,28,16,5,tzinfo=timezone.utc).timestamp())
        self.rtc_calls=[]
        self.rtc_error=False
        super().__init__(base)
        self.files[b'/dev/rtc0']=b''
    def hook(self,u,a,n,ud):
        x,y,z=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
        if a==0xc0bb094:
            ret=0xffffffff if self.clock_error else 0
            if not self.clock_error:u.mem_write(y,struct.pack('<qI',self.epoch,0))
        elif a in (0xc0f12d4,0xc0ee72c):
            ts=struct.unpack('<q',bytes(u.mem_read(x,8)))[0]
            dt=datetime.fromtimestamp(ts,timezone.utc)
            if a==0xc0f12d4:dt+=timedelta(minutes=self.offset)
            tm=(dt.second,dt.minute,dt.hour,dt.day,dt.month-1,dt.year-1900,
                (dt.weekday()+1)%7,dt.timetuple().tm_yday-1,0,0,0)
            u.mem_write(y,struct.pack('<11i',*tm));ret=y
        elif a==0xc37e1b4:
            assert self.fds[x][0]==b'/dev/rtc0' and y==0x1902
            tm=struct.unpack('<11i',bytes(u.mem_read(z,44)))
            self.rtc_calls.append(tm)
            if self.rtc_error:ret=0xffffffff
            else:
                self.epoch=int(datetime(tm[5]+1900,tm[4]+1,tm[3],tm[2],tm[1],tm[0],tzinfo=timezone.utc).timestamp())
                ret=0
        else:return super().hook(u,a,n,ud)
        u.reg_write(UC_ARM_REG_R0,ret)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))

def set_wheels(b,pid,first,second):
    root=b.r32(b.page(pid)+0x2c)
    def under(p):
        for _ in range(16):
            if p==root:return True
            if p not in b.objects:return False
            p=b.objects[p]['parent']
        return False
    pickers=[p for p in b.pickers if p not in b.deleted and under(p)]
    assert len(pickers)==2
    assert sorted((b.objects[p]['x']+2**31)%2**32-2**31 for p in pickers)==[-82,82]
    assert all(b.objects[b.objects[p]['parent']]['props'][0x11]==0 for p in pickers)
    assert all(b.objects[p].get('align')==9 and b.objects[p]['y']==((-44)&0xffffffff) for p in pickers)
    for p in pickers:
        assert b.objects[p]['w']==132
        face=b.objects[p]['props'][0x57]
        assert (b.r32(b.r32(face+28)+8)&65535)==64
    buttons=[v for o,v in b.objects.items() if o not in b.deleted and under(o) and v.get('native')=='button']
    assert any(v['w']==224 and v['h']==88 and v['x']==56 and v['y']==304 for v in buttons)
    for p,value in zip(pickers,(first,second)):
        count=struct.unpack('<h',b.u.mem_read(p+0x2d4,2))[0]
        assert struct.unpack('<H',b.u.mem_read(p+0x2d8,2))[0]==3
        b.u.mem_write(p+0x80,struct.pack('<h',value-b.pickers[p][0]+2*count))

def set_date(b,month,day):set_wheels(b,3,month,day)

for base in (0x1d100000,0x1d340000,0x1c900000):
    b=ClockBand(base)
    b.call('chaos_n67_init',0x3d800000,65536,131072,8192)
    b.create(2);set_wheels(b,2,1,5);b.click(0)
    assert not b.rtc_calls,'RTC written in event callback'
    b.drive();assert b.rtc_calls[-1][:6]==(0,5,17,28,1,124)
    b.create(3);set_date(b,4,31)
    before=len(b.rtc_calls);b.click(0);assert len(b.rtc_calls)==before
    b.drive()
    local=datetime.fromtimestamp(b.epoch,timezone.utc)+timedelta(minutes=480)
    assert (local.year,local.month,local.day,local.hour,local.minute)==(2024,4,30,1,5)
    assert '已保存'.encode() in [t for t,ms in b.toasts]
    b.rtc_error=True;b.click_and_drive(0)
    assert any(b'rc=-1' in t for t in [t for t,ms in b.toasts])
    b.rtc_error=False
    b.offset=-330;b.epoch=int(datetime(2026,12,31,5,35,tzinfo=timezone.utc).timestamp())
    b.create(3);set_date(b,1,31);b.epoch+=67
    current=datetime.fromtimestamp(b.epoch,timezone.utc)+timedelta(minutes=b.offset)
    b.click_and_drive(0)
    actual=datetime.fromtimestamp(b.epoch,timezone.utc)+timedelta(minutes=b.offset)
    assert actual.month==1 and (actual.hour,actual.minute,actual.second)==(current.hour,current.minute,current.second)
    b.offset=480;b.epoch=int(datetime(2024,1,31,3,4,5,tzinfo=timezone.utc).timestamp())
    b.create(3);set_date(b,2,31);b.click_and_drive(0)
    actual=datetime.fromtimestamp(b.epoch,timezone.utc)+timedelta(minutes=480)
    assert (actual.year,actual.month,actual.day,actual.hour,actual.minute,actual.second)==(2024,2,29,11,4,5)
    # The original date page always preserves the current system year, even after a year rollover.
    b.create(3);set_date(b,2,31)
    b.epoch=int(datetime(2025,1,1,tzinfo=timezone.utc).timestamp());b.click_and_drive(0)
    actual=datetime.fromtimestamp(b.epoch,timezone.utc)+timedelta(minutes=480)
    assert (actual.year,actual.month,actual.day)==(2025,2,28)
    failed=ClockBand(base);failed.call('chaos_n67_init',0x3d800000,65536,131072,8192)
    failed.clock_error=True;failed.create(2);failed.drive();failed.click_and_drive(0)
    assert not failed.rtc_calls and any('读取系统时间失败'.encode() in t for t,ms in failed.toasts)
    print(f'PASS datetime ARM {base:08x}: native dual wheels, confirmation, UTC offsets, leap/month clamp, deferred RTC, failure and current-year refresh')

# Execute firmware rtc_ioctl's real SET_TIME branch. Hardware lower-half,
# mutex and clock synchronization are explicit doubles; dispatch is real ARM.
class RtcDispatch(ClockBand):
    def __init__(self,base):
        self.synced=0;super().__init__(base)
        self.file=self.alloc(32);inode=self.alloc(36);upper=self.alloc(32)
        lower=self.alloc(4);ops=self.alloc(12)
        self.w32(self.file+16,inode);self.w32(inode+28,upper)
        self.w32(upper,lower);self.w32(lower,ops);self.w32(ops+4,0xc080101)
    def hook(self,u,a,n,ud):
        # This fixture's Unicorn CPU is generic Thumb, not Cortex-M. Model
        # only BASEPRI save/restore; execute dispatch and BL synchronize.
        if a==0xc0c8148:
            u.reg_write(UC_ARM_REG_R5,0);u.reg_write(UC_ARM_REG_PC,0xc0c814d);return
        if a in (0xc0c814e,0xc0c8158):
            u.reg_write(UC_ARM_REG_PC,(a+4)|1);return
        if a==0xc37e1b4:
            u.reg_write(UC_ARM_REG_R0,self.file);u.reg_write(UC_ARM_REG_PC,0xc0c80bd);return
        if 0xc0c80bc<=a<0xc0c8176:return
        if a in (0xc0e9dfc,0xc0e9e8c,0xc080100,0xc4db9ac):
            ret=0
            if a==0xc080100:
                p=u.reg_read(UC_ARM_REG_R1);tm=struct.unpack('<11i',bytes(u.mem_read(p,44)))
                self.rtc_calls.append(tm)
                if self.rtc_error:ret=0xffffffff
                else:self.epoch=int(datetime(tm[5]+1900,tm[4]+1,tm[3],tm[2],tm[1],tm[0],tzinfo=timezone.utc).timestamp())
            elif a==0xc4db9ac:self.synced+=1
            u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        return super().hook(u,a,n,ud)
for base in (0x1d100000,0x1d340000,0x1c900000):
    b=RtcDispatch(base);b.call('chaos_n67_init',0x3d800000,65536,131072,8192)
    b.create(3);set_date(b,3,1);b.click_and_drive(0)
    assert b.synced==1 and '已保存'.encode() in [t for t,ms in b.toasts]
    b.rtc_error=True;b.click_and_drive(0)
    assert b.synced==1 and any(b'rc=-1' in t for t in [t for t,ms in b.toasts])
    print(f'PASS RTC native dispatch {base:08x}: ioctl 0x1902, 44-byte tm, lower-half success/failure, synchronize only after successful write')

