"""Run the relocated N67 honeycomb with LVGL doubles and the stock click producer."""
import struct

from test_native_entries import NativeBand
from unicorn.arm_const import *


class HoneycombBand(NativeBand):
    def __init__(self, base):
        self.point = (0, 0)
        self.launches = []
        self.refreshes = []
        self.back_posts = []
        self.launcher_page = 0
        self.check_back_dispatch = False
        super().__init__(base)

    def hook(self, u, a, n, ud):
        if 0xc4490b8 <= a < 0xc4490d8:
            return
        if a == 0xc080300:
            assert u.reg_read(UC_ARM_REG_R0) == 0, 'explicit exit was consumed'
            u.reg_write(UC_ARM_REG_PC, self.back_dispatch_return)
            return
        if self.check_back_dispatch and 0xc44d730 <= a <= 0xc44d738:
            return
        if self.check_back_dispatch and a in (0xc44d73a, 0xc44d74e):
            u.emu_stop()
            return
        if 0xc2a1dd4 <= a < 0xc2a1eb8 or 0xc2a4f54 <= a < 0xc2a4f78:
            return
        x, y, z = [u.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
        result = 0
        if a == 0xc448c60:
            assert u.mem_read(x+12, 1)[0] == 0x36
            self.back_posts.append(x)
            self.back_dispatch_return = u.reg_read(UC_ARM_REG_LR)
            u.reg_write(UC_ARM_REG_R0, self.launcher_page)
            u.reg_write(UC_ARM_REG_R1, x+4)
            u.reg_write(UC_ARM_REG_LR, 0xc080301)
            u.reg_write(UC_ARM_REG_PC, self.r32(self.launcher_page+0x64))
            return
        if a == 0xc448748 and x == 0x100000:
            result = self.launcher_page
        elif a == 0xc2a31d4:
            assert x == self.launcher_page and y == self.r32(x+0x2c)
            self.w32(0x200cae00, y)
            result = 73
        elif a == 0xc29eff8:
            assert x == self.launcher_page
            result = 91
        elif a == 0xc23c880:
            pass
        elif a == 0xc2467a0:
            self.refreshes.append(bool(self.r32(self.grid+0x1c) & 1))
        elif a == 0xc239f92:
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
        self.launcher_page = page
        self.w32(page+0x48, 0xc2a31d5)
        self.w32(page+0x4c, 0xc29eff9)
        self.w32(page+0x64, 0xc2a4f55)
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

    def native_timer(self, timer):
        self.sym['honeycomb_timer_fixture'] = self.r32(timer+8)
        self.call('honeycomb_timer_fixture', timer)

    def stock_back_dispatch(self, page, request):
        self.check_back_dispatch = True
        try:
            self.u.reg_write(UC_ARM_REG_SP, 0x200ff000)
            self.u.reg_write(UC_ARM_REG_R0, page)
            self.u.reg_write(UC_ARM_REG_R4, request-4)
            self.u.emu_start(0xc44d731, 0, count=300000)
            return self.u.reg_read(UC_ARM_REG_PC)
        finally:
            self.check_back_dispatch = False

    def overlay(self):
        return self.call('chaos_honeycomb_overlay')


for base in (0x1d100000, 0x1d340000, 0x1c900000):
    b = HoneycombBand(base)
    b.call('chaos_n67_init', 0x3d800000, 65536, 131072, 8192)
    page = b.setup_grid(30)
    b.drive()
    assert not b.overlay() and not b.r32(b.grid+0x1c) & 1
    display, refresh = b.alloc(0x180), b.alloc(32)
    b.w32(0x200b3750, display)
    b.w32(display+4, refresh)
    b.w32(refresh+8, 0xc2467a1)
    b.w32(refresh+12, display)
    b.switch(3)
    assert b.r32(refresh+8) != 0xc2467a1
    manager = b.alloc(0x80)
    b.w32(0x200cacd0, manager)
    b.w8(manager+0x6d, 1)
    entry = b.r32(page+0x48)
    assert entry != 0xc2a31d5
    b.sym['launcher_create_fixture'] = entry
    assert b.call('launcher_create_fixture', page, b.r32(page+0x2c), 0) == 73
    assert b.overlay(), 'outgoing face state prevented launcher entry preparation'
    resume = b.r32(page+0x4c)
    assert resume != 0xc29eff9
    b.sym['launcher_resume_fixture'] = resume
    assert b.call('launcher_resume_fixture', page) == 91 and b.overlay()
    b.top = page
    b.native_timer(refresh)
    b.w8(manager+0x6d, 0)
    assert b.refreshes == [True], 'first native refresh saw the stock grid'
    assert b.overlay(), 'the first ring must be visible before remaining icons are built'
    b.drive()
    overlay = b.overlay()
    assert overlay and b.r32(b.grid+0x1c) & 1
    cells = [o for o, v in b.objects.items() if v['parent'] == overlay]
    assert len(cells) == 30
    first = cells[0]
    input_chain = 256 | 512 | 65536 | 131072
    assert not b.r32(overlay+0x1c) & input_chain
    assert b.r32(overlay+0x1c) & 8192
    assert all(not b.r32(o+0x1c) & 2 for o in cells)
    assert not any(obj in cells for obj, _, _, _ in b.events)
    def first_center():
        icon = b.objects[first]
        return icon['x'] + icon['w']//2, icon['y'] + icon['h']//2
    before = [(b.objects[o]['x'], b.objects[o]['y']) for o in cells[:7]]
    b.send(overlay, 1, (168, 240))
    b.send(overlay, 7, (168, 240))
    b.send(overlay, 8)
    assert b.launches == [20]
    b.send(overlay, 1, (168, 240))
    width_during_drag = b.objects[first]['w']
    b.send(overlay, 2, (210, 205))
    b.native_timer(b.timers[-1])
    after = [(b.objects[o]['x'], b.objects[o]['y']) for o in cells[:7]]
    assert after[0][0] > before[0][0] and after[0][1] < before[0][1]
    b.send(overlay, 2, (110, 355))
    b.native_timer(b.timers[-1])
    assert b.objects[first]['x'] < after[0][0] and b.objects[first]['y'] > after[0][1]
    assert b.objects[first]['w'] == width_during_drag
    assert not b.r32(overlay+0x1c) & input_chain
    request = b.alloc(48)
    b.w8(request+8, 0x36)
    back = b.r32(page+0x64)
    assert back != 0xc2a4f55
    b.sym['launcher_back_fixture'] = back
    assert b.stock_back_dispatch(page, request) == 0xc44d73a
    b.send(overlay, 7)
    b.send(overlay, 8)
    assert b.launches == [20], 'a drag launched an application'
    assert b.call('launcher_back_fixture', page, request) == 1
    b.w8(request+8, 0x33)
    assert b.call('launcher_back_fixture', page, request) == 0
    b.w8(request+8, 0x36)
    b.send(overlay, 1, (5, 240))
    b.send(overlay, 2, (45, 240))
    assert b.stock_back_dispatch(page, request) == 0xc44d73a
    b.send(overlay, 8)
    b.send(overlay, 1, (168, 240))
    b.send(overlay, 8)
    b.native_timer(b.timers[-1])
    # A single fast diagonal sample from the former zoom strip moves both axes.
    assert b.call('chaos_honeycomb_input', 0, 0, 0, 30) == 1
    b.send(overlay, 1, (325, 250))
    b.send(overlay, 2, (150, 100))
    frame = b.alloc(16)
    b.call('chaos_honeycomb_frame', 0, frame)
    assert struct.unpack('<ii', b.u.mem_read(frame, 8)) == (-7, 90)
    b.send(overlay, 2, (290, 190))
    b.call('chaos_honeycomb_frame', 0, frame)
    assert struct.unpack('<ii', b.u.mem_read(frame, 8)) == (133, 180)
    b.send(overlay, 8)
    b.w32(0x200cae00, 0)
    b.w8(manager+0x6d, 1)
    b.native_timer(refresh)
    assert not b.overlay() and overlay not in b.deleted
    b.w8(manager+0x6d, 0)
    b.native_timer(refresh)
    assert b.overlay() == overlay and b.refreshes[-1]
    # Catch inertia before entering the native editing fallback.
    b.send(overlay, 1, (168, 240))
    b.send(overlay, 8)
    b.send(overlay, 1, first_center())
    b.send(overlay, 5)
    b.call('chaos_honeycomb_update', 1)
    assert not b.overlay() and not b.r32(b.grid+0x1c) & 1
    b.switch(3)
    assert not b.overlay() and not b.r32(b.grid+0x1c) & 1
    assert overlay in b.deleted and b.r32(refresh+8) == 0xc2467a1
    assert b.r32(page+0x48) == 0xc2a31d5 and b.r32(page+0x4c) == 0xc29eff9
    assert b.r32(page+0x64) == 0xc2a4f55
    # With one icon, dragging from the centre still moves in both directions.
    # The former zero-width bounds swallowed the drag and passed it to stock.
    frame = b.alloc(16)
    b.call('chaos_honeycomb_input', 0, 0, 0, 1)
    b.call('chaos_honeycomb_input', 1, 168, 240, 1)
    assert b.call('chaos_honeycomb_input', 2, 220, 280, 1) == 1
    b.call('chaos_honeycomb_frame', 0, frame)
    assert struct.unpack('<ii', b.u.mem_read(frame, 8)) == (220, 280)
    assert b.call('chaos_honeycomb_input', 8, 0, 0, 1) == 0
    print(f'PASS honeycomb {base:x}: default off, settings switch, staged layout, two-axis drag, native launch, click suppression, right-edge diagonal drag, first refresh, cache reuse, native swipe-back dispatch and stock editing fallback')

b = HoneycombBand(0x1d100000)
b.call('chaos_n67_init', 0x3d800000, 65536, 131072, 8192)
page = b.setup_grid(1)
b.switch(3)
b.top = page
b.drive()
overlay = b.overlay()
assert overlay

def drag(points, end=8):
    b.send(overlay, 1, points[0])
    for point in points[1:]:
        b.send(overlay, 2, point)
    b.native_timer(b.timers[-1])
    assert not b.back_posts, 'exited before release'
    b.send(overlay, end)
    b.native_timer(b.timers[-1])

# While held, both axes keep tracking after crossing the content bounds.
b.send(overlay, 1, (12, 12))
b.send(overlay, 2, (290, 365))
frame = b.alloc(16)

def center():
    b.call('chaos_honeycomb_frame', 0, frame)
    return struct.unpack('<ii', b.u.mem_read(frame, 8))

# Use a second, smaller move still beyond the old horizontal boundary
# and inside the frame culling margin, then reverse while still held.
b.send(overlay, 2, (162, 232))
assert center() == (318, 460)
b.native_timer(b.timers[-1])
assert center() == (318, 460)
b.send(overlay, 2, (142, 212))
assert center() == (298, 440)
b.send(overlay, 8)
b.native_timer(b.timers[-1])
assert center() == (295, 438)
for _ in range(28):
    b.native_timer(b.timers[-1])
assert center() == (288, 432)
assert not b.back_posts
b.call('chaos_honeycomb_input', 0, 0, 0, 1)

drag([(168, 60), (168, 180), (168, 300)])
drag([(168, 120), (168, 160)])
drag([(168, 120), (168, 210)], end=3)
assert not b.back_posts
drag([(168, 120), (168, 210)])
b.native_timer(b.timers[-1])
assert len(b.back_posts) == 1
request = b.alloc(48)
b.w8(request+8, 0x36)
assert b.stock_back_dispatch(page, request) == 0xc44d73a
print('PASS top pull: reaching the top, short pull and cancellation stay in launcher; deliberate second pull posts one native back')
