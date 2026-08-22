#!/usr/bin/env python3
"""
scripts/probe.py
Standalone CLI diagnostic tool to query and inspect a running aia_weaver daemon.
"""

import json
import os
import socket
import sys
from pathlib import Path


def get_socket_path() -> Path:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    return Path(runtime_dir) / "aia_weaver" / "aia_weaver.sock"


def send_rpc(method: str, params: dict | None = None) -> None:
    socket_path = get_socket_path()

    if not socket_path.exists():
        print(f"[!] Error: Socket not found at {socket_path}")
        print("    Is the aia_weaver daemon running?")
        sys.exit(1)

    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": 1,
    }

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(str(socket_path))
            # Send newline-delimited JSON frame
            client.sendall(json.dumps(payload).encode("utf-8") + b"\n")

            # Read response
            response_data = client.recv(65536)
            if not response_data:
                print("[!] Empty response received from daemon.")
                return

            response = json.loads(response_data.decode("utf-8"))
            print(json.dumps(response, indent=2))

    except Exception as e:
        print(f"[!] Connection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Default to 'ping' if no argument passed
    method = sys.argv[1] if len(sys.argv) > 1 else "ping"

    # Optional second argument for JSON params
    params = {}
    if len(sys.argv) > 2:
        try:
            params = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            print("[!] Error: Second argument must be valid JSON params.")
            sys.exit(1)

    send_rpc(method, params)