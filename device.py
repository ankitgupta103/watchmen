import time
import os
import threading
import constants
import json
import glob

from file_communicator import FileCommunicator
from detect import Detector
from camera import Camera

class Device:
    def __init__(self, devid, fcomm):
        self.devid = devid
        self.neighbours_seen = []
        self.spath = []
        self.fcomm = fcomm
        self.cam = None
        if self.devid == "AAA":
            self.cam = Camera(devid, o_dir="/tmp/camera_captures_test")
            self.cam.start()
            self.detector = Detector()
            self.detector.set_debug_mode()
        self.image_count = 0
        self.event_count = 0

    def send_scan(self, ts):
        scan_msg = {
                "message_type" : constants.MESSAGE_TYPE_SCAN,
                "source" : self.devid,
                "last_sender" : self.devid,
                "ts" : ts,
                }
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
                # Routing info
                "shortest_path" : self.spath,
                "dest" : dest,
                "path_so_far" : [self.devid, dest],
                "last_sender" : self.devid,
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
                "shortest_path" : self.spath,
                "dest" : dest,
                "path_so_far" : [self.devid, dest],
                "last_sender" : self.devid,
                "last_ts" : ts
                }
        self.fcomm.send_to_network(hb_msg, self.devid, dest)

    def propogate_spath(self, msg):
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
                new_msg["last_sender"] = self.devid
                new_msg["network_ts"] = time.time_ns()
                self.fcomm.send_to_network(new_msg, self.devid, neighbour)

    def get_route(self, msg):
        dest = msg["dest"]
        msg_spath = msg["shortest_path"]
        path_so_far = msg["path_so_far"]
        if len(path_so_far) >= len(msg_spath):
            #print(f"Finished")
            return None
        if dest != self.devid:
            print(f"Weird that {dest} is not {self.devid:}")
            return None
        new_dest = msg_spath[len(path_so_far)] # Get the next item
        return new_dest

    def propogate_hb(self, msg):
        new_dest = self.get_route(msg)
        if new_dest is None:
            return
        new_msg = msg
        path_so_far = msg["path_so_far"]
        new_path_so_far = path_so_far + [new_dest]
        new_msg["dest"] = new_dest
        msg["path_so_far"] = new_path_so_far
        new_msg["last_sender"] = self.devid
        new_msg["last_ts"] = time.time_ns()
        self.fcomm.send_to_network(new_msg, self.devid, new_dest)

    def propogate_image(self, msg):
        new_dest = self.get_route(msg)
        if new_dest is None:
            return
        new_msg = msg
        path_so_far = msg["path_so_far"]
        new_path_so_far = path_so_far + [new_dest]
        new_msg["dest"] = new_dest
        print(f" ==== SENDING IMAGE FROM {self.devid} to {new_dest}")
        msg["path_so_far"] = new_path_so_far
        new_msg["last_sender"] = self.devid
        new_msg["last_ts"] = time.time_ns()
        self.fcomm.send_to_network(new_msg, self.devid, new_dest)

    def process_msg(self, msg):
        mtype = msg["message_type"]
        if mtype == constants.MESSAGE_TYPE_SCAN:
            source = msg["source"]
            if source not in self.neighbours_seen:
                self.neighbours_seen.append(source)
        if mtype == constants.MESSAGE_TYPE_HEARTBEAT:
            self.propogate_hb(msg)
        if mtype == constants.MESSAGE_TYPE_SPATH:
            self.propogate_spath(msg)
        if mtype == constants.MESSAGE_TYPE_PHOTO:
            self.propogate_image(msg)

    def check_event(self):
        if self.cam is None:
            return
        image_ts = time.time_ns()
        photo = self.cam.take_picture()
        self.image_count = self.image_count + 1
        event_found = self.detector.ImageHasPerson(photo)
        if event_found:
            print(f"###### {self.devid} saw an event, photo at {photo} ######")
            self.send_image(time.time_ns(), "Hello this is an image", image_ts)
            self.event_count = self.event_count + 1
