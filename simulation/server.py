import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
import uvicorn
import threading

# Your existing simulation imports
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
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            if connection.client_state == WebSocketState.CONNECTED:
                await connection.send_text(message)

# --- Simulation Control ---
simulation_running = asyncio.Event()

# --- FastAPI App Setup ---
app = FastAPI()
manager = WebSocketManager()

# --- Simulation Logic ---
async def simulation_main(manager_ref: WebSocketManager):
    """The main simulation logic, now controllable."""
    num_units = 25
    fcomm = IPCCommunicator(websocket_manager=manager_ref)
    layout_instance = Layout(num_units + 1)
    
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

    while True:
        await simulation_running.wait() # Pause here if the event is not set

        for device in devices:
            if not simulation_running.is_set(): break
            device.check_event()
            await fcomm.send_to_network(
                {
                    "message_type": "scan",
                    "source": device.devid,
                    "source_timestamp": time.time_ns(),
                    "path_so_far": [device.devid]
                },
                device.devid
            )
            hb_msg = device.make_hb_msg(time.time_ns())
            if hb_msg:
                await fcomm.send_to_network(hb_msg, device.devid)
            await asyncio.sleep(0.01)
        
        if not simulation_running.is_set(): continue
        await cc.send_spath()
        print("One round of Scan and HB done.")
        await asyncio.sleep(2)

def run_simulation_in_thread(loop, manager_ref):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(simulation_main(manager_ref))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    layout_instance = Layout(26)
    initial_layout_message = {
        "type": "INITIAL_LAYOUT",
        "nodes": layout_instance.get_all_nodes()
    }
    await websocket.send_text(json.dumps(initial_layout_message))
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("command") == "start":
                print(">>> Command Received: START Simulation")
                simulation_running.set()
            elif message.get("command") == "stop":
                print(">>> Command Received: STOP Simulation")
                simulation_running.clear()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    sim_thread = threading.Thread(
        target=run_simulation_in_thread, 
        args=(loop, manager,), 
        daemon=True
    )
    sim_thread.start()

    print("Starting FastAPI server on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000, loop="asyncio")
