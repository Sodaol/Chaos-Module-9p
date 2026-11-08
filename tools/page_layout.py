from pathlib import Path
import re
R=Path(__file__).resolve().parents[1]
PAGE_COUNT=int(re.search(r"pub const PAGE_COUNT: usize = (\d+);",(R/'supervisor/src/state.rs').read_text('utf8'))[1])
DESCRIPTOR_SIZE=0x2000
assert 0x1000+(PAGE_COUNT-1)*112<=DESCRIPTOR_SIZE
assert 0x800+PAGE_COUNT*4<=0x1000
