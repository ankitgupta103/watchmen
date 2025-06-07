import sys
import time
import threading
import image
import json
import socket
import random
from rf_comm import RFComm

import constants

def get_hostname():
    return socket.gethostname()

def is_node_src(devid):
    return constants.PATH_DEMOB[0] == devid

def is_node_dest(devid):
    return constants.PATH_DEMOB[-1] == devid

def is_node_passthrough(devid):
    if is_node_src(devid) or is_node_dest(devid):
        return False
    return True

def get_next_dest(devid):
    idx = -1
    num_nodes = len(constants.PATH_DEMOB)
    for i in range(num_nodes):
        if devid == constants.PATH_DEMOB[i]:
            if i + 1 >= num_nodes:
                return None
            else:
                return constants.PATH_DEMOB[i+1]
    return None

def save_image(msgstr):
    try:
        orig_msg = json.loads(msgstr)
        print("Checking for image")
        if "i_d" in orig_msg:
            print("Seems like an image")
            imstr = orig_msg["i_d"]
            im = image.imstrtoimage(imstr)
            fname = f"/tmp/commandcenter_{random.randint(1000,2000)}.jpg"
            print(f"Saving image to {fname}")
            im.save(fname)
            # im.show()
    except Exception as e:
        print(f"Error loadig json {e}")

class DevUnit:
    msg_queue = [] # str, type, dest tuple list
    msg_queue_lock = threading.Lock()

    def __init__(self, devid):
        self.devid = devid
        self.rf = RFComm(devid)
        self.rf.add_node(self)
        self.rf.keep_reading()
        self.keep_propagating()

    def process_msg(self, mst, msgstr):
        if is_node_passthrough(self.devid):
            next_dest = get_next_dest(self.devid)
            if next_dest == None:
                print(f"{self.devid} Weird no dest for {self.devid}")
                return
            with self.msg_queue_lock:
                print(f"{self.devid} Adding message to send queue for {next_dest}")
                self.msg_queue.append((msgstr, mst, next_dest))
        if is_node_src(self.devid):
            print(f"{self.devid}: Src should not be getting any messages")
        if is_node_dest(self.devid):
            print(f"########## Messsage receive at command center : {msgstr}")
            # Hack for now
            if len(msgstr) > 100:
                save_image(msgstr)

    def send_img(self):
        imgfile = sys.argv[1]
        next_dest = get_next_dest(self.devid)
        if next_dest == None:
            print(f"{self.devid} Weird no dest for {self.devid}")
            return
        mst = constants.MESSAGE_TYPE_PHOTO
        im = {"i_m" : "{imgfile}",
              "i_d" : image.image2string(imgfile)}
        msgstr = json.dumps(im)
        self.rf.send_message(msgstr, mst, next_dest)

    def _keep_sending(self):
        while True:
            with self.msg_queue_lock:
                if len(self.msg_queue) > 0:
                    (msgstr, mst, dest) = self.msg_queue.pop()
                    print(f"Propagating message {mst} to {dest}")
                    self.rf.send_message(msgstr, mst, dest)
                time.sleep(2)

    # Non blocking, background thread
    def keep_propagating(self):
        # Start background thread to read incoming data
        propogation_thread = threading.Thread(target=self._keep_sending, daemon=True)
        # TODO fix and make it a clean exit on self deletion
        propogation_thread.start()

def run_unit():
    hname = get_hostname()
    if hname not in constants.HN_ID:
        return None
    devid = constants.HN_ID[hname]
    du = DevUnit(devid)
    if is_node_src(devid):
        time.sleep(5)
        du.send_img()

    time.sleep(10000000)

def main():
    run_unit()

if __name__=="__main__":
    main()
