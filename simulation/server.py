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
        disconnected = []
        for connection in self.active_connections:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_text(message)
                else:
                    disconnected.append(connection)
            except Exception as e:
                print(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

# --- Global Simulation State ---
class SimulationState:
    def __init__(self):
        self.running = False
        self.task = None
        self.devices = []
        self.cc = None
        self.fcomm = None
        self.manager = None

simulation_state = SimulationState()

# --- FastAPI App Setup ---
app = FastAPI()
manager = WebSocketManager()
simulation_state.manager = manager

# --- Simulation Logic ---
async def simulation_loop():
    """The main simulation logic."""
    try:
        print("Initializing simulation...")
        num_units = 25
        simulation_state.fcomm = IPCCommunicator(websocket_manager=manager)
        layout_instance = Layout(num_units + 1)
        
        # Send initial layout to all connected clients
        initial_layout_message = {
            "type": "INITIAL_LAYOUT",
            "nodes": layout_instance.get_all_nodes()
        }
        await manager.broadcast(json.dumps(initial_layout_message))

        # Create devices
        simulation_state.devices = []
        for i in range(num_units):
            c = chr(i + 65)
            devid = f"{c}{c}{c}"
            device = Device(devid, simulation_state.fcomm, None)
            simulation_state.devices.append(device)

        # Create command central
        simulation_state.cc = CommandCentral("ZZZ", simulation_state.fcomm, None)
        simulation_state.fcomm.add_dev(simulation_state.cc.devid, simulation_state.cc)
        
        for d in simulation_state.devices:
            simulation_state.fcomm.add_dev(d.devid, d)

        print("Simulation initialized. Waiting for start command...")

        # Main simulation loop
        while True:
            if not simulation_state.running:
                await asyncio.sleep(0.1)
                continue

            try:
                # Device scanning and heartbeat phase
                for device in simulation_state.devices:
                    if not simulation_state.running:
                        break
                    
                    # Send scan message
                    scan_msg = {
                        "message_type": "scan",
                        "source": device.devid,
                        "source_timestamp": time.time_ns(),
                        "path_so_far": [device.devid]
                    }
                    await simulation_state.fcomm.send_to_network(scan_msg, device.devid)
                    
                    # Send heartbeat if device has a path
                    hb_msg = device.make_hb_msg(time.time_ns())
                    if hb_msg:
                        await simulation_state.fcomm.send_to_network(hb_msg, device.devid)
                    
                    await asyncio.sleep(0.05)  # Small delay between device operations

                if simulation_state.running:
                    # Command central sends shortest path updates
                    await simulation_state.cc.send_spath()
                    print(f"Simulation round completed. CC neighbours: {simulation_state.cc.neighbours_seen}")
                    await asyncio.sleep(2)  # Wait before next round

            except Exception as e:
                print(f"Error in simulation loop: {e}")
                await asyncio.sleep(1)

    except Exception as e:
        print(f"Fatal error in simulation: {e}")

async def start_simulation():
    """Start the simulation."""
    if simulation_state.task is None or simulation_state.task.done():
        print("Starting simulation task...")
        simulation_state.task = asyncio.create_task(simulation_loop())
    simulation_state.running = True
    print("Simulation started!")

async def stop_simulation():
    """Stop the simulation."""
    simulation_state.running = False
    print("Simulation stopped!")

@app.on_event("startup")
async def startup_event():
    """Start the simulation task when the app starts."""
    await start_simulation()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    print(f"New WebSocket connection. Total connections: {len(manager.active_connections)}")
    
    # Send initial layout to the new client
    if simulation_state.fcomm:
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
            command = message.get("command")
            
            if command == "start":
                print(">>> Command Received: START Simulation")
                simulation_state.running = True
                if simulation_state.task is None or simulation_state.task.done():
                    await start_simulation()
            elif command == "stop":
                print(">>> Command Received: STOP Simulation")
                await stop_simulation()
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Client disconnected. Remaining connections: {len(manager.active_connections)}")

if __name__ == "__main__":
    print("Starting FastAPI server on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)