import json
import time
import os
import threading
import glob
import constants
from file_communicator import FileCommunicator

class NodeInfo:
    def __init__(self, devid):
        self.devid = devid
        self.hb_count = 0
        self.latest_hb_ts = 0
        self.all_hb_ts = []
        self.neighbours = []
        self.shortest_path = []
        self.num_images_captured = 0
        self.num_events_reported = 0

    def add_hb(self, ts, neighbours, shortest_path, image_count, event_count):
        if ts not in self.all_hb_ts:
            self.hb_count = self.hb_count + 1
            self.all_hb_ts.append(ts)
            if self.latest_hb_ts < ts:
                self.latest_hb_ts = ts
                self.neighbours = neighbours
                self.shortest_path = shortest_path
                self.num_images_captured = image_count
                self.num_events_reported = event_count

    def print_info(self):
        print(f"""AtCC Node {self.devid}:
                ---- Num HBs = {self.hb_count}
                ---- Latest HB = {self.latest_hb_ts}
                ---- HB Timestamps = {self.all_hb_ts}
                ---- Neighbours = {self.neighbours}
                ---- Shortest Pats to CC = {self.shortest_path}
                ---- Num images processed = {self.num_images_captured}
                ---- Num events reported = {self.num_events_reported}
                """)

class CommandCentral:
    def __init__(self, devid, fcomm):
        self.devid = devid
        self.neighbours_seen = []
        self.fcomm = fcomm
        
        # Node : NodeInfo
        self.node_list = {}

    def console_output(self):
        for n, info in self.node_list.items():
            info.print_info()

    def send_spath(self):
        for neighbour in self.neighbours_seen:
            ts = time.time_ns()
            spath_msg = {
                    "message_type" : constants.MESSAGE_TYPE_SPATH,
                    "source" : self.devid,
                    "dest" : neighbour,
                    "source_ts" : ts,
                    "shortest_path" : [self.devid, neighbour],
                    "last_sender" : self.devid,
                    "last_ts" : ts,
                }
            self.fcomm.send_to_network(spath_msg, self.devid, neighbour)
        return True

    def parse_hb_msg(self, msg):
        source = msg["source"]
        dest = msg["dest"]
        source_ts = msg["source_ts"]
        path_so_far = msg["path_so_far"]
        msg_spath = msg["shortest_path"]
        neighbours = msg["neighbours"]
        image_count = msg["image_count"]
        event_count = msg["event_count"]
        return (source, dest, source_ts, path_so_far, msg_spath, neighbours, image_count, event_count)

    def consume_hb(self, msg):
        hb_msg = self.parse_hb_msg(msg)
        (source, dest, source_ts, path_so_far, msg_spath, neighbours, image_count, event_count) = hb_msg
        if source not in self.node_list:
            self.node_list[source] = NodeInfo(source)
        info = self.node_list[source]
        info.add_hb(source_ts, neighbours, msg_spath, image_count, event_count)

    def consume_image(self, msg):
        print(f" %%%%%% ==== CC got an image from {msg['source']}")
        print(f" ****** ==== ====================={msg['image_data']}")

    def process_msg(self, msg):
        mtype = msg["message_type"]
        if mtype == constants.MESSAGE_TYPE_SCAN:
            source = msg["source"]
            if source not in self.neighbours_seen:
                self.neighbours_seen.append(source)
        if mtype == constants.MESSAGE_TYPE_HEARTBEAT:
            self.consume_hb(msg)
        if mtype == constants.MESSAGE_TYPE_PHOTO:
            self.consume_image(msg)

def main():
    cc = CommandCentral("ZZZ", "/tmp/network_sim_1747651680792971540/")
    # tl = cc.keep_listening()
    print("###### Central Command #######")
    #tl.join()
    cc.listen_once()

if __name__=="__main__":
    main()
