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
        if self.devid == "AAAaa":
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
                "message_type" : constants.MESSAGE_TYPE_SCAN,
                "source" : self.devid,
                "last_sender" : self.devid,
                "ts" : ts,
                }
        # Failure Here is OK, since it is a discovery and alternative paths would be discovered.
        self.fcomm.send_to_network(scan_msg, self.devid)

    def send_hb(self, ts):
        if self.spath == None or len(self.spath) < 2 or self.spath[0] != self.devid:
            return
        dest = self.spath[1]
        hb_msg = {
                "message_type" : constants.MESSAGE_TYPE_HEARTBEAT,
                "source" : self.devid,
                "source_ts" : ts,
                # Payload
                "neighbours" : self.neighbours_seen,
                "image_count" : self.image_count,
                "event_count" : self.event_count,
                "shortest_path" : self.spath,
                # Routing info
                "dest" : dest,
                "path_so_far" : [self.devid],
                "last_ts" : ts
                }
        self.fcomm.send_to_network(hb_msg, self.devid, dest)

    def send_image(self, ts, image_data, image_ts):
        # TODO this will need to be stored until we have spath
        if self.spath == None or len(self.spath) < 2 or self.spath[0] != self.devid:
            return
        dest = self.spath[1]
        hb_msg = {
                "message_type" : constants.MESSAGE_TYPE_PHOTO,
                "source" : self.devid,
                "source_ts" : ts,
                # Payload
                "image_data" : image_data,
                "image_ts" : image_ts,
                # Routing info
                "dest" : dest,
                "path_so_far" : [self.devid],
                "last_ts" : ts
                }
        self.fcomm.send_to_network(hb_msg, self.devid, dest)

    def spread_spath(self, msg):
        source = msg["source"]
        dest = msg["dest"]
        source_ts = msg["source_ts"]
        spath1 = msg["shortest_path"]
        if len(self.spath) == 0 or len(spath1) < len(self.spath):
            if self.devid == "AAA":
                print(f" ********* {self.devid} : Updating spath from {self.spath} to {spath1[::-1]}")
            self.spath = spath1[::-1]

            for neighbour in self.neighbours_seen:
                if neighbour in spath1:
                    continue
                new_msg = msg
                new_msg["dest"] = neighbour
                msg["shortest_path"] = spath1 + [neighbour]
                new_msg["network_ts"] = time.time_ns()
                # Failure Here is OK, since it is a discovery and alternative paths would be discovered.
                self.fcomm.send_to_network(new_msg, self.devid, neighbour)

    def get_next_dest(self, msg):
        curr_dest = msg["dest"]
        if curr_dest != self.devid:
            print(f"Weird that {curr_dest} is not {self.devid:}")
            return None
        new_dest = self.get_next_on_spath()
        # TODO If already on path_so_far then pick a random neighbour not on path_so_far
        return new_dest
    
    def propogate_msg_to_next(self, msg, new_dest):
        new_msg = msg
        new_msg["dest"] = new_dest
        msg["path_so_far"] = msg["path_so_far"] + [self.devid]
        new_msg["last_ts"] = time.time_ns()
        succ = self.fcomm.send_to_network(new_msg, self.devid, new_dest)
        return succ

    def propogate_message(self, msg):
        new_dest = self.get_next_dest(msg)
        if new_dest is not None:
            sent = self.propogate_msg_to_next(msg, new_dest)
            if not sent:
                print(f"{self.devid} : Failed to deliver, find alternative route")

    def process_msg(self, msg):
        mtype = msg["message_type"]
        if mtype == constants.MESSAGE_TYPE_SCAN:
            source = msg["source"]
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
