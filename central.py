import json
import time
import os
import threading
import layout

class NodeSummary:
    def __init__(self, name):
        self.name = ""

def sort_tuples(tuples, a, b, c):
    key_func = lambda x: (x[a], x[b], x[c])
    return sorted(tuples, key=key_func)

class CommandCentral:
    def __init__(self, nodename, dname):
        # Node : List of neighbours, Shortest Path, Num HBs
        self.nodename = nodename
        self.node_list = []
        self.dname = dname
        self.simulated_layout = layout.Layout()
    
    def print_node_info(self, node):
        #print(node)
        pass

    def print_map(self):
        for n in self.node_list:
            self.print_node_info(n)

    def send_to_node(self):
        pass

    def get_hb_from_msg(self, data):
        # None
        # (node name, TS, path so far, neighbours)
        message_type = data["message_type"]
        message_id = data["message_id"]
        last_sender = data["last_sender"]
        hb_id = data["hb_id"]
        hb_ts = data["hb_ts"]
        neighbours = data["neighbours"]
        network_ts = data["network_ts"]
        path_so_far = data["path_so_far"]
        return (hb_id, hb_ts, neighbours, network_ts, path_so_far)

    def process_msgs(self, all_msgs):
        unit_HBs = {} # DevID -> [HBInfo]
        for msg in all_msgs:
            hbinfo = self.get_hb_from_msg(msg)
            if hbinfo == None:
                continue
            (name, ts, neighbours, network_ts, path_so_far) = hbinfo
            if name not in unit_HBs:
                unit_HBs[name] = [hbinfo]
            else:
                unit_HBs[name].append(hbinfo)
        return unit_HBs

    def summarize_node(self, name, hbs):
        sorted_hbs = sort_tuples(hbs, 0, 1, 3)
        for hb in sorted_hbs:
            print(hb)

    def listen_once(self):
        filenames = os.listdir(self.dname)
        all_files = []
        for f in filenames:
            fpath = os.path.join(self.dname, f)
            if not os.path.isfile(fpath):
                print(f"{fpath} isnt a file....")
                continue
            all_files.append(fpath)
        all_msgs = []
       
        for unread_fpath in all_files:
            with open(unread_fpath, 'r') as f:
                data = json.load(f)
                if self.simulated_layout.is_neighbour(data["last_sender"], self.nodename):
                    all_msgs.append(data)

        unit_HBs = self.process_msgs(all_msgs)
        for k,v in unit_HBs.items():
            print(f"{k} : {len(v)}")
            self.summarize_node(k, v)
        
    def _keep_listening(self):
        while True:
            self.listen_once()
            self.print_map()

    def keep_listening(self):
        thread_listen = threading.Thread(target=self._keep_listening)
        thread_listen.start()
        return thread_listen

def main():
    cc = CommandCentral("ZZZ", "/tmp/network_sim_1747643811251458546")
    # tl = cc.keep_listening()
    print("###### Central Command #######")
    #tl.join()
    cc.listen_once()

if __name__=="__main__":
    main()
