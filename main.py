#!/usr/bin/env python3
"""news-image-20261125 — copy the entry image to the output directory.

Revision history:
- v1 (2026-11-25): fresh stdlib-only copy program — PNG magic, IHDR dims
  <= 1024x1024, size <= 1 MiB, per-chunk CRC walk to IEND, expected
  sha256, byte-for-byte copy + re-verification of the output.
- v2 (2026-11-25): added revision-history comment block and an IDAT
  presence check — a PNG with no image-data chunk is rejected.

Reads entry.png (1024x1024 newspaper front page summing up Wednesday
25 November 2026 world news: Ukraine sea strike on the Sparta II, Huawei
convicted, Houthi drone hits Riyadh tower, Giuliani medal, CIA/ODNI breach,
Thanksgiving turkey pardon), validates it thoroughly, then copies it
byte-for-byte to $MAKEFUN_OUTPUT_DIR (default /output) and re-verifies
the written copy.

Standard library only: hashlib, os, struct, sys, zlib.
"""

import hashlib
import os
import struct
import sys
import zlib

EXPECTED_SHA256 = (
    "822b68597e171e5d1113e82a190b9924039391ec0673ea2458fa902dd24d936f"
)
MAX_BYTES = 1 << 20          # 1 MiB
MAX_DIM = 1024               # max width/height in pixels
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def fail(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def validate_png(data):
    """Validate PNG structure; return (width, height)."""
    if len(data) > MAX_BYTES:
        fail(f"entry.png too large: {len(data)} bytes > {MAX_BYTES}")
    if len(data) < 8 or data[:8] != PNG_MAGIC:
        fail("bad PNG magic")
    # Walk chunks, checking CRCs, until the terminating IEND chunk.
    pos = 8
    width = height = None
    seen_ihdr = False
    seen_idat = False
    seen_iend = False
    while pos < len(data):
        if pos + 8 > len(data):
            fail("truncated chunk header")
        length, ctype = struct.unpack(">I4s", data[pos:pos + 8])
        if pos + 12 + length > len(data):
            fail(f"truncated chunk {ctype!r}")
        chunk = data[pos + 4:pos + 8 + length]
        stored_crc, = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])
        if zlib.crc32(chunk) & 0xFFFFFFFF != stored_crc:
            fail(f"bad CRC in chunk {ctype!r}")
        if ctype == b"IDAT":
            if length == 0:
                fail("empty IDAT chunk")
            seen_idat = True
        if ctype == b"IHDR":
            if seen_ihdr:
                fail("duplicate IHDR")
            seen_ihdr = True
            width, height = struct.unpack(">II", data[pos + 8:pos + 16])
            if width > MAX_DIM or height > MAX_DIM:
                fail(f"image too large: {width}x{height}")
        if ctype == b"IEND":
            seen_iend = True
            if pos + 12 + length != len(data):
                fail("trailing data after IEND")
            break
        pos += 12 + length
    if not seen_ihdr:
        fail("missing IHDR")
    if not seen_idat:
        fail("missing IDAT")
    if not seen_iend:
        fail("missing IEND")
    return width, height


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "entry.png")
    try:
        with open(src, "rb") as f:
            data = f.read()
    except OSError as e:
        fail(f"cannot read entry.png: {e}")
    width, height = validate_png(data)
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        fail(f"entry.png sha256 mismatch: {digest}")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, "entry.png")
    with open(dst, "wb") as f:
        f.write(data)
    with open(dst, "rb") as f:
        written = f.read()
    if hashlib.sha256(written).hexdigest() != EXPECTED_SHA256:
        fail("written copy sha256 mismatch")
    print(f"wrote {dst} ({width}x{height}, {len(written)} bytes)")


if __name__ == "__main__":
    main()
