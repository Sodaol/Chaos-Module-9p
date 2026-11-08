#!/usr/bin/env python3
"""cnocomment.py -- a comment-free COPY of a C file, with line numbers preserved.

WHY THIS IS A BUILD FIX AND NOT A COSMETIC TOOL.
zig cc on this host dies with a bare 0xC0000005 at random, but the rate SCALES WITH
INPUT SIZE.  Measured: a 6-byte file crashed 2/6, a 4700-byte one 6/6.  This project's
C is deliberately dense with justification comments -- every firmware address carries
its evidence and the bug it once caused -- so the file is ~64 KB of which only about a
third is code.  That is the worst possible shape for a compiler that fails more often
the more bytes it reads.

So native/build_module.ps1 compiles THIS instead of the original.  The translation unit
is identical -- the preprocessor deletes comments before the compiler sees them -- but
the compiler reads far fewer bytes.

LINE NUMBERS ARE PRESERVED EXACTLY.  A comment's text is dropped and its newlines are
kept, so a diagnostic still points at the real line of the real file.  That is the whole
reason this does not simply delete comment lines.

An earlier attempt at this replaced comments with SPACES, which preserved the layout and
saved 46 bytes of 63643 -- i.e. nothing at all.  The point is the byte count.

Usage: python cnocomment.py <in.c> <out.c>
"""
import sys


def strip(src):
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            while i < n and src[i] != '\n':      # drop the text, keep the newline
                i += 1
        elif c == '/' and i + 1 < n and src[i + 1] == '*':
            i += 2
            while i + 1 < n and not (src[i] == '*' and src[i + 1] == '/'):
                if src[i] == '\n':
                    out.append('\n')             # a block comment spanning lines still
                i += 1                           # has to keep them
            i += 2
        elif c in '"\'':
            q = c
            out.append(c)
            i += 1
            while i < n:
                if src[i] == '\\':
                    out.append(src[i:i + 2])
                    i += 2
                    continue
                out.append(src[i])
                if src[i] == q:
                    i += 1
                    break
                i += 1
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def dedent(s):
    """Drop leading spaces/tabs and trailing spaces on every line.

    WHY THIS IS WORTH DOING SEPARATELY.  Once comments are gone the file is still 1415
    lines averaging ~14 bytes, and most of what is left is indentation: this source is
    four-space indented and about a third of its bytes are leading blanks.  zig's failure
    rate scales with the number of bytes it reads, so removing whitespace it does not care
    about is free reliability.  19353 -> ~14000 bytes is the difference between "crashed
    on all 40 attempts" and comfortable.

    WHY IT IS SAFE.  Leading and trailing whitespace is never significant in C, with one
    exception: the continuation lines of a multi-line STRING literal.  This module cannot
    contain a string literal at all -- elfpack.py rejects the relocation one would need --
    so that exception cannot arise.  A `\\`-continued #define is unaffected: the
    preprocessor only cares about the tokens.

    Line count is untouched, so diagnostics still point at the real line."""
    out = []
    start = True
    for ch in s:
        if start:
            if ch in ' \t':
                continue
            start = False
        if ch == '\n':
            while out and out[-1] in ' \t':      # trailing blanks before the newline
                out.pop()
            start = True
        out.append(ch)
    return ''.join(out)


src_path, out_path = sys.argv[1], sys.argv[2]
src = open(src_path, encoding='utf-8').read()
out = dedent(strip(src))
assert src.count('\n') == out.count('\n'), 'line count changed'
open(out_path, 'w', encoding='utf-8', newline='').write(out)
a, b = len(src.encode('utf-8')), len(out.encode('utf-8'))
print('  cnocomment: %d -> %d bytes (%.0f%% smaller), %d lines preserved'
      % (a, b, 100.0 * (a - b) / a, out.count('\n') + 1))
