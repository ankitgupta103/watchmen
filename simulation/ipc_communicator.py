import time
import constants
import json
import layout
import random
import asyncio

class IPCCommunicator:
    def __init__(self, websocket_manager=None):
        self.simulated_layout = layout.Layout()
        self.dev = {}  # ID -> Obj
        self.robustness = 0.7  # Higher robustness for better demo
        self.websocket_manager = websocket_manager
        self.flaky_nodes = ["VVV", "NNN", "CCC", "QQQ"]
        self.node_status = {}  # Track node status

    def add_dev(self, devid, devobj):
        self.dev[devid] = devobj
        self.node_status[devid] = "up"  # Initialize as up

    async def add_flakiness(self, msg, devid):
        """Simulate network flakiness for certain nodes."""
        # Only apply flakiness to designated flaky nodes
        if devid in self.flaky_nodes:
            if random.random() > self.robustness:
                print(f"Network flaky: Node {devid} is temporarily down.")
                self.node_status[devid] = "down"
                if self.websocket_manager:
                    await self.websocket_manager.broadcast(json.dumps({
                        "type": "STATUS_UPDATE",
                        "nodeId": devid,
                        "status": "down"
                    }))
                return True
        
        # If node is not flaky or passes robustness check, mark as up
        if self.node_status.get(devid) != "up":
            self.node_status[devid] = "up"
            if self.websocket_manager:
                await self.websocket_manager.broadcast(json.dumps({
                    "type": "STATUS_UPDATE",
                    "nodeId": devid,
                    "status": "up"
                }))
        
        return False

    async def send_to_network(self, msg, devid, dest=None):
        """Send message to network with visualization."""
        # Small delay to simulate network latency
        await asyncio.sleep(0.01)
        
        # Check if sender is flaky
        if await self.add_flakiness(msg, devid):
            return False

        # Determine destinations
        destinations = [dest] if dest is not None else self.simulated_layout.get_neighbours(devid)
        
        if not destinations:
            print(f"No destinations found for {devid}")
            return False
            
        success_count = 0
        
        for target in destinations:
            if target in self.dev:
                try:
                    # Check if target is down due to flakiness
                    if self.node_status.get(target) == "down":
                        print(f"Message from {devid} to {target} failed - target is down")
                        continue
                    
                    # Broadcast the communication link to the frontend
                    if self.websocket_manager:
                        # Get the full path taken by the message
                        path_so_far = msg.get(constants.JK_PATH_SO_FAR, [])
                        full_path = path_so_far + [devid, target]
                        
                        comm_message = {
                            "type": "COMMUNICATION",
                            "source": devid,
                            "target": target,
                            "msg_type": msg.get(constants.JK_MESSAGE_TYPE, "unknown"),
                            "full_path": full_path
                        }
                        
                        await self.websocket_manager.broadcast(json.dumps(comm_message))
                        print(f"Communication: {devid} -> {target} ({msg.get(constants.JK_MESSAGE_TYPE)})")
                    
                    # Deliver message to target device
                    self.dev[target].process_msg(msg)
                    success_count += 1
                    
                except Exception as e:
                    print(f"Error sending message from {devid} to {target}: {e}")
            else:
                print(f"Target device {target} not found in network")
        
        return success_count > 0