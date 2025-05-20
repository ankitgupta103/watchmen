import time
import os
import threading
import constants
import device_info
import json
import layout
import central
import glob
from file_communicator import FileCommunicator
from detect import Detector
from camera import Camera

class Device:
    def __init__(self, devid, dname):
        self.devid = devid
        self.neighbours_seen = []
        self.spath = []
        # This is a simulated network layout, it is only used to "receive" messages which a real network can see.
        self.simulated_layout = layout.Layout()
        # This ia a communication running in a simulated directory
        self.fcomm = FileCommunicator(dname, devid)
        self.detector = Detector()
        self.detector.set_debug_mode()
        self.cam = None
        if self.devid == "AAA":
            self.cam = Camera(devid, o_dir="/tmp/camera_captures_test")
            self.cam.start()
        self.image_count = 0
        self.event_count = 0

    def send_scan(self, ts):
        scan_msg = {
                "message_type" : constants.MESSAGE_TYPE_SCAN,
                "source" : self.devid,
                "ts" : ts,
                }
        self.fcomm.send_to_network(scan_msg, "scan")

    def send_hb(self, ts):
        if self.spath == None or len(self.spath) < 2 or self.spath[0] != self.devid:
            #print(f"{self.devid} : Not sending HB because spath not good : {self.spath}")
            return
        # Send to next on shortest path
        dest = self.spath[0]
        hb_msg = {
                "message_type" : constants.MESSAGE_TYPE_HEARTBEAT,
                "source" : self.devid,
                "neighbours" : self.neighbours_seen,
                "shortest_path" : self.spath,
                "dest" : dest,
                "path_so_far" : [self.devid],
                "source_ts" : ts,
                "last_sender" : self.devid,
                "image_count" : self.image_count,
                "event_count" : self.event_count,
                "last_ts" : ts
                }
        self.fcomm.send_to_network(hb_msg, "hb", dest)

    def propogate_spath(self, msg):
        source = msg["source"]
        dest = msg["dest"]
        source_ts = msg["source_ts"]
        spath1 = msg["shortest_path"]

        if len(self.spath) == 0 or len(spath1) < len(self.spath):
            #print(f"{self.devid} : Updating spath from {self.spath} to {spath1}")
            self.spath = spath1[::-1]

            for neighbour in self.neighbours_seen:
                if neighbour in spath1:
                    continue
                new_msg = msg
                new_msg["dest"] = neighbour
                msg["shortest_path"] = spath1 + [neighbour]
                new_msg["last_sender"] = self.devid
                new_msg["network_ts"] = time.time_ns()
                self.fcomm.send_to_network(new_msg, "spath", neighbour)

    def propogate_hb(self, msg):
        dest = msg["dest"]
        source = msg["source"]
        msg_spath = msg["shortest_path"]
        path_so_far = msg["path_so_far"]
        if len(path_so_far) >= len(msg_spath):
            #print(f"Finished")
            return
        if dest != self.devid:
            print(f"Weird that {dest} is not {self.devid:}")
            return
        new_dest = msg_spath[len(path_so_far)] # Get the next item
        new_path_so_far = path_so_far + [new_dest]

        #print(f"{self.devid} : Sending {source}'s HB to {new_dest}, spath = {msg_spath}, path_so_far = {path_so_far}")
        new_msg = msg
        new_msg["dest"] = new_dest
        msg["path_so_far"] = new_path_so_far
        new_msg["last_sender"] = self.devid
        new_msg["last_ts"] = time.time_ns()
        self.fcomm.send_to_network(new_msg, "hb", new_dest)

    def process_spath(self):
        spath_msgs = self.fcomm.read_msgs_of_type("spath")
        for msg in spath_msgs:
            source = msg["source"]
            last_sender = msg["last_sender"]
            if not self.simulated_layout.is_neighbour(last_sender, self.devid):
                continue
            else:
                self.propogate_spath(msg)
                self.fcomm.ack_message(msg)

    def process_hb(self):
        hb_msgs = self.fcomm.read_msgs_of_type("hb")
        for msg in hb_msgs:
            source = msg["source"]
            last_sender = msg["last_sender"]
            if not self.simulated_layout.is_neighbour(last_sender, self.devid):
                continue
            else:
                self.propogate_hb(msg)
                self.fcomm.ack_message(msg)

    def process_scans(self):
        scan_msgs = self.fcomm.read_msgs_of_type("scan")
        for msg in scan_msgs:
            source = msg["source"]
            if source == self.devid:
                continue
            if self.simulated_layout.is_neighbour(source, self.devid):
                if source not in self.neighbours_seen:
                    self.neighbours_seen.append(source)

    def listen_once(self):
        self.process_scans()
        self.process_spath()
        self.process_hb()

    def _keep_listening(self):
        while True:
            self.listen_once()
            time.sleep(1)

    def keep_listening(self):
        thread_listen = threading.Thread(target=self._keep_listening)
        thread_listen.start()
        return thread_listen
    
    def check_event(self):
        if self.cam is None:
            return
        photo = self.cam.take_picture()
        self.image_count = self.image_count + 1
        event_found = self.detector.ImageHasPerson(photo)
        if event_found:
            print(f"###### {self.devid} saw an event, photo at {photo} ######")
            self.event_count = self.event_count + 1
