import time
import constants

class NodeInfo:
    def __init__(self, devid):
        self.devid = devid
        # ... other initializations
    def add_hb(self, ts, neighbours, shortest_path, path_so_far, image_count, event_count):
        pass # Your logic here
    def print_info(self):
        pass # Your logic here

class CommandCentral:
    def __init__(self, devid, fcomm, ncomm):
        self.devid = devid
        self.neighbours_seen = []
        self.fcomm = fcomm
        self.node_list = {}
        #... other initializations

    async def send_message(self, msg, dest=None):
        if self.fcomm is not None:
            return await self.fcomm.send_to_network(msg, self.devid, dest)
        return False
        
    async def send_spath(self):
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
            await self.send_message(spath_msg, neighbour)
        return True

    def process_msg(self, msg):
        mtype = msg.get(constants.JK_MESSAGE_TYPE)
        source = msg.get(constants.JK_SOURCE)
        if mtype == constants.MESSAGE_TYPE_SCAN and source not in self.neighbours_seen:
            self.neighbours_seen.append(source)
            print(f"CC discovered new neighbour: {source}")
        elif mtype == constants.MESSAGE_TYPE_HEARTBEAT:
            # Your consume_hb logic here
            pass
