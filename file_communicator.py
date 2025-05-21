import time
import os
import threading
import constants
import json
import layout
import glob

class FileCommunicator:
    def __init__(self, dname, devid):
        self.dname = dname
        self.devid = devid
        print(f" Network simulated by {self.dname}")
        os.makedirs(self.dname, exist_ok=True)
        # This is a simulated network layout, it is only used to "receive" messages which a real network can see.
        self.simulated_layout = layout.Layout()

    # Send msg of mtype to dest, None=all neighbours (broadcast mode).
    def send_to_network(self, msg, dest=None):
        mtype = msg["message_type"]
        fname = f"{self.dname}/{mtype}_{self.devid}_{time.time_ns()}"
        if dest is not None:
            fname = f"{self.dname}/{mtype}_{self.devid}_to_{dest}_{time.time_ns()}"
        with open(fname, 'w') as f:
            json.dump(msg, f)

    # Read messages of type.
    # Assumes that spath and hb are unicasts and hence fileformat assumes destination.
    # Also hacks in a fname into the message so they can be acked later.
    def read_msgs_of_type(self, mtype):
        fnames = glob.glob(f"{self.dname}/{mtype}_*")
        if mtype != constants.MESSAGE_TYPE_SCAN:
            fnames = glob.glob(f"{self.dname}/{mtype}_*to_{self.devid}*")
        all_msgs = []
        for fname in fnames:
            fpath = os.path.join(self.dname, fname)
            with open(fpath, 'r') as f:
                data = json.load(f)
                last_sender = data["last_sender"]
                if last_sender != self.devid and self.simulated_layout.is_neighbour(last_sender, self.devid):
                    data["hack_fname"] = fpath
                    all_msgs.append(data)
        return all_msgs

    # Def acks message by deleting the file
    def ack_message(self, msg):
        # print(f"DELETING {msg['hack_fname']}")
        os.remove(msg["hack_fname"])
