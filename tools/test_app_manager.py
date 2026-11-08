"""Relocated Rust plus real 3.1.190 launcher add/delete/sort/list instructions.
OS, allocation, strings and LVGL are explicit doubles; this is not hardware QA.
"""
import struct
from test_port_pages import PortBand
from unicorn.arm_const import *
POLICY=b'/data/chaos/n67-app-policy.bin'
APPS=[(100,b'com.test.alpha'),(101,b'com.test.beta'),
      (22,b'com.xiaomi.miwear.settings'),(30,b'com.xiaomi.miwear.weather'),
      (81,b'com.test.native_boundary'),(82,b'com.test.installed_boundary')]
ORDER=[101,30,82,100,81,22]
ALL=set(ORDER)

def policy(items):
    data=b'NAM1'+struct.pack('<H',len(items))+b'\0\0'
    for id,flags in items:
        pkg=dict(APPS)[id];data+=bytes([flags])+pkg.ljust(96,b'\0')
    h=0x811c9dc5
    for c in data:h=((h^c)*16777619)&0xffffffff
    return data+struct.pack('<I',h)

class AppBand(PortBand):
    def __init__(self,base):
        self.app_nodes={};self.rename_fail=False;self.hide_calls=[];self.legacy=False;self.alloc_fail=False
        super().__init__(base)
        sent=self.alloc(8);self.w32(0x200a1dd0,sent);previous=sent
        iface=self.alloc(16);self.w32(iface+4,0xc4467b5);self.w32(0x200a1de8,iface)
        self.w32(iface+12,0xc080111)
        for id,pkg in APPS:
            p=self.alloc(len(pkg)+1);self.u.mem_write(p,pkg+b'\0')
            node=self.alloc(60);self.app_nodes[id]=node
            self.w32(node,previous);self.w32(previous+4,node)
            self.w32(node+8,p);self.w32(node+12,p);self.w32(node+16,id)
            self.w32(node+0x1c,0xc080101)
            self.w8(node+0x38,0xa0);previous=node
        self.w32(previous+4,sent);self.w32(sent,previous)
        # Use the actual firmware's RW initialization image, not a C-style
        # alignment assumption shared with the implementation under test.
        # Reset entry copies ROM 0x2c7d1114 to RAM 0x20096648.
        for head in (0x200a3938,0x200a4034):
            rom=0x2c7d1114+head-0x20096648
            self.u.mem_write(head,bytes(self.u.mem_read(rom,12)))
        assert self.r32(0x200a3938)==24
        assert self.r32(0x200a4034)==129
        for id in ORDER:
            node=self.alloc(32);self.w32(node,id)
            self.w32(node+8,self.r32(self.app_nodes[id]+8))
            self.list_add(0x200a3938,node)
            order=self.alloc(self.r32(0x200a4034)+8);self.u.mem_write(order,dict(APPS)[id]+b'\0')
            self.w8(order+128,3);self.list_add(0x200a4034,order)
    def chain(self,head):
        node=self.r32(head+4);prev=0;out=[];link=self.r32(head)
        while node:
            assert len(out)<160 and self.r32(node+link)==prev
            out.append(node);prev=node;node=self.r32(node+link+4)
        assert self.r32(head+8)==prev
        return out
    @property
    def desktop(self):return [self.r32(p)&65535 for p in self.chain(0x200a3938)]
    @property
    def shown(self):return set(self.desktop)
    @property
    def ordered(self):return [self.s(p) for p in self.chain(0x200a4034)]
    def check_order(self):
        assert self.ordered==[dict(APPS)[id] for id in ORDER],self.ordered
        assert self.desktop==[id for id in ORDER if id in self.shown],self.desktop
    def create(self,pid):
        old=self.r32(self.page(pid)+0x2c)
        if old in self.objects and old not in self.deleted:self.retire(pid,old)
        self.active=pid
        return super().create(pid)
    def app_action(self,slot):
        origin=self.active;self.goto=None
        self.click_and_drive(slot)
        if self.goto==(0xe7d4001d,0):
            self.create(29);self.click_and_drive(5);self.create(origin)
    def start(self):self.call('chaos_n67_init',0x3d800000,65536,131072,8192)
    def hook(self,u,a,n,ud):
        x,y,z=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
        if (0xc0e75c0<=a<0xc0e75e6 or 0xc257096<=a<0xc2570b0 or 0xc257e94<=a<0xc257fe2 or
            0xc2a308c<=a<0xc2a314e or 0xc2a3334<=a<0xc2a340c or
            0xc2a46d4<=a<0xc2a478c or 0xc2a47a0<=a<0xc2a47da):return
        if 0xc2a47ec<=a<0xc2a4852:
            assert self.legacy,'application deletion API destroys saved order'
            return
        if a==0xc37fc38:
            path=self.s(x);u.mem_write(y,bytes(96))
            if path in self.files:self.w32(y+8,0x8000);self.w32(y+24,len(self.files[path]));ret=0
            elif path in self.dirs:self.w32(y+8,0x4000);ret=0
            else:ret=0xffffffff
            u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        if a==0xc37e30c and y&8:
            path=self.s(x)
            if path in self.files:self.files[path]=b''
        if a==0xc2a1d20:
            self.hide_calls.append((a,self.r32(x)&65535));ret=0
        elif a in (0xc2a1cbc,0xc0eb0e8,0xc258498):ret=0
        elif a==0xc2578e8:ret=0 if self.alloc_fail else self.alloc(x)
        elif a==0xc4b49c0:u.mem_write(x,bytes([y&255])*z);ret=x
        elif a==0xc4b4c78:ret=0 if self.s(x)==self.s(y) else 1
        elif a==0xc080100:ret=self.r32(x+8)
        elif a==0xc080110:ret=next((self.app_nodes[id] for id,pkg in APPS if pkg==self.s(x)),0)
        elif a==0xc4467b4:ret=self.app_nodes.get(x,0)
        elif a==0xc37f490:
            f,t=self.s(x),self.s(y)
            if self.rename_fail or f not in self.files:ret=0xffffffff
            else:self.files[t]=self.files.pop(f);ret=0
        else:return super().hook(u,a,n,ud)
        u.reg_write(UC_ARM_REG_R0,ret);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))

for base in (0x1d100000,0x1d340000,0x1c900000):
    # Prove that the fixture catches the original bug in the real firmware.
    old=AppBand(base);old.legacy=True;old.sym['native_remove']=0xc2a47ec
    old.call('native_remove',100)
    assert dict(APPS)[100] not in old.ordered
    b=AppBand(base);b.start();b.create(1)
    b.click(6);assert 100 in b.shown
    b.drive();assert b.goto==(0xe7d4001d,0) and 100 in b.shown
    b.create(29);b.click(5);assert 100 in b.shown
    b.drive();assert 100 not in b.shown;b.check_order();b.create(1)
    assert b.u.mem_read(b.app_nodes[100]+0x38,1)==b'\xa1' and POLICY in b.files
    b.app_action(6);assert b.shown==ALL;b.check_order()
    assert b.u.mem_read(b.app_nodes[100]+0x38,1)==b'\xa0'
    for slot in (8,9,10):
        before=len(b.hide_calls);b.app_action(slot)
        assert b.shown==ALL and len(b.hide_calls)==before
        b.create(7);b.app_action(slot);b.create(1)
    for slot in (6,7,11):b.app_action(slot);b.check_order()
    for slot in (7,6,11):b.app_action(slot);b.check_order()
    assert b.shown==ALL
    b.app_action(6);saved=b.files[POLICY];b.alloc_fail=True
    b.app_action(6)
    assert 100 not in b.shown and b.files[POLICY]==saved
    assert b.u.mem_read(b.app_nodes[100]+0x38,1)==b'\xa1';b.check_order()
    b.alloc_fail=False;b.app_action(6);assert b.shown==ALL;b.check_order()
    saved=b.files[POLICY];b.rename_fail=True;b.app_action(6)
    assert b.shown==ALL and b.files[POLICY]==saved;b.check_order()
    assert '策略文件提交失败'.encode() in [t for t,ms in b.toasts]
    b.rename_fail=False
    b.create(7);b.app_action(6)
    b.create(1);b.click_and_drive(0)
    for _ in range(10):b.drive()
    assert b.shown=={100,22,30,81};b.check_order()
    resumed=AppBand(base);resumed.files[POLICY]=b.files[POLICY];resumed.start()
    for _ in range(240):resumed.call('chaos_shake_timer',resumed.timers[0])
    assert resumed.shown=={100,22,30,81};resumed.check_order()
    retry=AppBand(base);retry.files[POLICY]=policy([(100,1)]);retry.start()
    retry.w32(0x200a3938,0)
    for _ in range(100):retry.call('chaos_shake_timer',retry.timers[0])
    retry.w32(0x200a3938,24);assert retry.shown==ALL
    for _ in range(100):retry.call('chaos_shake_timer',retry.timers[0])
    assert retry.shown==ALL-{100};retry.check_order()
    b.click_and_drive(1)
    for _ in range(10):b.drive()
    assert b.shown==ALL;b.check_order()
    repair=AppBand(base);repair.files[POLICY]=policy([(30,1),(22,1),(81,1)])
    for id in (30,22,81):
        repair.legacy=True;repair.sym['native_remove']=0xc2a47ec
        repair.call('native_remove',id);repair.w8(repair.app_nodes[id]+0x38,0xa1)
    repair.legacy=False;repair.start()
    for _ in range(240):repair.call('chaos_shake_timer',repair.timers[0])
    assert repair.shown==ALL
    assert repair.files[POLICY]==policy([(30,2),(22,2),(81,2)])
    for head in (0x200a3938,0x200a4034):
        broken=AppBand(base);broken.start();broken.create(1)
        broken.w32(head+8,0);before=len(broken.hide_calls)
        broken.app_action(6)
        assert len(broken.hide_calls)==before and POLICY not in broken.files
        assert broken.u.mem_read(broken.app_nodes[100]+0x38,1)==b'\xa0'
        expected='桌面链未就绪或校验失败' if head==0x200a3938 else '排序链未就绪或校验失败'
        assert expected.encode() in [t for t,ms in broken.toasts]
    wrong=AppBand(base);wrong.start();wrong.create(1)
    wrong.w32(0x200a4034,132);wrong.app_action(6)
    assert not wrong.hide_calls and POLICY not in wrong.files
    assert '排序链未就绪或校验失败'.encode() in [t for t,ms in wrong.toasts]
    b.w32(b.app_nodes[100],0)
    before=len(b.hide_calls);b.create(1);b.app_action(6)
    assert len(b.hide_calls)==before
    c=AppBand(base);c.files[POLICY]=b'NAM1corrupt';c.start();c.create(1);c.app_action(6)
    assert c.shown==ALL and c.files[POLICY]==b'NAM1corrupt'
    print(f'PASS apps ARM {base:08x}: ROM-initialized 129-byte packed order links, real native sorting, retained order records, '
          'multiple hidden anchors, native ID protection, old-policy repair, '
          'deferred actions, rollback, batch exclusions, complete chain validation')

# Execute registrar recovery through the real firmware launcher add/list code.
# A previously successful entry can disappear when the launcher rebuilds.
import json
from pathlib import Path
for base in (0x1d100000,0x1d340000,0x1c900000):
    b=AppBand(base)
    generated=Path(__file__).resolve().parents[1]/'n67/generated'
    code=(generated/'bridge.bin').read_bytes()
    meta=json.loads((generated/'bridge.json').read_text())
    bridge=0x1d700000;b.u.mem_map(bridge,(len(code)+4095)&~4095);b.u.mem_write(bridge,code)
    b.sym['reg_tick']=bridge+meta['functions']['bt_reg_tick']['offset']
    r=b.alloc(96);timer=b.alloc(24);b.w32(timer+12,r)
    node=b.app_nodes[100]
    for off,value in {0:0x52474554,4:3,8:2,16:0xc4467b5,24:0xc2a47a1,28:node,40:100,56:0x200a3938,60:0x200a1de8}.items():b.w32(r+off,value)
    # Remove the desktop entry, preserve its saved order, and simulate a native
    # hidden flag. Other flags must survive recovery.
    rec=next(e for e in b.chain(0x200a3938) if b.r32(e)&65535==100)
    b.sym['unlink']=0xc257ece;b.call('unlink',0x200a3938,rec)
    b.w8(node+0x38,0xa1)
    b.call('reg_tick',timer)
    assert b.r32(r+4)==3 and b.r32(r+64)!=0 and b.desktop.count(100)==1
    assert bytes(b.u.mem_read(node+0x38,1))==b'\xa0'
    b.call('reg_tick',timer);assert b.desktop.count(100)==1 and b.r32(r+76)==1
    # Allocation failure must invalidate historical success, then recover on
    # the same context when allocation becomes available again.
    rec=b.r32(r+64);b.call('unlink',0x200a3938,rec);b.alloc_fail=True
    b.call('reg_tick',timer);assert b.r32(r+4)==2 and b.r32(r+64)==0
    b.alloc_fail=False;b.call('reg_tick',timer)
    assert b.r32(r+4)==3 and b.desktop.count(100)==1
    b.check_order()
    rec=b.r32(r+64);b.call('unlink',0x200a3938,rec)
    b.w8(node+0x38,0xa1);b.w32(r+28,b.app_nodes[101]);tries=b.r32(r+76)
    b.call('reg_tick',timer)
    assert b.r32(r+92)==21 and b.r32(r+76)==tries and bytes(b.u.mem_read(node+0x38,1))==b'\xa1'
    b.w32(r+28,node);icon=b.r32(node+12);b.w32(node+12,0)
    b.call('reg_tick',timer)
    assert b.r32(r+92)==22 and b.r32(r+76)==tries and bytes(b.u.mem_read(node+0x38,1))==b'\xa1'
    b.w32(node+12,icon)
    print(f'PASS registrar recovery ARM {base:08x}: lost icon, own hidden bit, real native add, no duplicate, allocation failure clears stale success, retained order')

# Optional Chaos visibility reuses real N67 sorting without removing order.
APPS.append((0xe7d4,b'com.chaos.manager'));ORDER.append(0xe7d4);ALL.add(0xe7d4)
for base in (0x1d100000,0x1d340000,0x1c900000):
    b=AppBand(base);b.start();b.create(15)
    meta=json.loads((generated/'bridge.json').read_text());code=(generated/'bridge.bin').read_bytes()
    bridge=0x1d700000;b.u.mem_map(bridge,(len(code)+4095)&~4095);b.u.mem_write(bridge,code)
    b.sym['coexisting_registrar']=bridge+meta['functions']['bt_reg_tick']['offset']
    reg=b.alloc(96);timer=b.alloc(24);b.w32(timer+12,reg)
    for off,value in {0:0x52474554,4:3,8:2,16:0xc4467b5,24:0xc2a47a1,28:b.app_nodes[0xe7d4],40:0xe7d4,56:0x200a3938,60:0x200a1de8,80:0x3d800300}.items():b.w32(reg+off,value)

    b.click_and_drive(9)
    assert 0xe7d4 not in b.shown,'visibility toggle did not apply on its first tick'
    for _ in range(25):b.drive();b.call('coexisting_registrar',timer)
    assert 0xe7d4 not in b.shown and b.shown==ALL-{0xe7d4};b.check_order()
    assert b.files[b'/data/chaos/launcher.cfg']==b'\0'
    # A second bridge allocated by re-entering the installer must read the
    # original application's policy rather than its own empty resident block.
    trampoline=0x1d7ff000;b.u.mem_map(trampoline,4096)
    b.u.mem_write(trampoline,b'\x00\x48\x70\x47'+b.page(0).to_bytes(4,'little'))
    b.w32(reg+20,trampoline|1);b.w32(reg+44,0xe7d40000);b.w32(reg+80,b.alloc(8))
    for _ in range(15):b.drive();b.call('coexisting_registrar',timer)
    assert 0xe7d4 not in b.shown,'a second registrar ignored the active app preference'

    b.click_and_drive(9)
    for _ in range(5):b.drive();b.call('coexisting_registrar',timer)
    assert b.shown==ALL and b.desktop.count(0xe7d4)==1;b.check_order()
    # Changing the shipped installer's file after injection reaches the live app.
    b.files[b'/data/chaos/launcher.cfg']=b'\0'
    for _ in range(9):b.drive();b.call('coexisting_registrar',timer)
    assert 0xe7d4 not in b.shown
    b.files[b'/data/chaos/launcher.cfg']=b'\1'
    for _ in range(9):b.drive();b.call('coexisting_registrar',timer)
    assert b.shown==ALL and b.desktop.count(0xe7d4)==1
    b.rename_fail=True;b.click_and_drive(9)
    for _ in range(5):b.drive()
    assert b.shown==ALL and b.files[b'/data/chaos/launcher.cfg']==b'\1'
    assert '桌面入口设置保存失败'.encode() in [t for t,ms in b.toasts]
    reboot=AppBand(base);reboot.files[b'/data/chaos/launcher.cfg']=b'\0';reboot.start()
    for _ in range(75):reboot.call('chaos_shake_timer',reboot.timers[0])
    assert reboot.shown==ALL-{0xe7d4};reboot.check_order()
    print(f'PASS optional launcher {base:08x}: own entry only, real native add/hide/sort, retained order and native apps, saved choice, failed commit rollback, fresh-load restore')
