import time
import constants
import json
import layout
import random

class IPCCommunicator:
    def __init__(self, websocket_manager=None):
        self.simulated_layout = layout.Layout()
        self.dev = {}  # ID -> Obj
        self.robustness = 0.4
        self.websocket_manager = websocket_manager

    def add_dev(self, devid, devobj):
        self.dev[devid] = devobj

    async def add_flakiness(self, msg, devid):
        # Nodes that have a chance to be flaky
        if devid in ["VVV", "NNN", "CCC", "QQQ"]:
            if random.random() > self.robustness:
                print(f"Flaky network: Node {devid} is down.")
                if self.websocket_manager:
                    await self.websocket_manager.broadcast(json.dumps({
                        "type": "STATUS_UPDATE",
                        "nodeId": devid,
                        "status": "down"
                    }))
                return True
        return False

    async def send_to_network(self, msg, devid, dest=None):
        time.sleep(0.01)
        if await self.add_flakiness(msg, devid):
            return False

        # If node is not flaky, ensure its status is up
        if self.websocket_manager:
            await self.websocket_manager.broadcast(json.dumps({
                "type": "STATUS_UPDATE",
                "nodeId": devid,
                "status": "up"
            }))

        destinations = [dest] if dest is not None else self.simulated_layout.get_neighbours(devid)
        
        for n in destinations:
            if n in self.dev:
                # Broadcast the communication link to the frontend
                if self.websocket_manager:
                    # Include the full path taken by the message so far
                    path_so_far = msg.get(constants.JK_PATH_SO_FAR, [])
                    
                    await self.websocket_manager.broadcast(json.dumps({
                        "type": "COMMUNICATION",
                        "source": devid,
                        "target": n,
                        "msg_type": msg.get(constants.JK_MESSAGE_TYPE),
                        "full_path": path_so_far + [n] # Add the target to complete the path for this hop
                    }))
                self.dev[n].process_msg(msg)
        return True
