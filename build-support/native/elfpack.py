#!/usr/bin/env python3
"""elfpack.py - turn a RELOCATABLE object into a flat injectable module.

    zig cc -c  ->  tickprobe.o  ->  tickprobe.bin + function offsets

Applies same-section Thumb BL/B.W REL relocations before extracting .text.
Rejects undefined/foreign targets, ARM interworking, absolute and unsupported
relocations. Relative calls still need resolution: accepting them without
patching shipped BL . and hung the UI in APP_DIAG=4. The final binary contains
no runtime relocations; its load address is chosen later by the installer.

Usage:
    python elfpack.py <input.o> <output.bin> [--json out.json] [--lua out.lua]
                      [--section .text] [--allow-relocs]
"""
import argparse
import json
import struct
import sys
import hashlib

SHT_PROGBITS = 1
SHT_SYMTAB = 2
SHT_STRTAB = 3
SHT_REL = 9
SHT_RELA = 4
STT_FUNC = 2
STT_SECTION = 3

# A relative relocation still MUST be applied before extracting .text.
# AAELF32: 10=THM_CALL, 30=THM_JUMP24; 11 (not 10) is THM_PC8.
# https://github.com/ARM-software/abi-aa/blob/main/aaelf32/aaelf32.rst
THUMB_BRANCH_RELOCS = {10, 30}


def thumb_branch_addend(code, off):
    hi, lo = struct.unpack_from('<HH', code, off)
    sign = (hi >> 10) & 1
    i1 = 1 ^ ((lo >> 13) & 1) ^ sign
    i2 = 1 ^ ((lo >> 11) & 1) ^ sign
    value = (sign << 24) | (i1 << 23) | (i2 << 22) | ((hi & 1023) << 12) | ((lo & 2047) << 1)
    return value - (1 << 25) if sign else value


def resolve_thumb_branch(code, off, rtype, symbol, code_sec):
    if rtype not in THUMB_BRANCH_RELOCS:
        raise ValueError(f'unsupported relocation type {rtype}')
    if symbol['shndx'] != code_sec['idx'] or not (symbol['value'] & 1):
        raise ValueError('branch target must be a defined Thumb symbol in the same code section')
    if off & 1 or off < 0 or off + 4 > len(code):
        raise ValueError('invalid branch relocation location')
    hi, lo = struct.unpack_from('<HH', code, off)
    expected = 0xD000 if rtype == 10 else 0x9000
    if hi & 0xF800 != 0xF000 or lo & 0xD000 != expected:
        raise ValueError('relocation does not point at the expected Thumb BL/B.W')
    sym_off = (symbol['value'] & ~1) - code_sec['addr']
    if not 0 <= sym_off < len(code):
        raise ValueError('branch symbol outside code section')
    addend = thumb_branch_addend(code, off)
    delta = sym_off + addend - off
    target = off + 4 + delta
    if delta & 1 or not -(1 << 24) <= delta < (1 << 24) or not 0 <= target < len(code):
        raise ValueError('relocated branch is out of range')
    sign = (delta >> 24) & 1
    j1 = 1 ^ ((delta >> 23) & 1) ^ sign
    j2 = 1 ^ ((delta >> 22) & 1) ^ sign
    hi = (hi & 0xF800) | (sign << 10) | ((delta >> 12) & 1023)
    lo = (lo & 0xD000) | (j1 << 13) | (j2 << 11) | ((delta >> 1) & 2047)
    struct.pack_into('<HH', code, off, hi, lo)
    if off + 4 + thumb_branch_addend(code, off) != target:
        raise ValueError('branch encoding verification failed')
    return target


def read_elf(path):
    d = open(path, "rb").read()
    if d[:4] != b"\x7fELF":
        raise SystemExit(f"{path}: not an ELF")
    if d[4] != 1 or d[5] != 1:
        raise SystemExit(f"{path}: need ELF32 little-endian (class={d[4]} data={d[5]})")
    (e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags,
     e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum,
     e_shstrndx) = struct.unpack_from("<HHIIIIIHHHHHH", d, 16)
    raw = [struct.unpack_from("<IIIIIIIIII", d, e_shoff + i * e_shentsize)
           for i in range(e_shnum)]
    names = []
    base = raw[e_shstrndx][4]
    for sh in raw:
        n = sh[0]
        end = d.index(b"\0", base + n)
        names.append(d[base + n:end].decode())
    secs = [{"name": names[i], "type": s[1], "flags": s[2], "addr": s[3],
             "offset": s[4], "size": s[5], "link": s[6], "info": s[7],
             "entsize": s[9], "idx": i} for i, s in enumerate(raw)]
    return d, e_machine, secs


def symtab(d, secs, table_idx=None):
    out = []
    for s in secs:
        if s["type"] != SHT_SYMTAB:
            continue
        if table_idx is not None and s['idx'] != table_idx:
            continue
        strt = secs[s["link"]]
        ent = s["entsize"] or 16
        for k in range(s["size"] // ent):
            off = s["offset"] + k * ent
            nm, val, size, info, oth, shndx = struct.unpack_from("<IIIBBH", d, off)
            b = strt["offset"] + nm
            e = d.index(b"\0", b)
            out.append({"name": d[b:e].decode(), "value": val, "size": size,
                        "type": info & 0xF, "bind": info >> 4, "shndx": shndx})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("obj")
    ap.add_argument("outbin")
    ap.add_argument("--json")
    ap.add_argument("--lua")
    ap.add_argument("--section", default=".text")
    ap.add_argument("--allow-relocs", action="store_true",
                    help="legacy option; unresolved/unsupported relocations are always rejected")
    a = ap.parse_args()

    d, machine, secs = read_elf(a.obj)
    byname = {s["name"]: s for s in secs}
    if machine != 40:
        raise SystemExit(f"machine={machine}, expected 40 (ARM)")
    if a.section not in byname:
        raise SystemExit(f"no {a.section}; have {[s['name'] for s in secs if s['name']]}")
    code_sec = byname[a.section]
    code = bytearray(d[code_sec["offset"]:code_sec["offset"] + code_sec["size"]])

    print(f"object    : {a.obj}")
    print(f"machine   : ARM (40)")
    print(f"section   : {a.section}  addr=0x{code_sec['addr']:X}  size={len(code)}")

    # ---- THE CHECK ------------------------------------------------------------
    print("relocations targeting the code section:")
    bad = []
    found_any = False
    for s in secs:
        if s["type"] not in (SHT_REL, SHT_RELA):
            continue
        tgt = secs[s["info"]] if s["info"] < len(secs) else None
        if not tgt or tgt["name"] != a.section:
            continue
        found_any = True
        ent = s["entsize"] or (12 if s['type'] == SHT_RELA else 8)
        symbols = symtab(d, secs, s['link'])
        cnt = s["size"] // ent
        print(f"  !! .rel{a.section} present with {cnt} entries")
        for k in range(cnt):
            off = s["offset"] + k * ent
            r_off, r_info = struct.unpack_from("<II", d, off)
            rtype = r_info & 0xFF
            rsym = r_info >> 8
            if rtype == 0:
                continue
            try:
                if s['type'] != SHT_REL or rsym >= len(symbols):
                    raise ValueError('unsupported RELA or invalid symbol index')
                symbol = symbols[rsym]
                target = resolve_thumb_branch(code, r_off, rtype, symbol, code_sec)
                print(f"     +0x{r_off:04X} type={rtype} RESOLVED -> {symbol['name']} +0x{target:04X}")
            except ValueError as exc:
                print(f"     +0x{r_off:04X} type={rtype} REJECTED: {exc}")
                bad.append((r_off, rtype))
    if not found_any:
        print("  none -- the code section is fully self-relative")
        print("  => POSITION INDEPENDENCE IS PROVEN, not assumed: an absolute address")
        print("     would have required a relocation entry, and there is no relocation")
        print("     section for this code at all.")
    if bad:
        raise SystemExit(f"FAILED: {len(bad)} unresolved/unsupported relocation(s); module is not injectable")

    # ---- symbols ---------------------------------------------------------------
    funcs = {}
    for s in symtab(d, secs):
        if s["shndx"] == 0 or s["shndx"] >= len(secs):
            continue
        if secs[s["shndx"]]["name"] != a.section:
            continue
        if s["type"] != STT_FUNC:
            continue
        thumb = bool(s["value"] & 1)
        off = (s["value"] & ~1) - code_sec["addr"]
        if off < 0 or off >= len(code) or off % 2:
            continue
        funcs[s["name"]] = {"offset": off, "thumb": thumb, "size": s["size"]}

    open(a.outbin, "wb").write(code)
    print(f"written   : {a.outbin}  ({len(code)} bytes)")
    print(f"functions : {len(funcs)}")
    for nm in sorted(funcs, key=lambda k: funcs[k]["offset"]):
        f = funcs[nm]
        print(f"    +0x{f['offset']:04X}  size={f['size']:<4} thumb={int(f['thumb'])}  {nm}")

    if a.json:
        # ARM ELF mapping symbols distinguish inline data from Thumb code.
        # Disassembling a whole section without these symbols can decode pool
        # bytes as fake PC loads, lose instruction alignment and stop early.
        mapping=sorted((s['value']-code_sec['addr'],s['name'][:2])
                       for s in symtab(d,secs) if s['shndx']==code_sec['idx']
                       and s['name'].split('.')[0] in ('$t','$d'))
        if not mapping or mapping[0]!=(0,'$t'):
            raise SystemExit('missing initial Thumb mapping symbol')
        ranges=[{'offset':off,'size':(mapping[i+1][0] if i+1<len(mapping) else len(code))-off,
                 'kind':'thumb' if kind=='$t' else 'data'} for i,(off,kind) in enumerate(mapping)]
        if any(r['size']<=0 for r in ranges):raise SystemExit('invalid ELF mapping symbols')
        json.dump({"bin": a.outbin, "size": len(code), "base": code_sec["addr"],
                   "functions": funcs,'sha256':hashlib.sha256(code).hexdigest(),'ranges':ranges}, open(a.json, "w"), indent=2)
    if a.lua:
        with open(a.lua, "w") as f:
            f.write("-- generated by native/elfpack.py -- do not edit\n")
            f.write(f"return {{ size = {len(code)}, off = {{\n")
            for nm in sorted(funcs, key=lambda k: funcs[k]["offset"]):
                f.write(f"  {nm} = 0x{funcs[nm]['offset']:X},\n")
            f.write("} }\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
