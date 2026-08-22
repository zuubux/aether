"""
Aether Canvas - IPC Client
Asynchronous UNIX domain socket client for JSON-RPC 2.0 communication with aia_weaver.
"""

import asyncio
import json
import logging
import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger("aia_canvas.ipc")

MAX_PAYLOAD_BYTES = 64 * 1024


class WeaverIPCClient(QObject):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    nodeUpdated = pyqtSignal(dict)
    nodeDeleted = pyqtSignal(dict)
    rpcResponseReceived = pyqtSignal(int, object, str)  # req_id, result, error

    def __init__(self, socket_path: str | None = None):
        super().__init__()
        if socket_path is None:
            runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
            self.socket_path = str(Path(runtime_dir) / "aia_weaver" / "aia_weaver.sock")
        else:
            self.socket_path = socket_path

        self._running = False
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

        self._req_id = 0
        self._pending_callbacks: dict[int, Callable[[Any, str | None], None]] = {}
        self.rpcResponseReceived.connect(self._dispatch_rpc_callback)

    def start(self):
        """Starts the background asyncio worker thread."""
        self._running = True
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

    def _run_event_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._lifecycle_loop())

    def _flush_pending_callbacks(self, error_msg: str):
        for req_id, callback in list(self._pending_callbacks.items()):
            try:
                callback(None, error_msg)
            except Exception as e:
                logger.error(f"Error in pending callback: {e}")
        self._pending_callbacks.clear()

    async def _lifecycle_loop(self):
        while self._running:
            try:
                if not Path(self.socket_path).exists():
                    await asyncio.sleep(1.5)
                    continue

                self._reader, self._writer = await asyncio.open_unix_connection(
                    self.socket_path, limit=MAX_PAYLOAD_BYTES
                )
                logger.info(f"IPC connected to {self.socket_path}")
                self.connected.emit()
                await self._listen_stream()

            except (ConnectionRefusedError, FileNotFoundError, asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError, OSError, KeyError) as e:
                logger.error(f"IPC socket fault: {e}")
                self.disconnected.emit()
                self._flush_pending_callbacks(f"IPC socket fault: {e}")
                await asyncio.sleep(2.0)

    async def _listen_stream(self):
        while self._running and self._reader:
            line = await self._reader.readline()
            if not line:
                break

            frame_size = len(line)
            if frame_size > (MAX_PAYLOAD_BYTES * 0.8):
                logger.warning(f"High IPC payload saturation: {frame_size} bytes")

            try:
                message = json.loads(line.decode("utf-8").strip())
                if not isinstance(message, dict) or "jsonrpc" not in message:
                    logger.error("Malformed IPC payload: missing jsonrpc key")
                    continue
                if "method" not in message and "id" not in message:
                    logger.error("Malformed IPC payload: missing method or id")
                    continue
                self._handle_incoming_message(message)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"Corrupt IPC frame dropped: {e}")
                continue

    def _handle_incoming_message(self, msg: dict):
        # 1. Handle Real-Time Broadcast Events
        if msg.get("method") == "graph_event":
            params = msg.get("params", {})
            event_type = params.get("type")
            data = params.get("data", {})
            if event_type == "node_updated":
                self.nodeUpdated.emit(data)
            elif event_type == "node_deleted":
                self.nodeDeleted.emit(data)

        # 2. Handle RPC Responses (Matched by ID)
        elif "id" in msg and msg["id"] is not None:
            req_id = int(msg["id"])
            result = msg.get("result")
            error = msg.get("error", {}).get("message") if "error" in msg else ""
            self.rpcResponseReceived.emit(req_id, result, error)

    def _dispatch_rpc_callback(self, req_id: int, result: Any, error: str):
        callback = self._pending_callbacks.pop(req_id, None)
        if callback:
            callback(result, error if error else None)

    def call_rpc_sync(self, method: str, params: dict, callback: Callable | None = None, timeout: float = 5.0):
        """Dispatches an asynchronous RPC request from Qt without blocking the UI thread."""
        if not self._running or not self._loop or not self._writer:
            if callback:
                callback(None, "IPC socket not connected")
            return

        self._req_id += 1
        req_id = self._req_id
        if callback:
            self._pending_callbacks[req_id] = callback
            # Schedule a timeout to flush this specific callback
            self._loop.call_later(timeout, self._handle_rpc_timeout, req_id)

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": req_id,
        }

        asyncio.run_coroutine_threadsafe(self._send_payload(payload), self._loop)

    def _handle_rpc_timeout(self, req_id: int):
        callback = self._pending_callbacks.pop(req_id, None)
        if callback:
            try:
                callback(None, "RPC request timed out")
            except Exception as e:
                logger.error(f"Error in RPC timeout callback: {e}")

    async def _send_payload(self, payload: dict):
        if self._writer:
            try:
                line = json.dumps(payload) + "\n"
                self._writer.write(line.encode("utf-8"))
                await self._writer.drain()
            except Exception as e:
                logger.error(f"Failed to send IPC request: {e}")