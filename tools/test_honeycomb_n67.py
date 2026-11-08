"""Run the relocated N67 honeycomb with LVGL doubles and the stock click producer."""
import struct

from test_native_entries import NativeBand
from unicorn.arm_const import *


class HoneycombBand(NativeBand):
    def __init__(self, base):
        self.point = (0, 0)
        self.launches = []
        super().__init__(base)

    def hook(self, u, a, n, ud):
        if 0xc2a1dd4 <= a < 0xc2a1eb8:
            return
        x, y, z = [u.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
        result = 0
        if a == 0xc239f92:
            u.mem_write(y, struct.pack('<hh', *self.point))
        elif a == 0xc25eba0:
            result = self.obj(x, cls=0x2c6825bc)
        elif a == 0xc2617d8:
            self.objects[x]['source'] = self.s(y)
            u.mem_write(x+0x2c, struct.pack('<HH', 96, 96))
        elif a in (0xc23e980, 0xc23b38a, 0xc43a874, 0xc080100):
            pass
        elif a == 0xc44a850:
            self.launches.append(struct.unpack_from('<H', u.mem_read(x, 44), 6)[0])
        elif a == 0xc4b49c0:
            u.mem_write(x, bytes([y & 255]) * z)
            result = x
        else:
            super().hook(u, a, n, ud)
            if a in (0xc23ba44, 0xc23baba):
                self.w32(x+0x1c, self.objects[x]['flags'])
            return
        u.reg_write(UC_ARM_REG_R0, result)
        u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))

    def setup_grid(self, count):
        page, _, content = self.native_page('Apps', 0x100000)
        self.grid = self.obj(content, size=0x900, cls=0x2c69e840)
        self.sync(content)
        self.u.mem_write(self.grid+0x14, struct.pack('<4h', 0, 0, 335, 479))
        self.w32(self.grid+0x880, 1)
        self.w32(0x200cb4c0, self.grid)
        self.w32(0x200bf388, self.alloc(64))
        iface = self.alloc(64)
        self.w32(iface+44, 0xc080101)
        self.w32(0x200a1d40, iface)
        self.top = page
        self.records = []
        self.w32(0x200a3938, 24)
        for i in range(count):
            rec, icon = self.alloc(32), self.alloc(64)
            self.u.mem_write(icon, f'S:/system/icon-{i}.bin'.encode()+b'\0')
            self.w32(rec, 20+i)
            self.w32(rec+12, icon)
            prev = self.records[-1] if self.records else 0
            self.w32(rec+24, prev)
            self.w32(prev+28 if prev else 0x200a393c, rec)
            self.records.append(rec)
        self.w32(0x200a3940, self.records[-1])
        return page

    def send(self, obj, code, point=(0, 0)):
        self.point = point
        cb = next(cb for target, cb, _, _ in reversed(self.events) if target == obj)
        e = self.alloc(24)
        self.w32(e, obj)
        self.w32(e+4, obj)
        self.w8(e+8, code)
        self.sym['honeycomb_event_fixture'] = cb
        self.call('honeycomb_event_fixture', e)

    def switch(self, index):
        self.create(28)
        row = self.r32(self.symbol('5state5PAGES') + 28*72 + index*4)
        self.send(self.r32(row+0x60), 29)
        self.drive()

    def overlay(self):
        return self.call('chaos_honeycomb_overlay')


for base in (0x1d100000, 0x1d340000, 0x1c900000):
    b = HoneycombBand(base)
    b.call('chaos_n67_init', 0x3d800000, 65536, 131072, 8192)
    page = b.setup_grid(30)
    b.drive()
    assert not b.overlay() and not b.r32(b.grid+0x1c) & 1
    b.switch(3)
    b.top = page
    b.call('chaos_honeycomb_update', 1)
    assert not b.overlay(), 'native icons must stay visible while building'
    b.drive()
    overlay = b.overlay()
    assert overlay and b.r32(b.grid+0x1c) & 1
    cells = [o for o, v in b.objects.items() if v['parent'] == overlay]
    assert len(cells) == 30
    first = cells[0]
    before = [(b.objects[o]['x'], b.objects[o]['y']) for o in cells[:7]]
    b.send(first, 1, (168, 240))
    b.send(first, 7, (168, 240))
    b.send(first, 8)
    assert b.launches == [20]
    b.send(first, 1, (168, 240))
    b.send(first, 2, (210, 205))
    b.call('chaos_honeycomb_update', 1)
    after = [(b.objects[o]['x'], b.objects[o]['y']) for o in cells[:7]]
    assert after[0][0] > before[0][0] and after[0][1] < before[0][1]
    b.send(first, 7)
    b.send(first, 8)
    assert b.launches == [20], 'a drag launched an application'
    original_width = b.objects[first]['w']
    b.send(overlay, 1, (325, 250))
    b.send(overlay, 2, (325, 210))
    b.call('chaos_honeycomb_update', 1)
    assert b.objects[first]['w'] > original_width
    b.send(overlay, 8)
    # Catch inertia before entering the native editing fallback.
    b.send(first, 1, (168, 240))
    b.send(first, 8)
    b.send(first, 1, (168, 240))
    b.send(first, 5)
    b.call('chaos_honeycomb_update', 1)
    assert not b.overlay() and not b.r32(b.grid+0x1c) & 1
    b.switch(3)
    assert not b.overlay() and not b.r32(b.grid+0x1c) & 1
    assert overlay in b.deleted
    print(f'PASS honeycomb {base:x}: default off, settings switch, staged layout, two-axis drag, native launch, click suppression, zoom and stock editing fallback')
