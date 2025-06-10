from datetime import datetime
import os
import sys
import time
import threading
import image
import json
import socket
import random
from rf_comm import RFComm
from vyom_client import VyomClient

import gps
import constants

ALLDIR = "../processed"
CRITICAL_DIR = "../processed/critical"

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

def get_files_in_dir(alldir, criticaldir):
    allfiles = []
    for a in os.listdir(alldir):
        allfiles.append(os.path.join(alldir, a))
    total_images_taken = len(allfiles)
    criticalfiles = []
    for c in os.listdir(criticaldir):
        criticalfiles.append(os.path.join(criticaldir, c))
    return (total_images_taken, criticalfiles)

def get_time_str():
    t = datetime.now()
    return f"{str(t.hour).zfill(2)}{str(t.minute).zfill(2)}"

class CommandCenter:
    def __init__(self, devid):
        self.devid = devid
        self.rf = RFComm(devid)
        self.rf.add_node(self)
        self.rf.keep_reading()
        self.node_map = {} # id->(num HB, last HB, gps, Num photos, Num events, [Event TS])
        self.images_saved = []
        self.msgids_seen = []
        self.vyom_client = VyomClient()

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
            imf = orig_msg["i_f"]
            ims = orig_msg["i_s"]
            imstr = orig_msg["i_d"]
            evid = orig_msg["e_i"]
            im = image.imstrtoimage(imstr)
            fname = f"/tmp/{ims}_{imf}_{random.randint(1000,2000)}.jpg"
            print(f"Saving image to {fname}")
            im.save(fname)
            self.images_saved.append(fname)
            # im.show()
            # SENDING TO VYOM
            try:
                imf = orig_msg["i_f"]
                file_name_suffix = imf.split("_")[-1].split(".")[0]
                filename = f"{evid}_{file_name_suffix}.jpg"
                image_bytes = image.imstrtobytes(imstr)
                self.vyom_client.on_image_arrive(node_hn=ims, image=image_bytes, filename=filename)
            except Exception as e:
                print(f"Error sending image to vyom client {e}")


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
        gpsloc = ""
        eventtslist = []
        if nodeid not in self.node_map.keys():
            hbcount = 1
        else:
            (hbc, _, gpsloc, _, _, el) = self.node_map[nodeid]
            hbcount = hbc + 1
            eventtslist = el
        self.node_map[nodeid] = (hbcount, hbtime, gpsloc, photos_taken, events_seen, eventtslist)
        # SENDING TO VYOM
        try:
            lat = None
            long = None
            if gpsloc is not None:
                lat, long = gpsloc.split(',')
                lat = float(lat)
                long = float(long)
            self.vyom_client.on_hb_arrive(node_hn=nodeid, lat=lat, long=long)
        except Exception as e:
            print(f"Error sending hb to vyom client {e}")
    
    # A:1205
    def process_event(self, eventstr):
        parts = eventstr.split(':')
        if len(parts) != 3:
            print(f"Error parsing event message : {eventstr}")
            return
        nodeid = parts[0]
        eventtime = parts[1]
        evid = parts[2]
        if nodeid not in self.node_map:
            print(f"Wierd that node {nodeid} not in map yet")
            return
        (hbcount, hbtime, gpsloc, photos_taken, events_seen, event_ts_list) = self.node_map[nodeid]
        event_ts_list.append(eventtime)
        self.node_map[nodeid] = (hbcount, hbtime, gpsloc, photos_taken, events_seen, event_ts_list)
        # SENDING TO VYOM
        try:
            self.vyom_client.on_event_arrive(node_hn=nodeid, event_id=evid)
        except Exception as e:
            print(f"Error sending event to vyom client {e}")

    def process_gps(self, msgstr):
        parts = msgstr.split(':')
        if len(parts) != 2:
            print(f"Error parsing event message : {msgstr}")
            return
        nodeid = parts[0]
        gpsloc = parts[1]
        if nodeid not in self.node_map:
            self.node_map[nodeid] = (0, "", gpsloc, 0, 0, [])
        (hbcount, hbtime, _, photos_taken, events_seen, event_ts_list) = self.node_map[nodeid]
        self.node_map[nodeid] = (hbcount, hbtime, gpsloc, photos_taken, events_seen, event_ts_list)

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
        elif mst == constants.MESSAGE_TYPE_GPS:
            print(f"########## Messsage receive at command center : {mst} : {msgstr}")
            self.process_gps(msgstr)
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
        self.photos_taken = 0
        self.critical_images_processed = []
        self.critical_images_sent = []

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

    def get_images_to_send(self, critical_images):
        cropped = None
        full = None
        for f in critical_images:
            if f not in self.critical_images_processed:
                self.critical_images_processed.append(f)
                if f.find("_c.jpg") >= 0:
                    cropped = f
                fname = f.split("/").pop()
                evid = fname.split("_")[2]
                if f.find(f"{evid}_f.jpg") >= 0:
                    full = f
        return (evid, cropped, full)

    def send_img(self, imgfile, evid):
        next_dest = get_next_dest(self.devid)
        if next_dest == None:
            print(f"{self.devid} Weird no dest for {self.devid}")
            return
        mst = constants.MESSAGE_TYPE_PHOTO
        fname = imgfile.split("/").pop()
        im = {"i_f" : fname,
              "i_s" : self.devid,
              "i_t" : str(int(time.time())),
              "e_i" : evid,
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
        propogation_thread.start()

    def _keep_beating_heart(self):
        self.send_gps()
        while True:
            self.send_heartbeat(self.photos_taken, len(self.critical_images_processed))
            time.sleep(300) # Every 5 mins

    # Non blocking, background thread
    def keep_beating_heart(self):
        hb_thread = threading.Thread(target=self._keep_beating_heart, daemon=True)
        hb_thread.start()

    def keep_sending_to_cc(self):
        self.keep_beating_heart()
        photos_seen = 0
        events_seen = 0
        while True:
            (photos_seen, critical_images) = get_files_in_dir(ALLDIR, CRITICAL_DIR)
            print(f"Taken sofar={self.photos_taken}, now={photos_seen}")
            print(f"Critical sofar={len(self.critical_images_processed)}, now={len(critical_images)}")
            self.photos_taken = photos_seen
            if len(critical_images) > 0:
                (evid, cropped, full) = self.get_images_to_send(critical_images)
                if cropped or full:
                    print(f"{cropped}, {full}")
                    events_seen += 1
                    self.send_event(evid)
                    time.sleep(10)
                if cropped:
                    self.send_img(cropped, evid)
                    time.sleep(60)
                if full:
                    self.send_img(full, evid)
                time.sleep(10)

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
        gpsgetter= gps.Gps()
        loc = gpsgetter.get_lat_lng()
        if loc is not None:
            (lat, lng) = loc
            next_dest = get_next_dest(self.devid)
            msgstr = f"{self.devid}:{lat},{lng}"
            self.rf.send_message(msgstr, constants.MESSAGE_TYPE_GPS, next_dest)

    # A:1205
    # Name, time
    def send_event(self, evid):
        t = get_time_str()
        msgstr = f"{self.devid}:{t}:{evid}"
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
        du.keep_sending_to_cc()
    time.sleep(10000000)

def main():
    run_unit()

if __name__=="__main__":
    main()
