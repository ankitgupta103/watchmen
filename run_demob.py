from datetime import datetime
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

def get_time_str():
    t = datetime.now()
    return f"{str(t.hour).zfill(2)}{str(t.minute).zfill(2)}"

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
            print(f"In Passthrough mode, trying to aquire lock")
            with self.msg_queue_lock:
                print(f"{self.devid} Adding message to send queue for {next_dest}")
                self.msg_queue.append((msgstr, mst, next_dest))
        if is_node_src(self.devid):
            print(f"{self.devid}: Src should not be getting any messages")
        if is_node_dest(self.devid):
            print(f"########## Messsage receive at command center : {mst} : {msgstr}")
            if mst == constants.MESSAGE_TYPE_PHOTO:
                save_image(msgstr)
            # TODO else process heartbeats etc

    def send_img(self, imgfile):
        next_dest = get_next_dest(self.devid)
        if next_dest == None:
            print(f"{self.devid} Weird no dest for {self.devid}")
            return
        mst = constants.MESSAGE_TYPE_PHOTO
        im = {"i_m" : "{imgfile}",
              "i_s" : self.devid,
              "i_t" : str(int(time.time())),
              "i_d" : image.image2string(imgfile)}
        msgstr = json.dumps(im)
        self.rf.send_message(msgstr, mst, next_dest)

    def _keep_propagating(self):
        while True:
            to_send = False
            msgstr = None
            mst = ""
            dest = ""
            with self.msg_queue_lock:
                if len(self.msg_queue) > 0:
                    (msgstr, mst, dest) = self.msg_queue.pop()
                    to_send = True
            if to_send:
                print(f"Propagating message {mst} to {dest}")
                self.rf.send_message(msgstr, mst, dest)
            time.sleep(2)

    # Non blocking, background thread
    def keep_propagating(self):
        # Start background thread to read incoming data
        propogation_thread = threading.Thread(target=self._keep_propagating, daemon=True)
        # TODO fix and make it a clean exit on self deletion
        propogation_thread.start()

    def keep_sending_to_cc(self):
        self.send_gps()
        time.sleep(10)
        photos_taken = 0
        events_seen = 0
        while True:
            self.send_heartbeat()
            # TODO take photo
            photos_taken += 1
            if is_node_src(self.devid) and photos_taken == 2: # Hack this should be is person detected
                events_seen += 1
                self.send_event()
                time.sleep(10)
                self.send_img("testdata/cropped.jpg")
                time.sleep(60)
                self.send_img("testdata/forest_man_2.jpg")
            time.sleep(60)

    # A:1205:100:12
    # Name, time, images taken, events noticed.
    def send_heartbeat(self):
        t = get_time_str()
        msgstr = f"{self.devid}:{t}:1000:12"
        next_dest = get_next_dest(self.devid)
        self.rf.send_message(msgstr, constants.MESSAGE_TYPE_HEARTBEAT, next_dest)

    # A:23.1,67.1
    # Name:GPS
    def send_gps(self):
        next_dest = get_next_dest(self.devid)
        msgstr = f"{self.devid}:28.4:77.0"
        self.rf.send_message(msgstr, constants.MESSAGE_TYPE_GPS, next_dest)

    # A:1205
    # Name, time
    def send_event(self):
        t = get_time_str()
        msgstr = f"{self.devid}:{t}"
        next_dest = get_next_dest(self.devid)
        self.rf.send_message(msgstr, constants.MESSAGE_TYPE_EVENT, next_dest)

def run_unit():
    hname = get_hostname()
    if hname not in constants.HN_ID:
        return None
    devid = constants.HN_ID[hname]
    du = DevUnit(devid)
    if not is_node_dest(devid):
        du.keep_sending_to_cc()
    time.sleep(10000000)

def main():
    run_unit()

if __name__=="__main__":
    main()
