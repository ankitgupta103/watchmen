import json
import time
import os
import threading
import layout
import glob
import constants
from file_communicator import FileCommunicator

class NodeInfo:
    def __init__(self, nodename):
        self.nodename = nodename
        self.hb_count = 0
        self.latest_hb_ts = 0
        self.all_hb_ts = []
        self.neighbours = []
        self.shortest_path = []
        self.num_images_captured = 0
        self.num_events_reported = 0

    def add_hb(self, ts, neighbours, shortest_path):
        if ts not in self.all_hb_ts:
            self.hb_count = self.hb_count + 1
            self.all_hb_ts.append(ts)
            if self.latest_hb_ts < ts:
                self.latest_hb_ts = ts
            self.neighbours = neighbours
            self.shortest_path = shortest_path

    def print_info(self):
        print(f"""AtCC Node {self.nodename}:
                ---- Num HBs = {self.hb_count}
                ---- Latest HB = {self.latest_hb_ts}
                ---- HB Timestamps = {self.all_hb_ts}
                ---- Neighbours = {self.neighbours}
                ---- Shortest Pats to CC = {self.shortest_path}
                ---- Num images processed = {self.num_images_captured}
                ---- Num events reported = {self.num_events_reported}
                """)

class CommandCentral:
    def __init__(self, nodename, dname):
        self.nodename = nodename
        self.dname = dname
        self.neighbours_seen = []
        self.simulated_layout = layout.Layout()
        self.fcomm = FileCommunicator(dname, nodename)
        
        # Node : NodeInfo
        self.node_list = {}

    def print_map(self):
        for n, info in self.node_list.items():
            info.print_info()

    def send_spath(self):
        print(f"Sending spath to {self.neighbours_seen}")
        for neighbour in self.neighbours_seen:
            ts = time.time_ns()
            spath_msg = {
                    "message_type" : constants.MESSAGE_TYPE_SPATH,
                    "source" : self.nodename,
                    "dest" : neighbour,
                    "source_ts" : ts,
                    "shortest_path" : [self.nodename, neighbour],
                    "last_sender" : self.nodename,
                    "last_ts" : ts,
                }
            self.fcomm._write_json_to_file(spath_msg, "spath", neighbour)
        return True

    def get_scan_messages(self):
        print("in CC SCAN")
        scan_msgs = self.fcomm.read_msgs_of_type("scan")
        for msg in scan_msgs:
            source = msg["source"]
            if self.simulated_layout.is_neighbour(source, self.nodename):
                if source not in self.neighbours_seen:
                    self.neighbours_seen.append(source)

    def parse_hb_msg(self, msg):
        source = msg["source"]
        dest = msg["dest"]
        source_ts = msg["source_ts"]
        path_so_far = msg["path_so_far"]
        msg_spath = msg["shortest_path"]
        neighbours = msg["neighbours"]
        return (source, dest, source_ts, path_so_far, msg_spath, neighbours)

    def consume_hb(self, msg):
        hb_msg = self.parse_hb_msg(msg)
        (source, dest, source_ts, path_so_far, msg_spath, neighbours) = hb_msg
        if source not in self.node_list:
            self.node_list[source] = NodeInfo(source)
        info = self.node_list[source]
        info.add_hb(source_ts, neighbours, msg_spath)

    def get_hb_messages(self):
        hb_msgs = self.fcomm.read_msgs_of_type("hb")
        for msg in hb_msgs:
            source = msg["source"]
            last_sender = msg["last_sender"]
            if not self.simulated_layout.is_neighbour(last_sender, self.nodename):
                continue
            else:
                self.consume_hb(msg)
                self.fcomm.ack_message(msg)

    def listen_once(self):
        self.get_scan_messages()
        self.get_hb_messages()
        self.print_map()
        
    def _keep_listening(self):
        while True:
            self.listen_once()
            time.sleep(5)

    def keep_listening(self):
        thread_listen = threading.Thread(target=self._keep_listening)
        thread_listen.start()
        return thread_listen

def main():
    cc = CommandCentral("ZZZ", "/tmp/network_sim_1747651680792971540/")
    # tl = cc.keep_listening()
    print("###### Central Command #######")
    #tl.join()
    cc.listen_once()

if __name__=="__main__":
    main()
