"""WebSocket manager for SAPA."""

import asyncio
import json
import logging
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

connected_clients: set[WebSocket] = set()


async def broadcast(event: str, data: dict):
    """Broadcast a message to all connected WebSocket clients."""
    message = json.dumps({"event": event, "data": data, "timestamp": datetime.now().isoformat()})
    disconnected = set()
    for client in connected_clients:
        try:
            await client.send_text(message)
        except Exception:
            disconnected.add(client)
    connected_clients.difference_update(disconnected)


async def websocket_endpoint(websocket: WebSocket, watcher=None):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info(f"Client connected. Total: {len(connected_clients)}")

    try:
        await websocket.send_text(json.dumps({
            "event": "connected",
            "data": {
                "files_count": len(watcher.files) if watcher else 0,
                "watch_path": str(watcher.watch_path) if watcher else None,
            }
        }))

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                message = json.loads(data)

                if message.get("action") == "refresh":
                    if watcher:
                        watcher.scan_existing()
                        await websocket.send_text(json.dumps({
                            "event": "refresh",
                            "data": {"files_count": len(watcher.files)}
                        }))

            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"event": "ping"}))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connected_clients.discard(websocket)
        logger.info(f"Client disconnected. Total: {len(connected_clients)}")
