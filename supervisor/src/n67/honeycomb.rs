//! N67 adapter for the upstream Chaos v1.1.7 honeycomb geometry (AGPL-3.0).
#[path = "honeycomb_layout.rs"]
mod layout;
use layout::{Camera, Point, Route};

static mut CAMERA: Camera = Camera::new();
static mut LAST: Point = Point { x: 0, y: 0 };
static mut ENABLED: bool = false;

extern "C" {
    fn chaos_honeycomb_update(enabled: u32);
    pub(crate) fn chaos_honeycomb_overlay() -> u32;
}

pub(crate) unsafe fn enabled() -> bool { ENABLED }
pub(crate) unsafe fn set_enabled(on: bool) { ENABLED = on; }
pub(crate) unsafe fn tick() {
    let active = ENABLED && crate::fw_api::watchface_is_on() == 0;
    chaos_honeycomb_update(active as u32);
}

#[no_mangle]
unsafe extern "C" fn chaos_honeycomb_input(code: u32, x: i32, y: i32, count: usize) -> u32 {
    let point = Point { x, y };
    match code {
        0 => { CAMERA = Camera::new(); return 1; }
        1 => CAMERA.press_at(point),
        2 => {
            let changed = CAMERA.drag(Point { x: x - LAST.x, y: y - LAST.y }, count);
            LAST = point;
            return changed as u32;
        }
        3 => CAMERA.cancel(),
        8 => CAMERA.release(),
        11 => return CAMERA.tick(count) as u32,
        12 => return (CAMERA.route() != Route::Cloud) as u32,
        7 => return (CAMERA.route() == Route::Cloud && CAMERA.can_click()) as u32,
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
