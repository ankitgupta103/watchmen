import json
import asyncio
import random
import time
import constants

# Mock classes for Detector and Camera if they are not defined elsewhere
class Detector:
    def ImageHasPerson(self, imfile):
        return random.random() > 0.95

class Camera:
    def __init__(self, devid, o_dir):
        self.devid = devid
        self.o_dir = o_dir
    def start(self):
        pass
    def take_picture(self):
        return f"{self.o_dir}/img.jpg", "imagedata"

class Device:
    def __init__(self, devid, fcomm, ncomm):
        self.devid = devid
        self.neighbours_seen = []
        self.spath = []
        self.fcomm = fcomm
        self.ncomm = ncomm
        if fcomm is None and ncomm is None:
            print("At least one communicator")
            return
        if fcomm is not None and ncomm is not None:
            print("At most one communicator")
            return
        self.cam = None
        # To test events, let's enable a camera on a specific device
        if self.devid == "GGG":
            self.cam = Camera(devid, o_dir="/tmp/camera_captures_test")
            self.cam.start()
            self.detector = Detector()
        self.image_count = 0
        self.event_count = 0

    async def send_message(self, msg, dest=None):
        if msg is None: return False
        if self.fcomm is not None:
            return await self.fcomm.send_to_network(msg, self.devid, dest)
        # ncomm logic would go here if used
        return False

    def get_next_on_spath(self):
        if not self.spath or len(self.spath) <= 1 or self.spath[0] != self.devid:
            return None
        return self.spath[1]

    def make_hb_msg(self, ts):
        if not self.spath or len(self.spath) < 2 or self.spath[0] != self.devid:
            return None
        return {
                constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_HEARTBEAT,
                constants.JK_SOURCE : self.devid,
                constants.JK_SOURCE_TIMESTAMP : ts,
                constants.JK_NEIGHBOURS : self.neighbours_seen,
                constants.JK_IMAGE_COUNT : self.image_count,
                constants.JK_EVENT_COUNT : self.event_count,
                constants.JK_SHORTEST_PATH : self.spath,
                constants.JK_DEST : None,
                constants.JK_PATH_SO_FAR : [],
                constants.JK_LAST_TS : ts
                }

    async def propogate_message(self, msg):
        if msg is None: return
        path_so_far = msg.get(constants.JK_PATH_SO_FAR, [])
        new_dest = self.get_next_on_spath()
        
        if new_dest and new_dest not in path_so_far:
            msg[constants.JK_DEST] = new_dest
            msg[constants.JK_PATH_SO_FAR] = path_so_far + [self.devid]
            msg[constants.JK_LAST_TS] = time.time_ns()
            await self.send_message(msg, new_dest)
        else:
            # Fallback to other neighbours if spath fails
            for n in self.neighbours_seen:
                if n not in path_so_far and n != new_dest:
                    msg[constants.JK_DEST] = n
                    msg[constants.JK_PATH_SO_FAR] = path_so_far + [self.devid]
                    await self.send_message(msg, n)
                    break
    
    async def send_hb(self, ts):
        msg = self.make_hb_msg(ts)
        await self.propogate_message(msg)
        
    def process_msg(self, msg):
        # This function is called by IPCCommunicator, so it should remain synchronous
        # or be carefully handled in the event loop. For this sim, it's fine.
        mtype = msg.get(constants.JK_MESSAGE_TYPE)
        source = msg.get(constants.JK_SOURCE)
        if mtype == constants.MESSAGE_TYPE_SCAN and source not in self.neighbours_seen:
            self.neighbours_seen.append(source)
        elif mtype == constants.MESSAGE_TYPE_SPATH:
             self.spread_spath(msg)
        elif mtype in [constants.MESSAGE_TYPE_HEARTBEAT, constants.MESSAGE_TYPE_PHOTO]:
            # This needs to be scheduled on the loop because it's async now
            asyncio.create_task(self.propogate_message(msg))
    
    def spread_spath(self, msg):
        spath1 = msg.get(constants.JK_SHORTEST_PATH, [])
        if not self.spath or len(spath1) < len(self.spath):
            self.spath = spath1[::-1]
            for neighbour in self.neighbours_seen:
                if neighbour in spath1: continue
                new_msg = msg.copy()
                new_msg[constants.JK_DEST] = neighbour
                new_msg[constants.JK_SHORTEST_PATH] = spath1 + [neighbour]
                asyncio.create_task(self.send_message(new_msg, neighbour))
                
    def check_event(self):
        # This remains synchronous for now
        pass

