import time
import constants

from detect import Detector
from camera import Camera

class Device:
    def __init__(self, devid, fcomm):
        self.devid = devid
        self.neighbours_seen = []
        self.spath = []
        self.fcomm = fcomm
        self.cam = None
        if self.devid == "AAAaaa":
            self.cam = Camera(devid, o_dir="/tmp/camera_captures_test")
            self.cam.start()
            self.detector = Detector()
        self.image_count = 0
        self.event_count = 0

    def get_next_on_spath(self):
        if len(self.spath) <= 1 or self.spath[0] != self.devid:
            print(f"{self.devid} : No next path yet")
            return None
        return self.spath[1]

    def send_scan(self, ts):
        scan_msg = {
                constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_SCAN,
                constants.JK_SOURCE : self.devid,
                constants.JK_LAST_SENDER : self.devid,
                constants.JK_SOURCE_TIMESTAMP : ts,
                }
        # Failure Here is OK, since it is a discovery and alternative paths would be discovered.
        self.fcomm.send_to_network(scan_msg, self.devid)

    def make_hb_msg(self, ts):
        if self.spath == None or len(self.spath) < 2 or self.spath[0] != self.devid:
            print(f"{self.devid} : Spath is not adequate {self.spath}")
            return None
        hb_msg = {
                constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_HEARTBEAT,
                constants.JK_SOURCE : self.devid,
                constants.JK_SOURCE_TIMESTAMP : ts,
                # Payload
                constants.JK_NEIGHBOURS : self.neighbours_seen,
                constants.JK_IMAGE_COUNT : self.image_count,
                constants.JK_EVENT_COUNT : self.event_count,
                constants.JK_SHORTEST_PATH : self.spath,
                # Routing info
                constants.JK_DEST : None, # Will get rerouted
                constants.JK_PATH_SO_FAR : [],
                constants.JK_LAST_TS : ts
                }
        return hb_msg

    def make_image_msg(self, ts, image_data, image_ts):
        # TODO this will need to be stored until we have spath
        if self.spath == None or len(self.spath) < 2 or self.spath[0] != self.devid:
            return None
        image_msg = {
                constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_PHOTO,
                constants.JK_SOURCE : self.devid,
                constants.JK_SOURCE_TIMESTAMP : ts,
                # Payload
                constants.JK_IMAGE_DATA : image_data,
                constants.JK_IMAGE_TS : image_ts,
                # Routing info
                constants.JK_DEST : None, # Will get rerouted
                constants.JK_PATH_SO_FAR : [],
                constants.JK_LAST_TS : ts
                }
        return image_msg

    def spread_spath(self, msg):
        source = msg[constants.JK_SOURCE]
        dest = msg[constants.JK_DEST]
        source_ts = msg[constants.JK_SOURCE_TIMESTAMP]
        spath1 = msg[constants.JK_SHORTEST_PATH]
        if len(self.spath) == 0 or len(spath1) < len(self.spath):
            if self.devid == "AAA":
                print(f" ********* {self.devid} : Updating spath from {self.spath} to {spath1[::-1]}")
            self.spath = spath1[::-1]

            for neighbour in self.neighbours_seen:
                if neighbour in spath1:
                    continue
                new_msg = msg
                new_msg[constants.JK_DEST] = neighbour
                msg[constants.JK_SHORTEST_PATH] = spath1 + [neighbour]
                # Failure Here is OK, since it is a discovery and alternative paths would be discovered.
                self.fcomm.send_to_network(new_msg, self.devid, neighbour)

    def get_next_dest(self, msg):
        path_so_far = msg[constants.JK_PATH_SO_FAR]
        new_dest = self.get_next_on_spath()
        if new_dest in path_so_far:
            print(f"{self.devid} : new_dest : {new_dest} is in {path_so_far}")
            return None
        return new_dest
    
    def propogate_msg_to_next(self, msg, new_dest):
        new_msg = msg
        new_msg[constants.JK_DEST] = new_dest
        msg[constants.JK_PATH_SO_FAR] = msg[constants.JK_PATH_SO_FAR] + [self.devid]
        new_msg[constants.JK_LAST_TS] = time.time_ns()
        succ = self.fcomm.send_to_network(new_msg, self.devid, new_dest)
        return succ

    def propogate_message(self, msg):
        new_dest = self.get_next_dest(msg)
        sent = False
        if new_dest is not None:
            sent = self.propogate_msg_to_next(msg, new_dest)
        path_so_far = msg[constants.JK_PATH_SO_FAR]
        if not sent:
            print(f"{self.devid} : Failed to send to {new_dest} : Trying to find alternative route : path_so_far {path_so_far}")
            for n in self.neighbours_seen:
                if n in path_so_far or n == new_dest:
                    continue
                new_dest = n
                sent = self.propogate_msg_to_next(msg, new_dest)
                if sent:
                    print(f"{self.devid} : Finally succeeded to deliver to {new_dest}, path_so_far : {path_so_far}")
                    break

    def send_hb(self, ts):
        msg = self.make_hb_msg(ts)
        if msg is not None:
            self.propogate_message(msg)

    def send_image(self, ts, imdatastr, image_ts):
        msg = self.make_image_msg(ts, imdatastr, image_ts)
        if msg is not None:
            self.propogate_message(msg)

    def process_msg(self, msg):
        mtype = msg[constants.JK_MESSAGE_TYPE]
        if mtype == constants.MESSAGE_TYPE_SCAN:
            source = msg[constants.JK_SOURCE]
            if source not in self.neighbours_seen:
                self.neighbours_seen.append(source)
        if mtype == constants.MESSAGE_TYPE_SPATH:
            self.spread_spath(msg)
        # Passthrough routing
        if mtype == constants.MESSAGE_TYPE_HEARTBEAT:
            self.propogate_message(msg)
        if mtype == constants.MESSAGE_TYPE_PHOTO:
            self.propogate_message(msg)

    def check_event(self):
        if self.cam is None:
            return
        image_ts = time.time_ns()
        (imfile, imdatastr) = self.cam.take_picture()
        self.image_count = self.image_count + 1
        event_found = self.detector.ImageHasPerson(imfile)
        if event_found:
            print(f"###### {self.devid} saw an event, photo at {imfile} ######")
            self.send_image(time.time_ns(), imdatastr, image_ts)
            self.event_count = self.event_count + 1
