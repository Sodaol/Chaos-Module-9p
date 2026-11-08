//! N67 adapter for the upstream Chaos v1.1.7 honeycomb geometry (AGPL-3.0).
#[path = "honeycomb_layout.rs"]
mod layout;
use layout::{Camera, Point};

static mut CAMERA: Camera = Camera::new();
static mut LAST: Point = Point { x: 0, y: 0 };
static mut START: Point = Point { x: 0, y: 0 };
static mut TOP_PULL: bool = false;
static mut EXIT_DISTANCE: bool = false;
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
        0 => { CAMERA = Camera::new(); TOP_PULL = false; EXIT_DISTANCE = false; return 1; }
        1 => {
            START = point;
            EXIT_DISTANCE = false;
            TOP_PULL = CAMERA.at_top(count);
            CAMERA.press();
        },
        2 => {
            let down = y - START.y;
            let across = (x - START.x).abs();
            EXIT_DISTANCE = TOP_PULL && down >= 72 && down >= across * 2;
            let changed = CAMERA.drag(Point { x: x - LAST.x, y: y - LAST.y }, count);
            LAST = point;
            if changed { crate::ui_activity::note_scroll(); }
            return changed as u32;
        }
        3 => { TOP_PULL = false; EXIT_DISTANCE = false; CAMERA.cancel(); },
        8 => {
            let exit = EXIT_DISTANCE;
            TOP_PULL = false;
            EXIT_DISTANCE = false;
            if exit { CAMERA.cancel(); } else { CAMERA.release(); }
            return exit as u32;
        },
        11 => {
            let changed = CAMERA.tick(count);
            if changed { crate::ui_activity::note_scroll(); }
            return changed as u32;
        }
        13 => return CAMERA.moving() as u32,
        7 => return CAMERA.can_click() as u32,
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
