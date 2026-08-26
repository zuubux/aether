"""
Integration Test for IPC Lifecycle & Socket Payload Boundaries.
Tests UNIX domain socket server/client connection, JSON-RPC 2.0 framing, payload validation,
event broadcasting, and bridge media RPC methods.
"""

import asyncio
import json
import tempfile
import time
from pathlib import Path
import pytest

from ipc.client import WeaverIPCClient
from ipc.server import IPCServer


def test_bridge_media_rpcs(mock_bridge):
    local_path = "/tmp/test_audio.mp3"
    resolved_url = mock_bridge.node.resolve_media_url(local_path)
    assert resolved_url.startswith("file://")
    assert "test_audio.mp3" in resolved_url

    alias_url = mock_bridge.resolve_file_url(local_path)
    assert alias_url == resolved_url

    wf = mock_bridge.node.get_audio_waveform(local_path)
    assert isinstance(wf, list)
    assert len(wf) == 64

    poster = mock_bridge.node.get_video_poster("/tmp/test_video.mp4")
    assert isinstance(poster, str)


@pytest.mark.anyio
async def test_ipc_server_client_handshake_and_rpc():
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = str(Path(tmpdir) / "test_weaver.sock")

        server = IPCServer(socket_path=sock_path)
        await server.start()

        # Connect client directly over UNIX socket
        reader, writer = await asyncio.open_unix_connection(sock_path)

        # Send ping JSON-RPC frame
        req = json.dumps({"jsonrpc": "2.0", "method": "ping", "params": {}, "id": 1}) + "\n"
        writer.write(req.encode("utf-8"))
        await writer.drain()

        resp_line = await reader.readline()
        resp = json.loads(resp_line.decode("utf-8"))

        assert resp["jsonrpc"] == "2.0"
        assert resp["result"] == "pong"
        assert resp["id"] == 1

        # Test broadcast event
        await server.broadcast_event("node_updated", {"id": 101, "name": "updated_node"})

        event_line = await reader.readline()
        event_msg = json.loads(event_line.decode("utf-8"))

        assert event_msg["method"] == "graph_event"
        assert event_msg["params"]["type"] == "node_updated"
        assert event_msg["params"]["data"] == {"id": 101, "name": "updated_node"}

        writer.close()
        await writer.wait_closed()
        await server.stop()
