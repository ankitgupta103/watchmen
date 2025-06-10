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

class CommandCenter:
    def __init__(self, devid):
        self.devid = devid
        self.rf = RFComm(devid)
        self.rf.add_node(self)
        self.rf.keep_reading()
        self.node_map = {} # id->(num HB, last HB, Num photos, Num events, [Event TS])
        self.images_saved = []
        self.msgids_seen = []

    def print_status(self):
        while True:
            print("######### Command Center printing status ##############")
            for x in self.node_map.keys():
                print(f" ####### {x} : {self.node_map[x]}")
            for x in self.images_saved:
                print(f"Saved image : {x}")
            print("#######################################################")
            time.sleep(10)

    def process_image(self, msgstr):
        try:
            orig_msg = json.loads(msgstr)
        except Exception as e:
            print(f"Error loadig json {e}")
        print("Checking for image")
        if "i_d" in orig_msg:
            print("Seems like an image")
            imstr = orig_msg["i_d"]
            im = image.imstrtoimage(imstr)
            fname = f"/tmp/commandcenter_{random.randint(1000,2000)}.jpg"
            print(f"Saving image to {fname}")
            im.save(fname)
            self.images_saved.append(fname)
            # im.show()

    # A:1205:100:12
    def process_hb(self, hbstr):
        parts = hbstr.split(':')
        if len(parts) != 4:
            print(f"Error parsing hb : {hbstr}")
            return
        nodeid = parts[0]
        hbtime = parts[1]
        photos_taken = int(parts[2])
        events_seen = int(parts[3])
        hbcount = 0
        eventtslist = []
        if nodeid not in self.node_map.keys():
            hbcount = 1
        else:
            (hbc, _, _, _, el) = self.node_map[nodeid]
            hbcount = hbc + 1
            eventtslist = el
        self.node_map[nodeid] = (hbcount, hbtime, photos_taken, events_seen, eventtslist)
    
    # A:1205
    def process_event(self, eventstr):
        parts = eventstr.split(':')
        if len(parts) != 2:
            print(f"Error parsing event message : {eventstr}")
            return
        nodeid = parts[0]
        eventtime = parts[1]
        if nodeid not in self.node_map:
            print(f"Wierd that node {nodeid} not in map yet")
            return
        (hbcount, hbtime, photos_taken, events_seen, event_ts_list) = self.node_map[nodeid]
        event_ts_list.append(eventtime)
        self.node_map[nodeid] = (hbcount, hbtime, photos_taken, events_seen, event_ts_list)

    def process_msg(self, msgid, mst, msgstr):
        if msgid not in self.msgids_seen:
            self.msgids_seen.append(msgid)
        else:
            print(f"Skipping message id : {msgid}")
            return
        if mst == constants.MESSAGE_TYPE_PHOTO:
            print(f"########## Image receive at command center")
            self.process_image(msgstr)
        elif mst == constants.MESSAGE_TYPE_HEARTBEAT:
            print(f"########## Messsage receive at command center : {mst} : {msgstr}")
            self.process_hb(msgstr)
        elif mst == constants.MESSAGE_TYPE_EVENT:
            print(f"########## Messsage receive at command center : {mst} : {msgstr}")
            self.process_event(msgstr)
        return True

class DevUnit:
    msg_queue = [] # str, type, dest tuple list
    msg_queue_lock = threading.Lock()

    def __init__(self, devid):
        self.devid = devid
        self.rf = RFComm(devid)
        self.rf.add_node(self)
        self.rf.keep_reading()
        self.keep_propagating()
        self.msgids_seen = []

    def process_msg(self, msgid, mst, msgstr):
        if msgid not in self.msgids_seen:
            self.msgids_seen.append(msgid)
        else:
            print(f"Skipping message id : {msgid}")
            return
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
                    (msgstr, mst, dest) = self.msg_queue.pop(0)
                    to_send = True
            if to_send:
                print(f"Propagating message {mst} to {dest}")
                self.rf.send_message(msgstr, mst, dest)
            time.sleep(0.5)

    # Non blocking, background thread
    def keep_propagating(self):
        # Start background thread to read incoming data
        propogation_thread = threading.Thread(target=self._keep_propagating, daemon=True)
        # TODO fix and make it a clean exit on self deletion
        propogation_thread.start()

    def keep_sending_to_cc(self, has_camera):
        # self.send_gps()
        # time.sleep(10)
        photos_taken = 0
        events_seen = 0
        while True:
            self.send_heartbeat(photos_taken, events_seen)
            time.sleep(5)
            self.send_heartbeat(photos_taken, events_seen)
            time.sleep(5)
            # TODO take photo
            photos_taken += 1
            if has_camera:
                events_seen += 1
                time.sleep(5)
                self.send_event()
                time.sleep(10)
                self.send_img("testdata/cropped.jpg")
                time.sleep(60)
                self.send_img("testdata/forest_man_2.jpg")
            time.sleep(1800) # Every 30 mins

    # A:1205:100:12
    # Name, time, images taken, events noticed.
    def send_heartbeat(self, photos_taken, events_seen):
        t = get_time_str()
        msgstr = f"{self.devid}:{t}:{photos_taken}:{events_seen}"
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
    if is_node_dest(devid):
        cc = CommandCenter(devid)
        cc.print_status()
    else:
        du = DevUnit(devid)
        has_camera = False
        if len(sys.argv) > 1:
            has_camera = sys.argv[1] == "c"
        du.keep_sending_to_cc(has_camera)
    time.sleep(10000000)

def main():
    run_unit()

if __name__=="__main__":
    main()
