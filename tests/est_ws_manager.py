# Create tests/test_ws_manager.py to test WebSocket connect, disconnect, state message, and broadcast behavior from ws_manager.py.
import asyncio
import pytest
import websockets

@pytest.mark.StopAsyncIteration
async def test_websocket_connection():
    """Tests that a WebSocket client can connect and receive a welcome message."""
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        # Wait for the welcome message
        welcome_message = await websocket.recv()
        assert welcome_message == "Welcome to the Guardio WebSocket!"
    
@pytest.mark.StopAsyncIteration
async def test_websocket_broadcast():
    """Tests that a message broadcasted by the server is received by connected clients."""
    uri = "ws://localhost:8000/ws"
    
    # Connect two clients
    async with websockets.connect(uri) as ws1, websockets.connect(uri) as ws2:
        # Wait for welcome messages
        await ws1.recv()
        await ws2.recv()
        
        # Simulate a server broadcast (this would normally be triggered by some event in the server)
        # For testing purposes, we can directly call the broadcast function if accessible, or simulate it via an API call.
        # Here we assume there's an API endpoint to trigger a broadcast for testing.
        
        # Trigger a broadcast (this part depends on your implementation, adjust as needed)
        # For example, you might have an endpoint like /broadcast that sends a message to all WebSocket clients.
        # You would use an HTTP client to call that endpoint here.
        
        # Wait for the broadcast message on both clients
        broadcast_message_1 = await ws1.recv()
        broadcast_message_2 = await ws2.recv()
        
        assert broadcast_message_1 == "This is a broadcast message from the server!"
        assert broadcast_message_2 == "This is a broadcast message from the server!"
    
@pytest.mark.StopAsyncIteration
async def test_websocket_disconnect():
    """Tests that a WebSocket client can disconnect gracefully."""
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        # Wait for the welcome message
        await websocket.recv()
        
        # Close the connection
        await websocket.close()
        
        # Ensure the connection is closed
        assert websocket.closed

