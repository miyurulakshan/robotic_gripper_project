import asyncio
import websockets

class WebSocketServer:
    def __init__(self, data_queue):
        self.data_queue = data_queue

    async def _handler(self, websocket):
        print(f"[Server] Client connected from {websocket.remote_address}")
        try:
            async for message in websocket:
                self.data_queue.put(message)
        except websockets.exceptions.ConnectionClosedError:
            print(f"[Server] Client disconnected.")
        except Exception as e:
            print(f"[Server] An error occurred in handler: {e}")

    async def start(self, host="0.0.0.0", port=8765):
        print(f"[Server] Starting WebSocket server at ws://{host}:{port}")
        async with websockets.serve(self._handler, host, port):
            await asyncio.Future()
