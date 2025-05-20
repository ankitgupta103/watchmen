import time
import os
import threading
import constants
import device_info
import json
import layout
import central
import glob

class FileCommunicator:
    def __init__(self, dname, devid):
        self.dname = dname
        self.devid = devid
        print(f" Network simulated by {self.dname}")
        os.makedirs(self.dname, exist_ok=True)

    def _write_json_to_file(self, msg, prefix, dest=None):
        fname = f"{self.dname}/{prefix}_{self.devid}_{time.time_ns()}"
        if dest is not None:
            fname = f"{self.dname}/{prefix}_{self.devid}_to_{dest}_{time.time_ns()}"
        with open(fname, 'w') as f:
            json.dump(msg, f)

    def read_msgs_of_type(self, scantype):
        fnames = glob.glob(f"{self.dname}/{scantype}_*")
        if scantype == "spath" or scantype == "hb":
            fnames = glob.glob(f"{self.dname}/{scantype}_*to_{self.devid}*")
        all_msgs = []
        for fname in fnames:
            fpath = os.path.join(self.dname, fname)
            with open(fpath, 'r') as f:
                data = json.load(f)
                data["hack_fname"] = fpath
                all_msgs.append(data)
        return all_msgs

    def ack_message(self, msg):
        # print(f"DELETING {msg['hack_fname']}")
        os.remove(msg["hack_fname"])
