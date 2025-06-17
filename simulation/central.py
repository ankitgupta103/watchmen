import time
import constants

class NodeInfo:
    def __init__(self, devid):
        self.devid = devid
        self.last_heartbeat = None
        self.neighbours = []
        self.image_count = 0
        self.event_count = 0
        
    def add_hb(self, ts, neighbours, shortest_path, path_so_far, image_count, event_count):
        self.last_heartbeat = ts
        self.neighbours = neighbours or []
        self.image_count = image_count or 0
        self.event_count = event_count or 0
        
    def print_info(self):
        print(f"Node {self.devid}: HB={self.last_heartbeat}, Neighbours={self.neighbours}, Images={self.image_count}, Events={self.event_count}")

class CommandCentral:
    def __init__(self, devid, fcomm, ncomm):
        self.devid = devid
        self.neighbours_seen = []
        self.fcomm = fcomm
        self.ncomm = ncomm
        self.node_list = {}  # devid -> NodeInfo
        
        if fcomm is None and ncomm is None:
            print("Command Central needs at least one communicator")
            return
        if fcomm is not None and ncomm is not None:
            print("Command Central should have at most one communicator")
            return

    async def send_message(self, msg, dest=None):
        if self.fcomm is not None:
            return await self.fcomm.send_to_network(msg, self.devid, dest)
        return False
        
    async def send_spath(self):
        """Send shortest path information to all discovered neighbours."""
        if not self.neighbours_seen:
            print("Command Central: No neighbours discovered yet")
            return True
            
        print(f"Command Central sending spath to {len(self.neighbours_seen)} neighbours: {self.neighbours_seen}")
        
        for neighbour in self.neighbours_seen:
            ts = time.time_ns()
            spath_msg = {
                constants.JK_MESSAGE_TYPE: constants.MESSAGE_TYPE_SPATH,
                constants.JK_SOURCE: self.devid,
                constants.JK_DEST: neighbour,
                constants.JK_SOURCE_TIMESTAMP: ts,
                constants.JK_SHORTEST_PATH: [self.devid, neighbour],
                constants.JK_LAST_SENDER: self.devid,
                constants.JK_LAST_TS: ts,
            }
            success = await self.send_message(spath_msg, neighbour)
            if success:
                print(f"Command Central sent spath to {neighbour}")
            else:
                print(f"Command Central failed to send spath to {neighbour}")
        return True

    def process_msg(self, msg):
        """Process incoming messages."""
        mtype = msg.get(constants.JK_MESSAGE_TYPE)
        source = msg.get(constants.JK_SOURCE)
        
        if mtype == constants.MESSAGE_TYPE_SCAN and source not in self.neighbours_seen:
            self.neighbours_seen.append(source)
            print(f"Command Central discovered new neighbour: {source} (Total: {len(self.neighbours_seen)})")
            
        elif mtype == constants.MESSAGE_TYPE_HEARTBEAT:
            self.consume_hb(msg)
            
        elif mtype == constants.MESSAGE_TYPE_PHOTO:
            self.consume_photo(msg)
            
    def consume_hb(self, msg):
        """Process heartbeat messages."""
        source = msg.get(constants.JK_SOURCE)
        ts = msg.get(constants.JK_SOURCE_TIMESTAMP)
        neighbours = msg.get(constants.JK_NEIGHBOURS, [])
        shortest_path = msg.get(constants.JK_SHORTEST_PATH, [])
        path_so_far = msg.get(constants.JK_PATH_SO_FAR, [])
        image_count = msg.get(constants.JK_IMAGE_COUNT, 0)
        event_count = msg.get(constants.JK_EVENT_COUNT, 0)
        
        if source not in self.node_list:
            self.node_list[source] = NodeInfo(source)
            
        self.node_list[source].add_hb(ts, neighbours, shortest_path, path_so_far, image_count, event_count)
        print(f"Command Central received heartbeat from {source} via path: {path_so_far + [self.devid]}")
        
    def consume_photo(self, msg):
        """Process photo messages."""
        source = msg.get(constants.JK_SOURCE)
        path_so_far = msg.get(constants.JK_PATH_SO_FAR, [])
        image_ts = msg.get(constants.JK_IMAGE_TS)
        
        print(f"Command Central received photo from {source} via path: {path_so_far + [self.devid]} at {image_ts}")
        
        # Update the node's image count if we're tracking it
        if source in self.node_list:
            self.node_list[source].image_count += 1
            
    def print_network_status(self):
        """Print the current network status."""
        print(f"\n=== Command Central Network Status ===")
        print(f"Direct neighbours: {len(self.neighbours_seen)} - {self.neighbours_seen}")
        print(f"Nodes reporting: {len(self.node_list)}")
        for node_info in self.node_list.values():
            node_info.print_info()
        print("=" * 40)