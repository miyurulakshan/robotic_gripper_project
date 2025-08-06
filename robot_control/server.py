# filename: server.py
import asyncio
import websockets

# This set will store all connected websocket clients.
CONNECTED_CLIENTS = set()

async def handler(websocket):
    """
    Handles a new client connection, adding them to the broadcast list
    and processing their messages.
    """
    print(f"[Server] Client connected: {websocket.remote_address}. Total clients: {len(CONNECTED_CLIENTS) + 1}")
    # Add the new client to our set of connections.
    CONNECTED_CLIENTS.add(websocket)
    try:
        # This loop runs as long as the client is connected.
        # It waits for a message from this specific client.
        async for message in websocket:
            # When a message is received, broadcast it to all other clients.
            # The websockets.broadcast function is efficient for this.
            websockets.broadcast(CONNECTED_CLIENTS, message)
    finally:
        # When the client disconnects (loop ends), remove them from the set.
        CONNECTED_CLIENTS.remove(websocket)
        print(f"[Server] Client disconnected: {websocket.remote_address}. Total clients: {len(CONNECTED_CLIENTS)}")

async def main():
    """Starts the WebSocket server."""
    print("[Server] Starting broadcast server...")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[Server] Shutting down.")

