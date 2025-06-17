import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketState
import uvicorn
import threading

import time
from device import Device
from central import CommandCentral
from ipc_communicator import IPCCommunicator
from layout import Layout

# --- WebSocket Manager ---
class WebSocketManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            if connection.client_state == WebSocketState.CONNECTED:
                await connection.send_text(message)

# --- FastAPI App Setup ---
app = FastAPI()
manager = WebSocketManager()

# --- Simulation Logic ---
def run_simulation(manager_ref: WebSocketManager):
    """This function contains your original simulation logic, modified to be async."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def simulation_main():
        num_units = 25
        fcomm = IPCCommunicator(websocket_manager=manager_ref)
        layout_instance = Layout(num_units + 1) # +1 for central command
        
        # Send initial node layout to frontend
        initial_layout_message = {
            "type": "INITIAL_LAYOUT",
            "nodes": layout_instance.get_all_nodes()
        }
        await manager_ref.broadcast(json.dumps(initial_layout_message))

        devices = []
        for i in range(num_units):
            c = chr(i + 65)
            devid = f"{c}{c}{c}"
            device = Device(devid, fcomm, None)
            devices.append(device)

        cc = CommandCentral("ZZZ", fcomm, None)
        fcomm.add_dev(cc.devid, cc)
        for d in devices:
            fcomm.add_dev(d.devid, d)

        # Main simulation loop
        while True:
            for device in devices:
                # These need to become async calls if they do network I/O
                # For now, we assume process_msg handles the async broadcast
                device.check_event()
                await fcomm.send_to_network(
                    {
                        "message_type": "scan",
                        "source": device.devid,
                        "source_timestamp": time.time_ns(),
                    },
                    device.devid
                )
                await fcomm.send_to_network(
                    device.make_hb_msg(time.time_ns()) or {},
                    device.devid
                )
                await asyncio.sleep(0.01)
            
            await cc.send_spath()
            print("One round of Scan and HB done.")
            await asyncio.sleep(2)

    loop.run_until_complete(simulation_main())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # On connect, send the current layout
    layout_instance = Layout(26)
    initial_layout_message = {
        "type": "INITIAL_LAYOUT",
        "nodes": layout_instance.get_all_nodes()
    }
    await websocket.send_text(json.dumps(initial_layout_message))
    try:
        while True:
            await websocket.receive_text() # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected")


if __name__ == "__main__":
    # Run the simulation in a separate thread
    sim_thread = threading.Thread(target=run_simulation, args=(manager,), daemon=True)
    sim_thread.start()

    # Start the web server
    print("Starting FastAPI server on [http://127.0.0.1:8000](http://127.0.0.1:8000)")
    uvicorn.run(app, host="127.0.0.1", port=8000)