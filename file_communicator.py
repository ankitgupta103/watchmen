import time
import os
import threading
import constants
import device_info
import json

class FileCommunicator:

    def __init__(self, dinfo, ndir):
        self.ndir = ndir 
        print(f" Network simulated by {self.ndir}")
        os.makedirs(self.ndir, exist_ok=True)
        self.dinfo = dinfo
        self.read_files = []
        self.messages_processed = []
        self.neighbours_seen = []
    
    def _write_json_to_file(self, msg):
        fname = f"{self.ndir}/hb_{time.time_ns()}"
        with open(fname, 'w') as f:
            json.dump(msg, f)

    def send_heartbeat(self, ts):
        hb_msg = {
                "message_type" : constants.MESSAGE_TYPE_HEARTBEAT,
                "hb_id" : self.dinfo.device_id_str,
                "hb_ts" : ts,
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
        print(data)
        message_type = data['message_type']
        message_id = data['message_id']
        last_sender = data['last_sender']
        if last_sender != self.dinfo.device_id_str and last_sender not in self.neighbours_seen:
            print("I saw a new neighbour")
            self.neighbours_seen.append(last_sender)
        if message_id in self.messages_processed:
            print("Skipping already processed message")
            return
        if message_type != constants.MESSAGE_TYPE_HEARTBEAT:
            print("Skipping non HB message")
            self.messages_processed.append(message_id)
            return
        if last_sender == self.dinfo.device_id_str:
            print("Self Message, Skipping")
            self.messages_processed.append(message_id)
            return
        path_so_far = data['path_so_far']
        if self.dinfo.device_id_str in path_so_far:
            print("Cyclic Message, Skipping")
            self.messages_processed.append(message_id)
            return
        hb_id = data['hb_id']
        hb_ts = data['hb_ts']
        network_ts = data['network_ts']

        # If desired_path_1,2 not empty and I am not on desired path, skip
        # else (if desired_path is empty OR I am on desired_path)

        path_so_far.append(self.dinfo.device_id_str)
        hb_msg = {
                "message_type" : constants.MESSAGE_TYPE_HEARTBEAT,
                "hb_id" : hb_id,
                "hb_ts" : hb_ts,
                "desired_path1" : [],
                "desired_path2" : [],
                "path_so_far" : path_so_far,
                "last_sender" : self.dinfo.device_id_str,
                "network_ts" : time.time_ns(),
                "message_id" : message_id,
                }
        self._write_json_to_file(hb_msg)
        
        self.messages_processed.append(message_id)

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
            if fpath in self.read_files:
                print(f"already read {f}")
            else:
                unread_files.append(fpath)
        print(f"Unread files : {len(unread_files)}, Total files : {len(all_files)}")
        for unread_fpath in unread_files:
            with open(unread_fpath, 'r') as f:
                data = json.load(f)
                self.process_msg(data)
            self.read_files.append(unread_fpath)

    def _keep_listening(self):
        while True:
            self._listen_once()
            time.sleep(2)

    def keep_listening(self):
        thread_listen = threading.Thread(target=self._keep_listening)
        thread_listen.start()
        return thread_listen



def main():
    dirname = "network_sim"
    
    dinfo1 = device_info.DeviceInfo("AAAA")
    comm1 = FileCommunicator(dinfo1, dirname)

    dinfo2 = device_info.DeviceInfo("BBBB")
    comm2 = FileCommunicator(dinfo2, dirname)

    thread_listen_1 = comm1.keep_listening()
    thread_listen_2 = comm2.keep_listening()

    for i in range(10):
        comm1.send_heartbeat(time.time_ns())
        time.sleep(1)
        comm2.send_heartbeat(time.time_ns())
        time.sleep(4)

    thread_listen_1.join()
    thread_listen_2.join()

if __name__=="__main__":
    main()
