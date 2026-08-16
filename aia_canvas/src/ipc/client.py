"""
Aether Canvas - IPC Client for aia_weaver
Handles asynchronous UNIX domain socket communication and secure JSON-RPC 2.0 validation.
"""

import os
import json
import asyncio
import threading
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger("aia_canvas.ipc")

MAX_PAYLOAD_BYTES = 64 * 1024  # 64 KB safety buffer


class WeaverIPCClient(QObject):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    nodeUpdated = pyqtSignal(dict)
    nodeDeleted = pyqtSignal(dict)
    errorOccurred = pyqtSignal(str)

    def __init__(self, socket_path: Optional[str] = None):
        super().__init__()
        self.socket_path = socket_path or self._resolve_socket_path()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._request_counter = 0
        self._running = False

    @staticmethod
    def _resolve_socket_path() -> str:
        xdg_runtime = os.environ.get("XDG_RUNTIME_DIR")
        if xdg_runtime:
            return str(Path(xdg_runtime) / "aia_weaver" / "aia_weaver.sock")
        return f"/run/user/{os.getuid()}/aia_weaver/aia_weaver.sock"

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._cleanup(), self._loop)

    def _run_event_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._lifecycle_loop())

    async def _lifecycle_loop(self):
        while self._running:
            try:
                if not Path(self.socket_path).exists():
                    await asyncio.sleep(2.0)
                    continue

                self._reader, self._writer = await asyncio.open_unix_connection(
                    self.socket_path, limit=MAX_PAYLOAD_BYTES
                )
                logger.info(f"IPC connected to {self.socket_path}")
                self.connected.emit()
                await self._listen_stream()

            except (ConnectionRefusedError, FileNotFoundError, asyncio.IncompleteReadError):
                # Throttle error spam if weaver isn't running yet
                if hasattr(self, '_last_warned') and not self._last_warned:
                    logger.warning("IPC unavailable or disconnected. Retrying in background...")
                    self._last_warned = True
                self.disconnected.emit()
            except Exception as e:
                logger.error(f"IPC socket fault: {e}")
                self.disconnected.emit()

            if self._writer:
                try:
                    self._writer.close()
                    await self._writer.wait_closed()
                except Exception:
                    pass
                self._writer = None
                self._reader = None

            if self._running:
                await asyncio.sleep(2.0)

    async def _listen_stream(self):
        while self._running and self._reader:
            line = await self._reader.readline()
            if not line:
                break
                
            frame_size = len(line)
            if frame_size > (MAX_PAYLOAD_BYTES * 0.8):
                logger.warning(f"High IPC payload saturation: {frame_size} bytes ({(frame_size/MAX_PAYLOAD_BYTES)*100:.1f}%)")

            try:
                message = json.loads(line.decode("utf-8").strip())
                if not isinstance(message, dict) or "jsonrpc" not in message:
                    continue  
                self._handle_incoming_message(message)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"Corrupt IPC frame dropped: {e}")
                continue

    def _handle_incoming_message(self, message: dict):
        msg_id = message.get("id")
        if msg_id in self._pending_requests:
            future = self._pending_requests.pop(msg_id)
            if not future.done():
                future.set_result(message)
            return

        method = message.get("method")
        if method == "graph_event":
            params = message.get("params", {})
            event_type = params.get("type")
            data = params.get("data", {})

            if not isinstance(data, dict):
                return

            if event_type == "node_updated":
                self.nodeUpdated.emit(data)
            elif event_type == "node_deleted":
                self.nodeDeleted.emit(data)

    async def _send_rpc(self, method: str, params: Optional[dict] = None) -> dict:
        if not self._writer:
            raise ConnectionError("Socket is not connected")

        self._request_counter += 1
        req_id = self._request_counter
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": req_id,
        }

        future = self._loop.create_future()
        self._pending_requests[req_id] = future

        frame = json.dumps(payload).encode("utf-8") + b"\n"
        if len(frame) > MAX_PAYLOAD_BYTES:
            self._pending_requests.pop(req_id, None)
            raise ValueError("Payload exceeds 64KB framing limit")

        self._writer.write(frame)
        await self._writer.drain()

        return await asyncio.wait_for(future, timeout=5.0)

    def call_rpc_sync(self, method: str, params: Optional[dict] = None, callback: Optional[Callable] = None):
        if not self._loop or not self._loop.is_running():
            return

        async def _runner():
            try:
                res = await self._send_rpc(method, params)
                if callback:
                    callback(res.get("result"), None)
            except Exception as e:
                if callback:
                    callback(None, str(e))

        asyncio.run_coroutine_threadsafe(_runner(), self._loop)

    async def _cleanup(self):
        for fut in self._pending_requests.values():
            if not fut.done():
                fut.cancel()
        self._pending_requests.clear()
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass