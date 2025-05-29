import json
import time
import io
import base64
from PIL import Image

import image
import constants

class NodeInfo:
    def __init__(self, devid):
        self.devid = devid
        self.hb_count = 0
        self.latest_hb_ts = 0
        self.all_hb_ts = []
        self.neighbours = []
        self.shortest_path = []
        self.paths_seen = []
        self.num_images_captured = 0
        self.num_events_reported = 0
        self.num_follow_spath = 0

    def add_hb(self, ts, neighbours, shortest_path, path_so_far, image_count, event_count):
        if ts not in self.all_hb_ts:
            self.hb_count = self.hb_count + 1
            self.all_hb_ts.append(ts)
            if shortest_path == path_so_far:
                self.num_follow_spath = self.num_follow_spath + 1
            if self.latest_hb_ts < ts:
                self.latest_hb_ts = ts
                self.neighbours = neighbours
                self.shortest_path = shortest_path
                self.num_images_captured = image_count
                self.num_events_reported = event_count
                self.paths_seen.append(path_so_far)

    def print_info(self):
        print(f"""AtCC Node {self.devid}:
                ---- Num HBs = {self.hb_count}
                ---- Latest HB = {self.latest_hb_ts}
                ---- HB Timestamps = {self.all_hb_ts}
                ---- Neighbours = {self.neighbours}
                ---- Shortest Path to CC = {self.shortest_path}
                ---- Actual Path to CC = {self.paths_seen}
                ---- Num HB Actually following Shortest Path to CC = {self.num_follow_spath}
                ---- Num images processed = {self.num_images_captured}
                ---- Num events reported = {self.num_events_reported}
                """)

class CommandCentral:
    def __init__(self, devid, fcomm, ncomm):
        self.devid = devid
        self.neighbours_seen = []
        self.fcomm = fcomm
        self.ncomm = ncomm
        if fcomm is None and ncomm is None:
            print("At least one communicator")
            return None
        if fcomm is not None and ncomm is not None:
            print("At most one communicator")
            return None
        
        # Node : NodeInfo
        self.node_list = {}

        self.num_hbs_received = 0
        self.num_hbs_rerouted = 0

    def send_message(self, msg, dest=None):
        if self.fcomm is not None:
            return self.fcomm.send_to_network(msg, self.devid, dest)
        if self.ncomm is not None:
            msgstr = json.dumps(msg)
            return self.ncomm.send_message(msgstr, dest)

    def console_output(self):
        for n, info in self.node_list.items():
            info.print_info()
        print(f"\n ---- Rerouted {self.num_hbs_rerouted} out of {self.num_hbs_received} HBs")

    def send_spath(self):
        for neighbour in self.neighbours_seen:
            ts = time.time_ns()
            spath_msg = {
                    constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_SPATH,
                    constants.JK_SOURCE : self.devid,
                    constants.JK_DEST : neighbour,
                    constants.JK_SOURCE_TIMESTAMP : ts,
                    constants.JK_SHORTEST_PATH : [self.devid, neighbour],
                    constants.JK_LAST_SENDER : self.devid,
                    constants.JK_LAST_TS : ts,
                }
            self.send_message(spath_msg, neighbour)
        return True

    def parse_hb_msg(self, msg):
        source = msg[constants.JK_SOURCE]
        dest = msg[constants.JK_DEST]
        source_ts = msg[constants.JK_SOURCE_TIMESTAMP]
        path_so_far = msg[constants.JK_PATH_SO_FAR] + [self.devid]
        msg_spath = msg[constants.JK_SHORTEST_PATH]
        neighbours = msg[constants.JK_NEIGHBOURS]
        image_count = msg[constants.JK_IMAGE_COUNT]
        event_count = msg[constants.JK_EVENT_COUNT]
        return (source, dest, source_ts, path_so_far, msg_spath, neighbours, image_count, event_count)

    def consume_hb(self, msg):
        hb_msg = self.parse_hb_msg(msg)
        (source, dest, source_ts, path_so_far, msg_spath, neighbours, image_count, event_count) = hb_msg
        if source not in self.node_list:
            self.node_list[source] = NodeInfo(source)
        info = self.node_list[source]
        info.add_hb(source_ts, neighbours, msg_spath, path_so_far, image_count, event_count)
        self.num_hbs_received = self.num_hbs_received + 1
        if path_so_far != msg_spath:
            self.num_hbs_rerouted = self.num_hbs_rerouted + 1
            print(f" --- At CC Noticed rerouting from {msg_spath} to {path_so_far}")

    def consume_image(self, msg):
        imf = f"/tmp/camera_captures_test/Image_CC_{msg['constants.JK_SOURCE']}_{msg['constants.JK_IMAGE_TS']}.jpg"
        print(f" %%%%%% ==== CC got an image from {msg['constants.JK_SOURCE']}, will save to {imf}")
        im = image.imstrtoimage(msg[constants.JK_IMAGE_DATA])
        im.save(imf)
        im.show()

    def process_msg(self, msg):
        mtype = msg[constants.JK_MESSAGE_TYPE]
        if mtype == constants.MESSAGE_TYPE_SCAN:
            source = msg[constants.JK_SOURCE]
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
