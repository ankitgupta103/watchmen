import json
import time
import os
import threading
import layout
import glob
import constants

class CommandCentral:
    def __init__(self, nodename, dname):
        # Node : List of neighbours, Shortest Path, Num HBs
        self.nodename = nodename
        self.dname = dname
        self.simulated_layout = layout.Layout()
        
        self.node_list = []

        self.neighbours_seen = []

    def print_node_info(self, node):
        #print(node)
        pass

    def _write_json_to_file(self, msg, dest):
        fname = f"{self.dname}/spath_{self.nodename}_to_{dest}_{time.time_ns()}"
        with open(fname, 'w') as f:
            json.dump(msg, f)

    def print_map(self):
        for n in self.node_list:
            self.print_node_info(n)

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
                    "network_ts" : ts,
                }
            self._write_json_to_file(spath_msg, neighbour)
        return True

    def get_msgs_of_type(self, scantype):
        fnames = glob.glob(f"{self.dname}/{scantype}_*")
        all_msgs = []
        for fname in fnames:
            fpath = os.path.join(self.dname, fname)
            with open(fpath, 'r') as f:
                data = json.load(f)
                all_msgs.append(data)
        return all_msgs

    def get_scan_messages(self):
        print("in CC SCAN")
        scan_msgs = self.get_msgs_of_type("scan")
        for msg in scan_msgs:
            source = msg["source"]
            if self.simulated_layout.is_neighbour(source, self.nodename):
                if source not in self.neighbours_seen:
                    self.neighbours_seen.append(source)

    def get_hb_messages(self):
        pass

    def listen_once(self):
        self.get_scan_messages()
        
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
