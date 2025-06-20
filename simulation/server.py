import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
import uvicorn
import time
from device import Device
from central import CommandCentral
from ipc_communicator import IPCCommunicator
from layout import Layout
import constants

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
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_text(message)
            except Exception:
                self.disconnect(connection)

# --- FastAPI and Simulation State ---
app = FastAPI()
manager = WebSocketManager()
# Add a lock to prevent race conditions from creating two simulation loops
simulation_lock = asyncio.Lock()
simulation_state = {"running": False, "task": None}
fcomm = IPCCommunicator(websocket_manager=manager)
layout_instance = Layout()
devices = []
cc = None
sleep_factor = 2.0

async def setup_simulation():
    global devices, cc
    await fcomm.log_message("SYSTEM: Initializing simulation environment...")
    
    node_ids = [node['id'] for node in layout_instance.get_all_nodes() if node['id'] != constants.CENTRAL_NODE_ID]
    devices = []
    for devid in node_ids:
        device = Device(devid, fcomm, None)
        devices.append(device)
        fcomm.add_dev(devid, device)
    
    cc = CommandCentral(constants.CENTRAL_NODE_ID, fcomm, None)
    fcomm.add_dev(cc.devid, cc)
    
    await fcomm.log_message(f"SYSTEM: Created {len(devices)} devices and 1 command central.")
    
    initial_layout_message = {"type": "INITIAL_LAYOUT", "nodes": layout_instance.get_all_nodes()}
    await manager.broadcast(json.dumps(initial_layout_message))
    await fcomm.log_message("SYSTEM: Sent initial network layout to frontend.")


async def simulation_loop():
    await setup_simulation()

    while True:
        if not simulation_state["running"]:
            await asyncio.sleep(0.5 * sleep_factor)
            continue
        try:
            # This is a clean, single-instance loop.
            await fcomm.log_message("SIM_PHASE: All nodes scanning for neighbors.")
            await asyncio.sleep(1 * sleep_factor)
            for device in devices:
                if not simulation_state["running"]: break
                await device.send_scan_message()
                await asyncio.sleep(0.2 * sleep_factor)
            if not simulation_state["running"]: continue
            await asyncio.sleep(2 * sleep_factor)

            await fcomm.log_message("SIM_PHASE: Central node broadcasting path information.")
            await asyncio.sleep(1 * sleep_factor)
            await cc.send_spath()
            if not simulation_state["running"]: continue
            await asyncio.sleep(3 * sleep_factor)

            await fcomm.log_message("SIM_PHASE: All nodes sending heartbeats.")
            await asyncio.sleep(1 * sleep_factor)
            for device in devices:
                 if not simulation_state["running"]: break
                 await device.send_hb()
                 await asyncio.sleep(0.3 * sleep_factor)
            if not simulation_state["running"]: continue
            await fcomm.log_message("SIM_PHASE: Round complete. Waiting before next cycle.")
            await asyncio.sleep(5 * sleep_factor)

        except Exception as e:
            await fcomm.log_message(f"ERROR: Simulation loop crashed: {e}")
            await asyncio.sleep(2 * sleep_factor)

async def start_simulation():
    """Safely start the simulation using a lock to prevent duplicates."""
    async with simulation_lock:
        if simulation_state["task"] is None or simulation_state["task"].done():
            await fcomm.log_message("SYSTEM: Creating new simulation task.")
            simulation_state["task"] = asyncio.create_task(simulation_loop())
    
    simulation_state["running"] = True
    await fcomm.log_message("CONTROL: Simulation started by user.")

async def stop_simulation():
    """Stop the simulation."""
    simulation_state["running"] = False
    await fcomm.log_message("CONTROL: Simulation paused by user.")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    print("New client connected.")
    
    # Immediately send layout info to the new client
    initial_layout_message = {"type": "INITIAL_LAYOUT", "nodes": layout_instance.get_all_nodes()}
    await websocket.send_text(json.dumps(initial_layout_message))
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            command = message.get("command")
            
            if command == "start":
                await start_simulation()
            elif command == "stop":
                await stop_simulation()
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected.")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)