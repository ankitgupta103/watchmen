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
    def __init__(self, dinfo, dname):
        self.dname = dname
        print(f" Network simulated by {self.dname}")
        os.makedirs(self.dname, exist_ok=True)
        self.dinfo = dinfo
        self.neighbours_seen = []
        self.spath = []
        # This is a simulated network layout, it is only used to "receive" messages which a real network can see.
        self.simulated_layout = layout.Layout()

    def _write_json_to_file(self, msg, prefix):
        fname = f"{self.dname}/{prefix}_{self.dinfo.device_id_str}_{time.time_ns()}"
        with open(fname, 'w') as f:
            json.dump(msg, f)

    def _write_json_to_spath_file(self, msg, dest, prefix):
        fname = f"{self.dname}/{prefix}_{self.dinfo.device_id_str}_to_{dest}_{time.time_ns()}"
        with open(fname, 'w') as f:
            json.dump(msg, f)

    def _write_json_to_hb_file(self, msg, dest, prefix):
        fname = f"{self.dname}/{prefix}_{self.dinfo.device_id_str}_to_{dest}_{time.time_ns()}"
        with open(fname, 'w') as f:
            json.dump(msg, f)

    def print_state(self):
        print(f"Node: {self.dinfo.device_id_str}, Neighbours = {self.neighbours_seen}, spath = {self.spath}")

    def send_scan(self, ts):
        scan_msg = {
                "message_type" : constants.MESSAGE_TYPE_SCAN,
                "source" : self.dinfo.device_id_str,
                "ts" : ts,
                }
        self._write_json_to_file(scan_msg, "scan")

    def send_hb(self, ts):
        if self.spath == None or len(self.spath) < 2 or self.spath[0] != self.dinfo.device_id_str:
            #print(f"{self.dinfo.device_id_str} : Not sending HB because spath not good : {self.spath}")
            return
        # Send to next on shortest path
        dest = self.spath[0]
        hb_msg = {
                "message_type" : constants.MESSAGE_TYPE_HEARTBEAT,
                "source" : self.dinfo.device_id_str,
                "neighbours" : self.neighbours_seen,
                "shortest_path" : self.spath,
                "dest" : dest,
                "path_so_far" : [self.dinfo.device_id_str],
                "source_ts" : ts,
                "last_sender" : self.dinfo.device_id_str,
                "last_ts" : ts
                }
        self._write_json_to_hb_file(hb_msg, dest, "hb")

    def get_msgs_of_type(self, scantype):
        fnames = glob.glob(f"{self.dname}/{scantype}_*")
        if scantype == "spath" or scantype == "hb":
            fnames = glob.glob(f"{self.dname}/{scantype}_*to_{self.dinfo.device_id_str}*")
        all_msgs = []
        for fname in fnames:
            fpath = os.path.join(self.dname, fname)
            with open(fpath, 'r') as f:
                data = json.load(f)
                data["hack_fname"] = fpath
                all_msgs.append(data)
        return all_msgs

    def propogate_spath(self, msg):
        source = msg["source"]
        dest = msg["dest"]
        source_ts = msg["source_ts"]
        spath1 = msg["shortest_path"]

        if len(self.spath) == 0 or len(spath1) < len(self.spath):
            #print(f"{self.dinfo.device_id_str} : Updating spath from {self.spath} to {spath1}")
            self.spath = spath1[::-1]

            for neighbour in self.neighbours_seen:
                if neighbour in spath1:
                    continue
                new_msg = msg
                new_msg["dest"] = neighbour
                msg["shortest_path"] = spath1 + [neighbour]
                new_msg["last_sender"] = self.dinfo.device_id_str
                new_msg["network_ts"] = time.time_ns()
                self._write_json_to_spath_file(new_msg, neighbour, "spath")

    def propogate_hb(self, msg):
        dest = msg["dest"]
        source = msg["source"]
        msg_spath = msg["shortest_path"]
        path_so_far = msg["path_so_far"]
        if len(path_so_far) >= len(msg_spath):
            #print(f"Finished")
            return
        if dest != self.dinfo.device_id_str:
            print(f"Weird that {dest} is not {self.dinfo.device_id_str:}")
            return
        new_dest = msg_spath[len(path_so_far)] # Get the next item
        new_path_so_far = path_so_far + [new_dest]

        #print(f"{self.dinfo.device_id_str} : Sending {source}'s HB to {new_dest}, spath = {msg_spath}, path_so_far = {path_so_far}")
        new_msg = msg
        new_msg["dest"] = new_dest
        msg["path_so_far"] = new_path_so_far
        new_msg["last_sender"] = self.dinfo.device_id_str
        new_msg["last_ts"] = time.time_ns()
        self._write_json_to_hb_file(new_msg, new_dest, "hb")

    def process_spath(self):
        spath_msgs = self.get_msgs_of_type("spath")
        for msg in spath_msgs:
            source = msg["source"]
            last_sender = msg["last_sender"]
            if not self.simulated_layout.is_neighbour(last_sender, self.dinfo.device_id_str):
                continue
            else:
                self.propogate_spath(msg)
#                print(f"DELETING {msg['hack_fname']}")
                os.remove(msg["hack_fname"])

    def process_hb(self):
        hb_msgs = self.get_msgs_of_type("hb")
        for msg in hb_msgs:
            source = msg["source"]
            last_sender = msg["last_sender"]
            if not self.simulated_layout.is_neighbour(last_sender, self.dinfo.device_id_str):
                continue
            else:
                self.propogate_hb(msg)
 #               print(f"DELETING {msg['hack_fname']}")
                os.remove(msg["hack_fname"])

    def process_scans(self):
        scan_msgs = self.get_msgs_of_type("scan")
        for msg in scan_msgs:
            source = msg["source"]
            if source == self.dinfo.device_id_str:
                continue
            if self.simulated_layout.is_neighbour(source, self.dinfo.device_id_str):
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

def start_n_units(dirname, n):
    comms = []
    for i in range(n):
        c=chr(i+65)
        name=f"{c}{c}{c}"
        dinfo = device_info.DeviceInfo(name)
        comm = FileCommunicator(dinfo, dirname)
        comms.append(comm)
    return comms

def main():
    dirname = f"/tmp/network_sim_{time.time_ns()}"
    num_units = 25

    comms = start_n_units(dirname, num_units)

    listen_threads = []
    for i in range(num_units):
        listen_threads.append(comms[i].keep_listening())

    cc = central.CommandCentral("ZZZ", dirname)

    for j in range(5):
        for comm in comms:
            comm.send_scan(time.time_ns())
            comm.send_hb(time.time_ns())
            time.sleep(0.001)
        cc.send_spath()
        print(f"{j} rounds of Scan done.")
        time.sleep(15)
        cc.listen_once()

    #for comm in comms:
    #    comm.print_state()

    print("Waiting for 15 secs")
    time.sleep(15)
    print("Listening on command center now")
    cc.listen_once()

    #for i in range(num_units):
    #    listen_threads[i].join()

if __name__=="__main__":
    main()
