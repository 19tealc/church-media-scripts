#!/usr/bin/env python3
"""
OSC listener for testing what the DiGiCo board actually sends.

Run this with Reaper CLOSED (Reaper binds the same port when it launches),
fire the macro on the console, and this prints the source IP and the OSC
message that arrived. That tells you the board is reaching the Mac and
exactly what address it's sending.

    python3 osc_listen.py            # listen on 9000
    python3 osc_listen.py 8000       # or any other port

Ctrl-C to stop.
"""

import socket
import sys
import datetime


def parse_osc(data: bytes):
    """Minimal OSC parse: address string, then type tags and args."""
    try:
        end = data.index(b"\x00")
        address = data[:end].decode("ascii", "replace")
    except ValueError:
        return repr(data), []

    # Addresses are padded to a 4-byte boundary
    pos = (end + 4) & ~3
    args = []

    if pos < len(data) and data[pos:pos + 1] == b",":
        tag_end = data.index(b"\x00", pos)
        tags = data[pos + 1:tag_end].decode("ascii", "replace")
        pos = (tag_end + 4) & ~3

        for t in tags:
            if t == "i" and pos + 4 <= len(data):
                args.append(int.from_bytes(data[pos:pos + 4], "big", signed=True))
                pos += 4
            elif t == "f" and pos + 4 <= len(data):
                import struct
                args.append(round(struct.unpack(">f", data[pos:pos + 4])[0], 4))
                pos += 4
            elif t == "s":
                s_end = data.index(b"\x00", pos)
                args.append(data[pos:s_end].decode("ascii", "replace"))
                pos = (s_end + 4) & ~3
            elif t == "T":
                args.append(True)
            elif t == "F":
                args.append(False)

    return address, args


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("0.0.0.0", port))
    except OSError as e:
        raise SystemExit(
            f"Could not listen on port {port}: {e}\n"
            "If Reaper is running, close it first — it binds this port."
        )

    print(f"Listening for OSC on 0.0.0.0:{port}  (Ctrl-C to stop)")
    print("Fire the macro on the console now.\n")

    count = 0
    try:
        while True:
            data, (src_ip, src_port) = sock.recvfrom(4096)
            count += 1
            address, args = parse_osc(data)
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] #{count} from {src_ip}:{src_port}")
            print(f"           {address}  {args if args else ''}")
    except KeyboardInterrupt:
        print(f"\nStopped. {count} message(s) received.")
        if count == 0:
            print("Nothing arrived — check the board's OSC destination IP and port,")
            print("and that the Mac and console are on the same network.")


if __name__ == "__main__":
    main()
