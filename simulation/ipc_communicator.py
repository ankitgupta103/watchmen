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
        self.robustness = 0.60
        self.websocket_manager = websocket_manager
        self.flaky_nodes = ["VVV", "NNN", "CCC", "QQQ"]
        self.node_status = {}

    def add_dev(self, devid, devobj):
        self.dev[devid] = devobj
        self.node_status[devid] = "up"

    async def log_message(self, text):
        if self.websocket_manager:
            log_msg = {"type": constants.LOG_MESSAGE, "message": text, "timestamp": time.time()}
            await self.websocket_manager.broadcast(json.dumps(log_msg))

    async def add_flakiness(self, devid):
        if devid in self.flaky_nodes and random.random() > self.robustness:
            if self.node_status.get(devid) != "down":
                self.node_status[devid] = "down"
                await self.log_message(f"STATUS: Node {devid} went offline due to flakiness.")
                if self.websocket_manager:
                    await self.websocket_manager.broadcast(json.dumps({"type": "STATUS_UPDATE", "nodeId": devid, "status": "down"}))
            return True
        if self.node_status.get(devid) != "up":
            self.node_status[devid] = "up"
            await self.log_message(f"STATUS: Node {devid} is back online.")
            if self.websocket_manager:
                await self.websocket_manager.broadcast(json.dumps({"type": "STATUS_UPDATE", "nodeId": devid, "status": "up"}))
        return False

    async def send_to_network(self, msg, devid, dest=None):
        await asyncio.sleep(0.1)
        if await self.add_flakiness(devid):
            return False

        msg_type = msg.get(constants.JK_MESSAGE_TYPE, "unknown")
        destinations = [dest] if dest else self.simulated_layout.get_neighbours(devid)
        
        if not destinations:
            return False

        log_action = "UNICAST" if dest else "BROADCAST"
        log_targets = dest if dest else "Neighbors"
        await self.log_message(f"{log_action}: {devid} -> {log_targets} ({msg_type})")
        
        success_count = 0
        for target in destinations:
            if target in self.dev:
                if self.node_status.get(target) == "down":
                    await self.log_message(f"FAILED: {devid} -> {target}. Target is offline.")
                    continue
                
                if self.websocket_manager:
                    # --- CRITICAL FIX START ---
                    # Add the message's path to the payload for frontend visualization
                    path_so_far = msg.get(constants.JK_PATH_SO_FAR, [])
                    full_path = path_so_far + [devid, target]
                    comm_message = {
                        "type": "COMMUNICATION",
                        "source": devid,
                        "target": target,
                        "msg_type": msg_type,
                        "msg": msg,
                        "full_path": full_path if len(full_path) > 2 else None
                    }
                    # --- CRITICAL FIX END ---
                    await self.websocket_manager.broadcast(json.dumps(comm_message))
                
                self.dev[target].process_msg(msg)
                success_count += 1
                await asyncio.sleep(0.05)
        return success_count > 0