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

    def print_state(self):
        print(f"Node: {self.dinfo.device_id_str}, Neighbours = {self.neighbours_seen}")
    def send_scan(self, ts):
        scan_msg = {
                "message_type" : constants.MESSAGE_TYPE_SCAN,
                "source" : self.dinfo.device_id_str,
                "ts" : ts,
                }
        self._write_json_to_file(scan_msg, "scan")

    def get_msgs_of_type(self, scantype):
        fnames = glob.glob(f"{self.dname}/{scantype}_*")
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
        spath = msg["shortest_path"]
        print(f"{self.dinfo.device_id_str} : Current = {self.spath} ...... Should update to {spath}")

        if len(self.spath) == 0 or len(spath) < len(self.spath):
            print(f"{self.dinfo.device_id_str} : Updating spath from {self.spath} tp {spath}")
            self.spath = spath

            for neighbour in self.neighbours_seen:
                spath_new = spath
                spath_new.append(neighbour)
                new_msg = msg
                new_msg["dest"] = neighbour
                msg["shortest_path"] = spath_new
                new_msg["last_sender"] = self.dinfo.device_id_str
                new_msg["network_ts"] = time.time_ns()
                self._write_json_to_file(new_msg, "spath")

    def process_spath(self):
        scan_msgs = self.get_msgs_of_type("spath")
        for msg in scan_msgs:
            source = msg["source"]
            dest = msg["dest"]
            if not self.simulated_layout.is_neighbour(source, self.dinfo.device_id_str):
                continue
            if dest == self.dinfo.device_id_str:
                self.propogate_spath(msg)
                print(f"DELETING {msg['hack_fname']}")
                os.remove(msg["hack_fname"])

    def process_scans(self):
        scan_msgs = self.get_msgs_of_type("scan")
        for msg in scan_msgs:
            source = msg["source"]
            if self.simulated_layout.is_neighbour(source, self.dinfo.device_id_str):
                if source not in self.neighbours_seen:
                    self.neighbours_seen.append(source)

    def listen_once(self):
        self.process_scans()
        self.process_spath()

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
            time.sleep(0.001)
        print(f"{j} rounds of HB done.")
        time.sleep(5)
        cc.listen_once()
        cc.send_spath()

    for comm in comms:
        comm.print_state()

    print("Waiting for 15 secs")
    time.sleep(15)
    print("Listening on command center now")
    cc.listen_once()

    #for i in range(num_units):
    #    listen_threads[i].join()

if __name__=="__main__":
    main()
