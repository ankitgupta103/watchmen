import json
import time
import os
import threading
import layout
import glob
import constants

class CommandCentral:
    def __init__(self, nodename, dname):
        self.nodename = nodename
        self.dname = dname
        self.neighbours_seen = []
        self.simulated_layout = layout.Layout()
        
        # Node : List of neighbours, Shortest Path, Num HBs
        self.node_list = []

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
                    "last_ts" : ts,
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
                data["hack_fname"] = fpath
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
        print(f" --- AT CC -- {source} : {hb_msg}")

    def get_hb_messages(self):
        hb_msgs = self.get_msgs_of_type("hb")
        for msg in hb_msgs:
            source = msg["source"]
            last_sender = msg["last_sender"]
            if not self.simulated_layout.is_neighbour(last_sender, self.nodename):
                continue
            else:
                self.consume_hb(msg)
                os.remove(msg["hack_fname"])

    def listen_once(self):
        self.get_scan_messages()
        self.get_hb_messages()
        
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
