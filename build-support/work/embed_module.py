#!/usr/bin/env python3
"""embed_module.py - embed a compiled module as an exact Lua binary expression.

Uses bounded LZSS when it is smaller than raw literals. Python checks the
round trip, and the build evaluates the shipped expression with actual Lua
and compares every byte against the native module.

    python embed_module.py <main.lua.in> <module.bin> <main.lua.out>

WHY THE BYTES TRAVEL INSIDE main.lua AT ALL
    The first design stored the module in the container's `shellpp_ii.bin` slot and
    read it back on the device with io.open(SCRIPT_PATH .. "shellpp_ii.bin").  That
    FAILED ON HARDWARE: the face runtime does not materialise every container record
    into SCRIPT_PATH, so the file was simply not there.  main.lua is guaranteed to
    arrive, because the face is running it.

WHY RAW LONG-BRACKET BYTES RATHER THAN HEX
    Hex costs TWO characters per byte.  At 3576 bytes that is 7152 characters of a
    51780-byte Lua slot -- 13.8% of the entire face spent on the ENCODING of one
    string, and it doubles the price of every byte of native code added.  The build
    ran out of slot by 2020 bytes with correct code.

    Lua long strings normalize CR and CR/LF pairs. Raw CR bytes therefore must
    be emitted as escaped short-string literals between long-bracket chunks.
    Each chunk without CR retains one source byte per module byte:

      * pack.py's strip_lua consumes the WHOLE long string at its opening bracket
        (`line.append(s[i:end])`), so `--`, quotes and newlines inside the payload
        are never interpreted.  Its per-line .rstrip()/skip-blank logic only sees
        the text AFTER the closing bracket.

      * The closing sequence cannot occur in the payload: the bracket level is
        searched for at build time.  Only the CLOSER terminates a long string in
        Lua -- brackets do not nest -- but the opener is avoided too, so the file
        stays readable by any tool that does scan naively.

      * Lua DROPS ONE NEWLINE immediately after the opening bracket, so a payload
        that begins with 0x0A gets a spare newline prepended to absorb that.

WHY THE PLACEHOLDER KEEPS ITS QUOTES IN THE MATCH PATTERN
    main.lua declares `local MODULE_BIN = '@@MODULE_PAYLOAD@@'` and this script
    replaces the QUOTED form, quotes included, with the bracketed bytes.  A build
    that forgets this step therefore ships the 18-character literal string
    '@@MODULE_PAYLOAD@@' rather than a syntax error: load_module() compares its
    length against MODULE_SIZE and refuses it loudly.  Same guarantee as the hex
    placeholder had, without the 2x cost.

Usage: also verifies the result -- it re-reads the output, extracts the long string
back out, and refuses to write if it is not byte-identical to the module.
"""
import sys
import re
from collections import defaultdict, deque

PLACEHOLDER = b"'@@MODULE_PAYLOAD@@'"
MAX_LEVEL = 12
LZ_PREFIX = b'(function(s,z)'
LZ_DECODER = b'''(function(s,z)
local o,i='',1
while i<=#s do
local t=s:byte(i);i=i+1
if t<128 then
assert(t>0 and i+t-1<=#s);o=o..s:sub(i,i+t-1);i=i+t
else
assert(i+1<=#s);local d=s:byte(i)+s:byte(i+1)*256;i=i+2
local n=t-128+4;assert(d>0 and d<=#o)
local p=o:sub(#o-d+1,#o-d+n)
if #p<n then p=p:rep((n+#p-1)//#p):sub(1,n) end
o=o..p
end
assert(#o<=z)
end
assert(#o==z);return o
end)('''


def compress(data: bytes) -> bytes:
    """Bounded LZSS: literal 1..127; match 128..255 => 4..131 + u16 distance."""
    positions = defaultdict(lambda: deque(maxlen=64))
    out, literals = bytearray(), bytearray()
    def flush():
        if literals:
            out.append(len(literals)); out.extend(literals); literals.clear()
    i = 0
    while i < len(data):
        best, distance = 0, 0
        if i + 4 <= len(data):
            for p in reversed(positions[data[i:i+4]]):
                if i-p > 65535:
                    break
                n = 4
                while n < 131 and i+n < len(data) and data[p+n] == data[i+n]:
                    n += 1
                if n > best:
                    best, distance = n, i-p
        step = best if best >= 4 else 1
        if best >= 4:
            flush(); out.extend((128+best-4, distance&255, distance>>8))
        else:
            literals.append(data[i])
            if len(literals) == 127:
                flush()
        for p in range(i, i+step):
            positions[data[p:p+4]].append(p)
        i += step
    flush()
    return bytes(out)


def decompress(data: bytes, size: int) -> bytes:
    out, i = bytearray(), 0
    while i < len(data):
        token = data[i]; i += 1
        if token < 128:
            if not token or i+token > len(data):
                raise ValueError('truncated/empty LZ literal')
            out.extend(data[i:i+token]); i += token
        else:
            if i+2 > len(data):
                raise ValueError('truncated LZ match')
            distance = data[i] + data[i+1]*256; i += 2
            if not 0 < distance <= len(out):
                raise ValueError('invalid LZ distance')
            for _ in range(token-128+4):
                out.append(out[-distance])
        if len(out) > size:
            raise ValueError('LZ output overflow')
    if len(out) != size:
        raise ValueError('LZ output size mismatch')
    return bytes(out)


def module_expression(data: bytes) -> bytes:
    raw = binary_expression(data)
    packed = LZ_DECODER + binary_expression(compress(data)) + b',' + str(len(data)).encode() + b')'
    return packed if len(packed) < len(raw) else raw


def long_bracket(data: bytes) -> bytes:
    """Wrap `data` in the shortest Lua long bracket that cannot close early."""
    lead = b"\n" if data[:1] == b"\n" else b""
    for k in range(MAX_LEVEL + 1):
        op = b"[" + b"=" * k + b"["
        cl = b"]" + b"=" * k + b"]"
        # A suffix of the payload can combine with the closer's prefix to make
        # an earlier closer (e.g. payload ends ']' and level-0 close is ']]').
        if cl not in data and op not in data and (data + cl).find(cl) == len(data):
            return op + lead + data + cl
    raise SystemExit(f"no long-bracket level up to {MAX_LEVEL} is safe for this payload")


def extract(blob: bytes, start: int = 0):
    """Inverse of long_bracket: (payload, end_offset) for the first long string."""
    at = blob.find(b"[", start)
    while at >= 0:
        k, i = 0, at + 1
        while i < len(blob) and blob[i:i + 1] == b"=":
            k += 1
            i += 1
        if blob[i:i + 1] == b"[":
            op_end = i + 1
            cl = b"]" + b"=" * k + b"]"
            end = blob.find(cl, op_end)
            if end < 0:
                raise SystemExit("unterminated long string in the generated source")
            # Lua's lexer normalizes ALL CR/LF sequences in long strings.
            body = re.sub(b'\r\n|\n\r|\r', b'\n', blob[op_end:end])
            if body[:1] == b"\n":
                body = body[1:]
            return body, end + len(cl)
        at = blob.find(b"[", at + 1)
    raise SystemExit("no long string found in the generated source")


def binary_expression(data: bytes) -> bytes:
    """Long-bracket chunks separated by escaped CRs: Lua never sees raw CRs."""
    parts = []
    for i, part in enumerate(data.split(b'\r')):
        if i:
            parts.append(b"'\\r'")
        if part or not parts:
            parts.append(long_bracket(part))
    # A large Thumb image can have hundreds of CR separators. One huge '..'
    # expression needs a register for every operand and exceeds Lua's 255-register
    # limit even though its local count passes. Tables flush each 50 values;
    # table.concat preserves the exact bytes with a bounded compiler register set.
    if len(parts)>32:
        return b'table.concat({' + b','.join(parts) + b'})'
    return b'..'.join(parts)


def extract_expression(blob: bytes, start: int):
    if blob[start:].startswith(LZ_PREFIX):
        if blob[start:start+len(LZ_DECODER)] != LZ_DECODER:
            raise ValueError('unrecognized LZ decoder')
        encoded, at = extract_expression(blob, start+len(LZ_DECODER))
        match = re.match(rb',(\d+)\)', blob[at:])
        if not match:
            raise ValueError('LZ decoded size missing')
        return decompress(encoded, int(match[1])), at+match.end()
    if blob[start:].startswith(b'table.concat({'):
        parts,at=[],start+len(b'table.concat({')
        while True:
            part,at=extract_expression(blob,at); parts.append(part)
            if blob[at:at+2]==b'})': return b''.join(parts),at+2
            if blob[at:at+1]!=b',': raise ValueError('binary table separator missing')
            at+=1
    parts, at = [], start
    while True:
        if blob[at:at + 4] == b"'\\r'":
            parts.append(b'\r')
            at += 4
        elif blob[at:at + 1] == b'[':
            part, at = extract(blob, at)
            parts.append(part)
        else:
            raise ValueError(f'unsupported binary literal at {at}')
        if blob[at:at + 2] != b'..':
            return b''.join(parts), at
        at += 2


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    src_path, mod_path, out_path = sys.argv[1:4]

    src = open(src_path, "rb").read()
    mod = open(mod_path, "rb").read()

    n = src.count(PLACEHOLDER)
    if n != 1:
        raise SystemExit(f"{src_path}: expected exactly one {PLACEHOLDER!r}, found {n}")

    payload = module_expression(mod)
    at = src.find(PLACEHOLDER)
    out = src.replace(PLACEHOLDER, payload)

    # Round trip against the text we are about to write, not against `payload`:
    # extract() re-derives the bytes the way the Lua lexer would, so it also proves
    # the leading-newline rule and the bracket level are right.
    #
    # ⚠ IT MUST START AT `at`, NOT AT 0.  A first cut searched from the top of the
    # file, hit the first '[' anywhere in the source -- an index expression, a
    # comment -- and reported a 5-byte "round trip mismatch".  The substitution
    # point is the only place the long string can be, and it is known exactly.
    got, _ = extract_expression(out, at)
    if got != mod:
        raise SystemExit(f"long-bracket round trip mismatch: {len(got)} vs {len(mod)} bytes")

    open(out_path, "wb").write(out)

    lvl = payload.count(b"=", 0, payload.find(b"["))
    print(f"  module   : {mod_path}  ({len(mod)} bytes)")
    print(f"  encoding : {'LZSS' if payload.startswith(LZ_PREFIX) else 'raw'} long brackets + escaped CR ({len(payload)} source bytes)")
    print(f"  source   : {len(src)} -> {len(out)} bytes")
    print(f"  round trip verified: extracted {len(got)} identical bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
