# filename: server.py
# This is the complete, correct code for this file.
import asyncio
import websockets

CONNECTED_CLIENTS = set()

async def handler(websocket):
    """
    Handles a new client connection, adding them to the broadcast list
    and processing their messages.
    """
    print(f"[Server] Client connected: {websocket.remote_address}. Total clients: {len(CONNECTED_CLIENTS) + 1}")
    CONNECTED_CLIENTS.add(websocket)
    try:
        async for message in websocket:
            websockets.broadcast(CONNECTED_CLIENTS, message)
    finally:
        CONNECTED_CLIENTS.remove(websocket)
        print(f"[Server] Client disconnected: {websocket.remote_address}. Total clients: {len(CONNECTED_CLIENTS)}")

async def main():
    """Starts the WebSocket server."""
    print("[Server] Starting broadcast server on ws://0.0.0.0:8765")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[Server] Shutting down.")