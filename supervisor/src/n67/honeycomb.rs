//! N67 adapter for the upstream Chaos v1.1.7 honeycomb geometry (AGPL-3.0).
#[path = "honeycomb_layout.rs"]
mod layout;
use layout::{Camera, Point};

static mut CAMERA: Camera = Camera::new();
static mut LAST: Point = Point { x: 0, y: 0 };
static mut START: Point = Point { x: 0, y: 0 };
static mut EDGE_BACK: bool = false;
static mut ENABLED: bool = false;

extern "C" {
    fn chaos_honeycomb_update(enabled: u32);
    pub(crate) fn chaos_honeycomb_overlay() -> u32;
}

pub(crate) unsafe fn enabled() -> bool { ENABLED }
pub(crate) unsafe fn set_enabled(on: bool) { ENABLED = on; }
pub(crate) unsafe fn tick() {
    chaos_honeycomb_update(ENABLED as u32);
}

#[no_mangle]
unsafe extern "C" fn chaos_honeycomb_input(code: u32, x: i32, y: i32, count: usize) -> u32 {
    let point = Point { x, y };
    match code {
        0 => { CAMERA = Camera::new(); return 1; }
        1 => { START = point; EDGE_BACK = false; CAMERA.press_at(point); },
        2 => {
            if START.x <= 12 && x - START.x >= 24 && x - START.x > (y - START.y).abs() {
                EDGE_BACK = true;
                CAMERA.cancel();
            }
            let changed = CAMERA.drag(Point { x: x - LAST.x, y: y - LAST.y }, count);
            LAST = point;
            if changed { crate::ui_activity::note_scroll(); }
            return changed as u32;
        }
        3 => CAMERA.cancel(),
        8 => CAMERA.release(),
        11 => {
            let changed = CAMERA.tick(count);
            if changed { crate::ui_activity::note_scroll(); }
            return changed as u32;
        }
        12 => return EDGE_BACK as u32,
        13 => return CAMERA.moving() as u32,
        7 => return (!EDGE_BACK && CAMERA.can_click()) as u32,
        _ => {}
    }
    LAST = point;
    0
}

#[no_mangle]
unsafe extern "C" fn chaos_honeycomb_frame(index: usize, out: *mut i32) {
    let f = CAMERA.frame(index);
    for (i, v) in [f.x, f.y, f.diameter, f.visible as i32].into_iter().enumerate() {
        out.add(i).write(v);
    }
}
