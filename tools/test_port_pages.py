"""Run the relocated new ARM pages; OS/LVGL/storage remain explicit doubles."""
import struct
import json
from pathlib import Path
from check_photo15 import UiBand, IMAGE
from page_layout import PAGE_COUNT
from unicorn.arm_const import *

LOG = b'/data/chaos/chaos.log'

class PortBand(UiBand):
    def alloc(self,n):
        # The real allocator cannot hand out the resident module's heap alias.
        start=self.base+0x20000000
        end=start+len(IMAGE)
        if self.next<end and self.next+((n+7)&~7)>start:self.next=(end+63)&~63
        return super().alloc(n)
    def __init__(self, base):
        self.short_writes = 0
        super().__init__(base)

    def hook(self, u, a, n, ud):
        if a==0xc0be244:
            u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        if 0xc4467fa <= a < 0xc44681e:
            return  # Execute the actual firmware default-page helper.
        if a in (0xc4467b4, 0xc448748):
            key = u.reg_read(UC_ARM_REG_R0)
            ret = getattr(self, 'registered', 0)
            if a == 0xc448748:
                ret = self.page(key & 65535) if ret and key >> 16 == 0xe7d4 else 0
            u.reg_write(UC_ARM_REG_R0, ret)
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
            return
        if a == 0xc4497cc:
            x, y, z = [u.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
            assert z == PAGE_COUNT
            self.registered = self.alloc(60)
            u.mem_write(self.registered, bytes(u.mem_read(x, 60)))
            arr = self.alloc(8 + z * 4)
            self.w32(arr, z)
            u.mem_write(arr + 8, bytes(u.mem_read(y, z * 4)))
            self.w32(self.registered + 0x2c, arr)
            sent = self.r32(0x200a1dd0)
            self.w32(self.registered, sent)
            self.w32(self.registered + 4, sent)
            self.w32(sent, self.registered)
            self.w32(sent + 4, self.registered)
            self.w32(0x200a1dd8, 1)
            self.w32(0x200a1ddc, PAGE_COUNT)
            u.reg_write(UC_ARM_REG_R0, 0)
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
            return
        if a == 0xc37fe00:
            path = self.s(u.reg_read(UC_ARM_REG_R0))
            present = path in self.files
            self.files.pop(path, None)
            u.reg_write(UC_ARM_REG_R0, 0 if present else 0xffffffff)
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
            return
        if a == 0xc37f0fc and self.short_writes:
            # Force real ARM write-all through a series of short writes.
            count = u.reg_read(UC_ARM_REG_R2)
            u.reg_write(UC_ARM_REG_R2, min(count, self.short_writes))
        return super().hook(u, a, n, ud)

    def drive(self):
        for _ in range(3):
            self.call('chaos_shake_timer', self.timers[0])

    def live_text(self):
        return [v['text'] for k, v in self.objects.items() if k not in self.deleted]

    def click_and_drive(self, row):
        self.click(row)
        self.drive()

    def registrar(self):
        generated = Path(__file__).resolve().parents[1] / 'n67/generated'
        code = (generated / 'bridge.bin').read_bytes()
        meta = json.loads((generated / 'bridge.json').read_text('utf8'))
        base = 0x1d700000
        self.u.mem_map(base, (len(code) + 4095) & ~4095)
        self.u.mem_write(base, code)
        for name in ('bt_reg_tick', 'bt_install_check'):
            self.sym[name] = base + meta['functions'][name]['offset']
        sent = 0x200a0100
        self.w32(0x200a1dd0, sent)
        self.w32(sent, sent)
        self.w32(sent + 4, sent)
        self.w32(0x200a1de0, 0x3d001000)
        self.w32(0x200a1d3c, 0x200a0204)
        self.w32(0x200a1d48, 0xc4487cd)
        assert self.call('bt_install_check', 0xc4467b5, 0xe7d4) == 0
        guards = json.loads((generated / 'firmware-fingerprints.json').read_text('utf8'))
        for guard in guards:
            a = int(guard['address'], 16)
            before = bytes(self.u.mem_read(a, 8))
            self.u.mem_write(a, bytes([before[0] ^ 1]) + before[1:])
            assert self.call('bt_install_check', 0xc4467b5, 0xe7d4) == 0
            self.u.mem_write(a, before)
        assert self.call('bt_install_check',0xc4467b5,0xe7d5)==29
        assert self.call('bt_install_check',0xc4467b7,0xe7d4)==29
        app = 0x3d800000
        self.w32(app + 0x10, 0xe7d4)
        self.w32(app + 8, app + 0x280)
        reg = app + 0xf0
        values = {0: 0x52474554, 8: 1, 12: 0xc4497cd, 16: 0xc4467b5,
                  20: 0xc448749, 24: 0xc2a47a1, 28: app, 32: self.page(0),
                  36: app + 0x800, 40: 0xe7d4, 44: 0xe7d40000,
                  56: 0x200a3938, 60: 0x200a1de8}
        for off, value in values.items():
            self.w32(reg + off, value)
        timer = self.alloc(24)
        self.w32(timer + 12, reg)
        self.w32(0x200a3938, 24)
        self.call('bt_reg_tick', timer)
        assert self.r32(reg + 4) == (3 if json.loads((generated.parent/'manifest.json').read_text('utf8')).get('profile')=='settings-egg' else 2)
        self.sym['default_page'] = 0xc4467fb
        assert self.call('default_page', 0xe7d4) == self.page(0)
        assert self.call('bt_install_check', 0xc4467b5, 0xe7d4) == self.registered
        return len(guards)

def main():
    for base in (0x1d100000, 0x1d340000, 0x1c900000):
        b = PortBand(base)
        b.short_writes = 3
        assert b.call('chaos_n67_init', 0x3d800000, 65536, 131072, 8192) == 0x4e363743
        assert b.files[LOG].startswith(b'[10-24 12:30:00] ')
        assert b.files[LOG].endswith('\u521d\u59cb\u5316\n'.encode())
        for pid in range(PAGE_COUNT):
            p = b.page(pid)
            assert b.r32(0x3d800800 + pid * 4) == p
            assert b.r32(p + 0x14) == 0xe7d40000 | pid
            for off in (0x30, 0x48, 0x4c, 0x54, 0x60):
                cb = b.r32(p + off)
                assert base <= cb < base + len(IMAGE) and cb & 1
    
        # New page lifecycle twice, with firmware-owned roots and one UI timer.
        for _ in range(2):
            for pid in range(15, PAGE_COUNT):
                b.test_pid = pid
                root = b.create(pid)
                b.drive()
                assert b.r32(b.symbol('5state5PAGES') + pid * 72 + 68) == 1
                b.call('chaos_on_pause')
                b.call('chaos_on_resume', b.page(pid))
                b.retire(pid, root)
                b.drive()
        assert len(b.timers) == 1
    
        b.create(0)
        b.click(8)
        assert b.goto == (0xe7d4000f, 0)
        b.create(12)
        before_cache=dict(b.files)
        b.click_and_drive(1)
        assert {k:v for k,v in b.files.items() if k!=LOG}=={k:v for k,v in before_cache.items() if k!=LOG},'retired cache page performed file operations'
        b.create(15)
        assert not any('缓存清理'.encode()==t or '系统更新入口'.encode() in t for t in b.live_text())
        b.click(2)
        assert b.goto == (0xe7d40010, 0)
        b.create(16)
        before = b.files[LOG]
        b.click_and_drive(2)  # stale/forged confirm without first arming
        assert b.files[LOG] == before
        b.click_and_drive(1)
        assert '\u786e\u8ba4\u6e05\u7a7a\u65e5\u5fd7'.encode() in b.live_text()
        assert b.files[LOG] == before
        b.click_and_drive(3)  # cancel
        assert b.files[LOG] == before
        b.click_and_drive(1)
        b.click_and_drive(2)
        assert LOG not in b.files
        assert '\u65e5\u5fd7\u5df2\u6e05\u7a7a'.encode() in [t for t,ms in b.toasts]
    
        # Read tail after many short reads; reject partial UTF-8 from a corrupt log.
        b.files[LOG] = ('\u4e2d\u6587\u65e5\u5fd7\n' * 700).encode()
        b.read_limit = 7
        b.click_and_drive(0)
        text = b.live_text()
        assert any(t.startswith('\u4e2d\u6587\u65e5\u5fd7\n'.encode()) and len(t) > 100 for t in text)
        b.files[LOG] = b'bad\xff\xfe\n'
        b.click_and_drive(0)
        assert '\u65e5\u5fd7\u4e0d\u662f UTF-8\uff0c\u8bf7\u7528\u6587\u4ef6\u7ba1\u7406\u67e5\u770b'.encode() in b.live_text()
    
        # Log rotation never grows beyond the 48-KiB bound.
        b.files[LOG] = b'x' * (48 * 1024)
        b.create(0)
        b.click(8)
        assert 0 < len(b.files[LOG]) < 240
    
        # License next/previous must return to exactly the same first chunk.
        b.create(18)
        first = next(t for t in b.live_text() if t.startswith(b'                    GNU'))
        b.click_and_drive(1)
        assert first not in b.live_text()
        b.click_and_drive(0)
        assert first in b.live_text()
        b.create(15)
        b.click(5)
        assert b.goto == (0xe7d40014, 0)
        b.create(20)
        b.vibrations.clear()
        b.click(0)
        assert not b.vibrations, 'vibration invoked during event dispatch'
        b.drive()
        assert b.vibrations == [bytes([1])+bytes(11)]
        b.now += 1000
        b.click_and_drive(1)
        assert b.vibrations[-1] == bytes([3])+bytes(11)
        assert len(b.vibrations)==2
        guards = b.registrar()
    
        print(f'PASS ARM {base:08x}: {PAGE_COUNT} descriptors, new page lifecycle, routes, '
              'short log I/O, two-step clear/cancel, UTF-8 handling, log rotation, license paging; '
              f'C registrar count, actual firmware default page, {guards} fingerprint differences ignored by ID-only precheck')

if __name__=="__main__": main()
