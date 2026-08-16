import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Callable, Awaitable, Dict, Any
from utils.security import is_safe_path

logger = logging.getLogger("aia_weaver.ipc")

# Security Hardening: Cap maximum IPC message size to 64 KB to prevent OOM / DoS
MAX_PAYLOAD_BYTES = 64 * 1024


class IPCServer:
    def __init__(
        self,
        socket_path: str | None = None,
        search_handler: Callable[[str, int], Awaitable[list]] = None,
        neighbors_handler: Callable[[int], Awaitable[dict]] = None,
        allowed_directories: list[Path] | None = None,
    ):
        if socket_path is None:
            runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
            socket_dir = Path(runtime_dir) / "aia_weaver"
            socket_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(socket_dir, 0o700)
            self.socket_path = socket_dir / "aia_weaver.sock"
        else:
            self.socket_path = Path(socket_path)

        self.search_handler = search_handler
        self.neighbors_handler = neighbors_handler
        self.allowed_directories = allowed_directories or []
        self.server: asyncio.Server | None = None
        self._clients: set[asyncio.StreamWriter] = set()

    async def start(self) -> None:
        """Removes stale sockets and starts the hardened UNIX socket server."""
        if self.socket_path.exists():
            self.socket_path.unlink()

        self.server = await asyncio.start_unix_server(
            self._handle_client,
            path=str(self.socket_path),
            limit=MAX_PAYLOAD_BYTES,
        )

        os.chmod(self.socket_path, 0o600)
        logger.info(
            f"IPC Server bound securely to socket: {self.socket_path} "
            f"(Max Frame Size: {MAX_PAYLOAD_BYTES // 1024} KB)"
        )

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handles incoming JSON-RPC connections with payload length guards."""
        self._clients.add(writer)
        logger.info("New IPC client connected.")

        try:
            while True:
                try:
                    data = await reader.readline()
                    if not data:
                        break  # Client disconnected cleanly

                    message = data.decode("utf-8").strip()
                    if not message:
                        continue

                    response = await self._dispatch_rpc(message)
                    writer.write((json.dumps(response) + "\n").encode("utf-8"))
                    await writer.drain()

                except asyncio.LimitOverrunError:
                    logger.warning(
                        "Security Warning: IPC client sent payload exceeding 64 KB limit! Dropping connection."
                    )
                    err_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32600,
                            "message": "Invalid Request: Payload exceeds 64 KB size limit.",
                        },
                        "id": None,
                    }
                    writer.write((json.dumps(err_response) + "\n").encode("utf-8"))
                    await writer.drain()
                    break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"IPC client handler error: {e}")
        finally:
            self._clients.remove(writer)
            writer.close()
            await writer.wait_closed()
            logger.info("IPC client disconnected.")

    async def _dispatch_rpc(self, raw_message: str) -> Dict[str, Any]:
        """Parses JSON-RPC requests and routes them to internal handlers."""
        try:
            req = json.loads(raw_message)
            method = req.get("method")
            params = req.get("params", {})
            req_id = req.get("id")

            # --- Path Traversal Guard for path parameters ---
            requested_path = params.get("file_path") or params.get("path")
            if requested_path:
                if not is_safe_path(requested_path, self.allowed_directories):
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32602,
                            "message": "Access Denied: Requested path falls outside allowed workspace boundaries.",
                        },
                        "id": req_id,
                    }

            # --- Method Dispatching ---
            if method == "get_neighbors":
                node_id = params.get("node_id")
                if node_id is None or not isinstance(node_id, int):
                    return {
                        "jsonrpc": "2.0",
                        "error": {"code": -32602, "message": "Invalid params: 'node_id' (integer) required"},
                        "id": req_id,
                    }

                if self.neighbors_handler:
                    result = await self.neighbors_handler(node_id)
                    return {"jsonrpc": "2.0", "result": result, "id": req_id}

            elif method == "search_graph":
                query_text = params.get("query", "")
                limit = params.get("limit", 5)

                if self.search_handler and query_text:
                    results = await self.search_handler(query_text, limit)
                    return {"jsonrpc": "2.0", "result": results, "id": req_id}

                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "Invalid params: 'query' required"},
                    "id": req_id,
                }

            elif method == "ping":
                return {"jsonrpc": "2.0", "result": "pong", "id": req_id}

            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": "Method not found"},
                    "id": req_id,
                }

        except json.JSONDecodeError:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None,
            }

    async def broadcast_event(self, event_type: str, payload: dict) -> None:
        """Broadcasting real-time graph events to connected canvas subscribers."""
        if not self._clients:
            return

        message = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "graph_event",
                    "params": {"type": event_type, "data": payload},
                }
            )
            + "\n"
        )

        for writer in list(self._clients):
            try:
                writer.write(message.encode("utf-8"))
                await writer.drain()
            except Exception:
                self._clients.remove(writer)

    async def stop(self) -> None:
        """Gracefully shuts down socket server and cleans up socket file."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        if self.socket_path.exists():
            self.socket_path.unlink()
        logger.info("IPC socket server stopped.")