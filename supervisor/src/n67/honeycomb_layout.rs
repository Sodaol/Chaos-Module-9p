//! Integer-only hexagonal launcher geometry and pointer state. No firmware I/O.

pub(crate) const MAX_ICONS: usize = 192;
pub(crate) const WIDTH: i32 = 336;
pub(crate) const HEIGHT: i32 = 480;
const ONE: i32 = 256;
const DRAG_THRESHOLD: i32 = 10;

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
#[repr(C)]
pub(crate) struct Point {
    pub x: i32,
    pub y: i32,
}

/// Stable app order, filling complete hexagonal rings around the first app.
pub(crate) fn position(index: usize) -> Point {
    let mut left = index.min(MAX_ICONS - 1);
    if left == 0 {
        return Point::default();
    }
    left -= 1;
    let mut ring = 1;
    while left >= 6 * ring {
        left -= 6 * ring;
        ring += 1;
    }
    let mut q = -(ring as i32);
    let mut r = ring as i32;
    for (dq, dr) in [(0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0)] {
        let steps = left.min(ring);
        q += dq * steps as i32;
        r += dr * steps as i32;
        left -= steps;
        if left == 0 {
            break;
        }
    }
    Point {
        x: q * 96 + r * 48,
        y: r * 83,
    }
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct Frame {
    pub x: i32,
    pub y: i32,
    pub diameter: i32,
    pub visible: bool,
}

pub(crate) fn frame(index: usize, pan: Point) -> Frame {
    let p = position(index);
    let dx = p.x + pan.x;
    let dy = p.y + pan.y;
    let visible = dx.abs() < WIDTH / 2 + 56 && dy.abs() < HEIGHT / 2 + 56;
    if !visible {
        return Frame { x: 0, y: 0, diameter: 1, visible: false };
    }
    let nx = dx * 256 / (WIDTH / 2);
    let ny = dy * 256 / (HEIGHT / 2);
    let radial = (nx * nx + ny * ny).min(65536);
    Frame {
        x: WIDTH / 2 + dx,
        y: HEIGHT / 2 + dy,
        diameter: 84 - 56 * radial / 65536,
        visible,
    }
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct Camera {
    pan: Point,
    velocity: Point,
    pending: Point,
    pressed: bool,
    dragged: bool,
    stop_tap: bool,
    travel: i32,
    bounds_count: usize,
    min: Point,
    max: Point,
}

impl Default for Camera {
    fn default() -> Self {
        Self::new()
    }
}

impl Camera {
    pub(crate) const fn new() -> Self {
        Self {
            pan: Point { x: 0, y: 0 },
            velocity: Point { x: 0, y: 0 },
            pending: Point { x: 0, y: 0 },
            pressed: false,
            dragged: false,
            stop_tap: false,
            travel: 0,
            bounds_count: usize::MAX,
            min: Point { x: 0, y: 0 },
            max: Point { x: 0, y: 0 },
        }
    }
    pub(crate) fn pan(&self) -> Point {
        Point {
            x: self.pan.x / ONE,
            y: self.pan.y / ONE,
        }
    }
    pub(crate) fn frame(&self, index: usize) -> Frame {
        frame(index, self.pan())
    }

    pub(crate) fn moving(&self) -> bool {
        self.pressed || self.velocity.x != 0 || self.velocity.y != 0
    }
    pub(crate) fn press(&mut self) {
        // A tap which catches a moving cloud stops it without launching an app.
        self.stop_tap = self.velocity.x != 0 || self.velocity.y != 0;
        self.velocity = Point::default();
        self.pending = Point::default();
        self.pressed = true;
        self.dragged = false;
        self.travel = 0;
    }
    pub(crate) fn drag(&mut self, d: Point, count: usize) -> bool {
        if !self.pressed {
            return false;
        }
        self.travel = (self.travel + d.x.abs() + d.y.abs()).min(1024);
        self.pending.x += d.x;
        self.pending.y += d.y;
        if !self.dragged && self.travel < DRAG_THRESHOLD {
            return false;
        }
        self.dragged = true;
        let old = self.pan;
        self.pan.x += self.pending.x * ONE;
        self.pan.y += self.pending.y * ONE;
        self.pending = Point::default();
        self.velocity = Point {
            x: d.x.clamp(-24, 24) * ONE,
            y: d.y.clamp(-24, 24) * ONE,
        };
        self.clamp(count);
        self.pan != old
    }
    pub(crate) fn release(&mut self) {
        self.pressed = false;
        // Keep the drag latch until the NEXT press, including SHORT_CLICKED.
        if !self.dragged {
            self.velocity = Point::default();
        }
    }
    pub(crate) fn cancel(&mut self) {
        self.release();
        self.velocity = Point::default();
        self.stop_tap = true;
    }
    pub(crate) fn can_click(&self) -> bool {
        !self.dragged && !self.stop_tap
    }
    pub(crate) fn tick(&mut self, count: usize) -> bool {
        if self.pressed || (self.velocity.x == 0 && self.velocity.y == 0) {
            return false;
        }
        self.pan.x += self.velocity.x;
        self.pan.y += self.velocity.y;
        self.clamp(count);
        self.velocity.x = self.velocity.x * 7 / 8;
        self.velocity.y = self.velocity.y * 7 / 8;
        if self.velocity.x.abs() < 64 {
            self.velocity.x = 0;
        }
        if self.velocity.y.abs() < 64 {
            self.velocity.y = 0;
        }
        true
    }
    fn update_bounds(&mut self, count: usize) {
        let count = count.min(MAX_ICONS);
        if self.bounds_count != count {
            self.min = Point::default();
            self.max = Point::default();
            for i in 0..count {
                let p = position(i);
                self.min.x = self.min.x.min(p.x);
                self.min.y = self.min.y.min(p.y);
                self.max.x = self.max.x.max(p.x);
                self.max.y = self.max.y.max(p.y);
            }
            self.bounds_count = count;
        }
    }

    fn top_limit(&self) -> i32 {
        -self.min.y * ONE + (HEIGHT / 2 - 48) * ONE
    }

    pub(crate) fn at_top(&mut self, count: usize) -> bool {
        self.update_bounds(count);
        self.pan.y >= self.top_limit()
    }

    fn clamp(&mut self, count: usize) {
        self.update_bounds(count);
        let x = self
            .pan
            .x
            .clamp(-self.max.x * ONE - (WIDTH / 2 - 48) * ONE, -self.min.x * ONE + (WIDTH / 2 - 48) * ONE);
        let y = self
            .pan
            .y
            .clamp(-self.max.y * ONE - (HEIGHT / 2 - 48) * ONE, self.top_limit());
        if x != self.pan.x {
            self.velocity.x = 0;
        }
        if y != self.pan.y {
            self.velocity.y = 0;
        }
        self.pan = Point { x, y };
    }
}
