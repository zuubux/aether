import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from utils.security import is_safe_path

logger = logging.getLogger("aia_weaver.ipc")

MAX_PAYLOAD_BYTES = 64 * 1024


class IPCServer:
    def __init__(
        self,
        socket_path: str | None = None,
        search_handler: Callable[[str, int], Awaitable[list]] = None,
        neighbors_handler: Callable[[int], Awaitable[dict]] = None,
        all_nodes_handler: Callable[[], Awaitable[list]] = None,
        touch_handler: Callable[[int, str], Awaitable[dict]] = None,
        save_node_handler: Callable[[int, str], Awaitable[dict]] = None,
        create_edge_handler: Callable[[int, int, str], Awaitable[dict]] = None,
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
        self.all_nodes_handler = all_nodes_handler
        self.touch_handler = touch_handler
        self.save_node_handler = save_node_handler
        self.create_edge_handler = create_edge_handler
        self.allowed_directories = allowed_directories or []
        self.server: asyncio.Server | None = None
        self._clients: set[asyncio.StreamWriter] = set()

    async def start(self) -> None:
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
        self._clients.add(writer)
        logger.info("New IPC client connected.")

        try:
            while True:
                try:
                    data = await reader.readline()
                    if not data:
                        break

                    message = data.decode("utf-8").strip()
                    if not message:
                        continue

                    response = await self._dispatch_rpc(message)
                    writer.write((json.dumps(response) + "\n").encode("utf-8"))
                    await writer.drain()

                except asyncio.LimitOverrunError:
                    logger.warning("Security Warning: Payload exceeds 64 KB size limit.")
                    err_response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32600, "message": "Payload exceeds limit."},
                        "id": None,
                    }
                    writer.write((json.dumps(err_response) + "\n").encode("utf-8"))
                    await writer.drain()
                    break

        except (ConnectionError, BrokenPipeError, ConnectionResetError, OSError, KeyError) as e:
            logger.error(f"IPC client handler error: {e}")
        except asyncio.CancelledError:
            pass
        finally:
            if writer in self._clients:
                self._clients.remove(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except (ConnectionError, BrokenPipeError, ConnectionResetError):
                pass
            except Exception as close_err:
                logger.debug(f"Suppressed socket teardown warning: {close_err}")
            logger.info("IPC client disconnected.")

    async def _dispatch_rpc(self, raw_message: str) -> dict[str, Any]:
        try:
            req = json.loads(raw_message)
            if not isinstance(req, dict) or "jsonrpc" not in req:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Invalid Request: missing jsonrpc key"},
                    "id": None,
                }
            if "method" not in req and "id" not in req:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Invalid Request: missing method or id"},
                    "id": None,
                }
            method = req.get("method")
            params = req.get("params", {})
            req_id = req.get("id")

            requested_path = params.get("file_path") or params.get("path")
            if requested_path:
                if not is_safe_path(requested_path, self.allowed_directories):
                    return {
                        "jsonrpc": "2.0",
                        "error": {"code": -32602, "message": "Access Denied."},
                        "id": req_id,
                    }

            if method == "get_neighbors":
                node_id = params.get("node_id")
                if node_id is None or not isinstance(node_id, int):
                    return {
                        "jsonrpc": "2.0",
                        "error": {"code": -32602, "message": "Invalid params: 'node_id' required"},
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

            elif method == "get_all_nodes":
                if self.all_nodes_handler:
                    results = await self.all_nodes_handler()
                    return {"jsonrpc": "2.0", "result": results, "id": req_id}
                return {"jsonrpc": "2.0", "result": [], "id": req_id}

            elif method == "touch_node":
                node_id = params.get("node_id")
                event_type = params.get("event_type", "focus")
                if node_id is None or not isinstance(node_id, int):
                    return {
                        "jsonrpc": "2.0",
                        "error": {"code": -32602, "message": "Invalid params: 'node_id' required"},
                        "id": req_id,
                    }

                if self.touch_handler:
                    result = await self.touch_handler(node_id, event_type)
                    return {"jsonrpc": "2.0", "result": result, "id": req_id}
                return {"jsonrpc": "2.0", "result": {"status": "noop"}, "id": req_id}

            elif method == "create_edge":
                source_id = params.get("source_id")
                target_id = params.get("target_id")
                edge_type = params.get("edge_type", "semantic_link")

                if source_id is None or target_id is None:
                    return {
                        "jsonrpc": "2.0",
                        "error": {"code": -32602, "message": "Invalid params: 'source_id' and 'target_id' required"},
                        "id": req_id,
                    }

                if self.create_edge_handler:
                    result = await self.create_edge_handler(source_id, target_id, edge_type)
                    return {"jsonrpc": "2.0", "result": result, "id": req_id}
                return {"jsonrpc": "2.0", "result": {"status": "noop"}, "id": req_id}

            elif method == "save_node_content":
                node_id = params.get("node_id")
                content = params.get("content", "")
                if node_id is None or not isinstance(node_id, int):
                    return {
                        "jsonrpc": "2.0",
                        "error": {"code": -32602, "message": "Invalid params: 'node_id' required"},
                        "id": req_id,
                    }

                if self.save_node_handler:
                    result = await self.save_node_handler(node_id, content)
                    return {"jsonrpc": "2.0", "result": result, "id": req_id}
                return {"jsonrpc": "2.0", "result": {"status": "noop"}, "id": req_id}

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
            except (ConnectionError, BrokenPipeError, ConnectionResetError):
                if writer in self._clients:
                    self._clients.remove(writer)
            except Exception:
                if writer in self._clients:
                    self._clients.remove(writer)

    async def stop(self) -> None:
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        if self.socket_path.exists():
            self.socket_path.unlink()
        logger.info("IPC socket server stopped.")