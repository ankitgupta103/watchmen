import time
import os
import threading
import constants
import device_info
import json
import layout
import central

class FileCommunicator:
    def __init__(self, dinfo, ndir):
        self.ndir = ndir 
        print(f" Network simulated by {self.ndir}")
        os.makedirs(self.ndir, exist_ok=True)
        self.dinfo = dinfo
        self.read_files = []
        self.messages_processed = []
        self.neighbours_seen = []
        # This is a simulated network layout, it is only used to "receive" messages which a real network can see.
        self.simulated_layout = layout.Layout()
    
    def _write_json_to_file(self, msg):
        fname = f"{self.ndir}/hb_{time.time_ns()}"
        with open(fname, 'w') as f:
            json.dump(msg, f)

    def print_state(self):
        print(f"Node: {self.dinfo.device_id_str}, Messages processed: {len(self.messages_processed)}, Neighbours = {self.neighbours_seen}")

    def send_heartbeat(self, ts):
        hb_msg = {
                "message_type" : constants.MESSAGE_TYPE_HEARTBEAT,
                "hb_id" : self.dinfo.device_id_str,
                "hb_ts" : ts,
                "neighbours" : self.neighbours_seen,
                "desired_path1" : [],
                "desired_path2" : [],
                "path_so_far" : [self.dinfo.device_id_str],
                "last_sender" : self.dinfo.device_id_str,
                "network_ts" : ts,
                "message_id" : f"hb_{self.dinfo.device_id_str}_{ts}",
                }
        self._write_json_to_file(hb_msg)
        return True

    def process_msg(self, data):
        message_type = data['message_type']
        message_id = data['message_id']
        last_sender = data['last_sender']
        if not self.simulated_layout.is_neighbour(last_sender, self.dinfo.device_id_str):
            # print("I did not see this because it isnt in range in reality")
            return
        if last_sender == self.dinfo.device_id_str:
            # print("Self Message, Skipping")
            return
        if message_type != constants.MESSAGE_TYPE_HEARTBEAT:
            print("Skipping non HB message")
            return
        #if message_id in self.messages_processed:
            #print("Skipping already processed message")
        #    return
        self.messages_processed.append(message_id)
        if last_sender != self.dinfo.device_id_str and last_sender not in self.neighbours_seen:
            #print(f"I saw a new neighbour : {self.dinfo.device_id_str} : {last_sender}")
            self.neighbours_seen.append(last_sender)
        path_so_far = data['path_so_far']
        if self.dinfo.device_id_str in path_so_far:
 #           print(f"{self.dinfo.device_id_str} : Cyclic Message, Skipping : {path_so_far}")
            return
        hb_id = data['hb_id']
        hb_ts = data['hb_ts']
        hb_network_ts = data['network_ts']
        hb_neighbours = data["neighbours"]

        # If desired_path_1,2 not empty and I am not on desired path, skip
        # else (if desired_path is empty OR I am on desired_path)

        path_so_far.append(self.dinfo.device_id_str)
        hb_msg = {
                "message_type" : constants.MESSAGE_TYPE_HEARTBEAT,
                "hb_id" : hb_id,
                "hb_ts" : hb_ts,
                "neighbours" : hb_neighbours,
                "desired_path1" : [],
                "desired_path2" : [],
                "path_so_far" : path_so_far,
                "last_sender" : self.dinfo.device_id_str,
                "network_ts" : time.time_ns(),
                "message_id" : message_id,
                }
        self._write_json_to_file(hb_msg)

    def _listen_once(self):
        filenames = os.listdir(self.ndir)
        all_files = []
        unread_files = []
        for f in filenames:
            fpath = os.path.join(self.ndir, f)
            if not os.path.isfile(fpath):
                print(f"{fpath} isnt a file....")
                continue
            all_files.append(fpath)
            if fpath not in self.read_files:
                unread_files.append(fpath)
        # print(f"Unread files : {len(unread_files)}, Total files : {len(all_files)}")
        for unread_fpath in unread_files:
            with open(unread_fpath, 'r') as f:
                data = json.load(f)
                self.process_msg(data)
            self.read_files.append(unread_fpath)

    def _keep_listening(self):
        while True:
            self._listen_once()
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

    for j in range(10):
        for comm in comms:
            comm.send_heartbeat(time.time_ns())
            time.sleep(0.001)
        print(f"{j} rounds of HB done.")
        cc.listen_once()
        time.sleep(5)
    for comm in comms:
        comm.print_state()

    #for i in range(num_units):
    #    listen_threads[i].join()

if __name__=="__main__":
    main()
