//! Native N67 file engine symbols are implemented by `n67/files` C bridge.
extern "C" {
    pub fn chaos_files_flags(g: u32, p: u32);
    pub fn chaos_files_open(m: u32);
    pub fn chaos_files_create(p: u32, r: u32, s: u32) -> u32;
    pub fn chaos_files_resume(p: u32) -> u32;
    pub fn chaos_files_pause(p: u32) -> u32;
    pub fn chaos_files_destroy(p: u32) -> u32;
    pub fn chaos_files_signal(p: u32, c: u32, a: u32) -> u32;
    pub fn chaos_files_poll();
}
