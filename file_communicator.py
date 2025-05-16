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
    
    def _write_json_to_file(self, msg):
        fname = f"{self.ndir}/hb_{time.time_ns()}"
        with open(fname, 'w') as f:
            json.dump(msg, f)

    def send_heartbeat(self, ts):
        hb_msg = {
                "message_type" : "heartbeat",
                "hb_id" : self.dinfo.device_id_str,
                "hb_ts" : ts,
                "desired_path1" : [],
                "desired_path2" : [],
                "path_so_far" : [self.dinfo.device_id_str],
                "last_sender" : self.dinfo.device_id_str,
                "network_ts" : ts,
                "message_id" : f"{self.dinfo.device_id_str}_{ts}",
                }
        self._write_json_to_file(hb_msg)
        return True

    def process_msg(self):
        pass

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
                process_msg(data)
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
    dinfo = device_info.DeviceInfo("AAAA")
    comm = FileCommunicator(dinfo, dirname)

    thread_listen = comm.keep_listening()

    for i in range(10):
        comm.send_heartbeat(time.time_ns())
        time.sleep(5)

    thread_listen.join()

if __name__=="__main__":
    main()
