import asyncio
import json
import websockets

async def main():
    uri = "ws://127.0.0.1:8000/ws/agent"
    task = "Привет"
    workspace_path = "C:\\Users\\danik\\Documents\\Field"
    
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            payload = {
                "task": task,
                "workspace_path": workspace_path
            }
            await websocket.send(json.dumps(payload))
            print("Payload sent. Listening for events...")
            
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    event_type = data.get("type")
                    print(f"EVENT: {data}")
                    if event_type == "status" and data.get("status") == "done":
                        break
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed by server.")
                    break
    except Exception as e:
        print(f"Failed to connect or test: {e}")

if __name__ == "__main__":
    asyncio.run(main())
