import time
import constants
import asyncio

class NodeInfo:
    def __init__(self, devid):
        self.devid = devid
        self.last_heartbeat = None
        self.neighbours = []
        
    def add_hb(self, ts, neighbours):
        self.last_heartbeat = ts
        self.neighbours = neighbours or []

class CommandCentral:
    def __init__(self, devid, fcomm, ncomm):
        self.devid = devid
        self.neighbours_seen = []
        self.fcomm = fcomm
        self.ncomm = ncomm
        self.node_list = {}  # devid -> NodeInfo
        
    async def log(self, message):
        """Convenience method for logging."""
        if self.fcomm and hasattr(self.fcomm, 'log_message'):
            await self.fcomm.log_message(f"CENTRAL ({self.devid}): {message}")

    async def send_message(self, msg, dest=None):
        if self.fcomm is not None:
            return await self.fcomm.send_to_network(msg, self.devid, dest)
        return False
        
    async def send_spath(self):
        """Sends shortest path information to all directly discovered neighbors."""
        if not self.neighbours_seen:
            return
            
        await self.log(f"Broadcasting shortest path info to {len(self.neighbours_seen)} direct neighbors.")
        
        for neighbour in self.neighbours_seen:
            # --- CRITICAL FIX START ---
            # The path being sent IS the path from the neighbour to the central node.
            # It must include the central node as the destination.
            spath_to_send = [neighbour, self.devid]
            # --- CRITICAL FIX END ---

            spath_msg = {
                constants.JK_MESSAGE_TYPE: constants.MESSAGE_TYPE_SPATH,
                constants.JK_SOURCE: self.devid,
                constants.JK_DEST: neighbour,
                constants.JK_SOURCE_TIMESTAMP: time.time_ns(),
                constants.JK_SHORTEST_PATH: spath_to_send, 
            }
            await self.send_message(spath_msg, neighbour)
            await asyncio.sleep(0.1)

    def process_msg(self, msg):
        """Process incoming messages."""
        mtype = msg.get(constants.JK_MESSAGE_TYPE)
        source = msg.get(constants.JK_SOURCE)
        
        loop = asyncio.get_running_loop()

        if mtype == constants.MESSAGE_TYPE_SCAN and source not in self.neighbours_seen:
            self.neighbours_seen.append(source)
            loop.create_task(self.log(f"Discovered direct neighbor: {source}"))
            
        elif mtype == constants.MESSAGE_TYPE_HEARTBEAT:
            loop.create_task(self.consume_hb(msg))
            
    async def consume_hb(self, msg):
        """Process heartbeat messages."""
        source = msg.get(constants.JK_SOURCE)
        path_so_far = msg.get(constants.JK_PATH_SO_FAR, [])
        # The final hop to the central node is itself.
        full_path = path_so_far + [self.devid]
        
        await self.log(f"Heartbeat from {source} via path: {'->'.join(full_path)}")
        
        if source not in self.node_list:
            self.node_list[source] = NodeInfo(source)
            
        self.node_list[source].add_hb(
            msg.get(constants.JK_SOURCE_TIMESTAMP),
            msg.get(constants.JK_NEIGHBOURS, [])
        )