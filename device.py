import time
import constants

from detect import Detector
from camera import Camera

class Device:
    def __init__(self, devid, fcomm):
        self.devid = devid
        self.neighbours_seen = []
        self.spath = []
        self.fcomm = fcomm
        self.cam = None
        if self.devid == "AAA":
            self.cam = Camera(devid, o_dir="/tmp/camera_captures_test")
            self.cam.start()
            self.detector = Detector()
        self.image_count = 0
        self.event_count = 0

    def send_scan(self, ts):
        scan_msg = {
                "message_type" : constants.MESSAGE_TYPE_SCAN,
                "source" : self.devid,
                "last_sender" : self.devid,
                "ts" : ts,
                }
        # Failure Here is OK, since it is a discovery and alternative paths would be discovered.
        self.fcomm.send_to_network(scan_msg, self.devid)

    def send_hb(self, ts):
        if self.spath == None or len(self.spath) < 2 or self.spath[0] != self.devid:
            return
        dest = self.spath[1]
        hb_msg = {
                "message_type" : constants.MESSAGE_TYPE_HEARTBEAT,
                "source" : self.devid,
                "source_ts" : ts,
                # Payload
                "neighbours" : self.neighbours_seen,
                "image_count" : self.image_count,
                "event_count" : self.event_count,
                # Routing info
                "shortest_path" : self.spath,
                "dest" : dest,
                "path_so_far" : [self.devid, dest],
                "last_sender" : self.devid,
                "last_ts" : ts
                }
        self.fcomm.send_to_network(hb_msg, self.devid, dest)

    def send_image(self, ts, image_data, image_ts):
        # TODO this will need to be stored until we have spath
        if self.spath == None or len(self.spath) < 2 or self.spath[0] != self.devid:
            return
        dest = self.spath[1]
        hb_msg = {
                "message_type" : constants.MESSAGE_TYPE_PHOTO,
                "source" : self.devid,
                "source_ts" : ts,
                # Payload
                "image_data" : image_data,
                "image_ts" : image_ts,
                # Routing info
                "shortest_path" : self.spath,
                "dest" : dest,
                "path_so_far" : [self.devid, dest],
                "last_sender" : self.devid,
                "last_ts" : ts
                }
        self.fcomm.send_to_network(hb_msg, self.devid, dest)

    def propogate_spath(self, msg):
        source = msg["source"]
        dest = msg["dest"]
        source_ts = msg["source_ts"]
        spath1 = msg["shortest_path"]
        if len(self.spath) == 0 or len(spath1) < len(self.spath):
            if self.devid == "AAA":
                print(f" ********* {self.devid} : Updating spath from {self.spath} to {spath1[::-1]}")
            self.spath = spath1[::-1]

            for neighbour in self.neighbours_seen:
                if neighbour in spath1:
                    continue
                new_msg = msg
                new_msg["dest"] = neighbour
                msg["shortest_path"] = spath1 + [neighbour]
                new_msg["last_sender"] = self.devid
                new_msg["network_ts"] = time.time_ns()
                # Failure Here is OK, since it is a discovery and alternative paths would be discovered.
                self.fcomm.send_to_network(new_msg, self.devid, neighbour)

    def get_route(self, msg):
        dest = msg["dest"]
        msg_spath = msg["shortest_path"]
        path_so_far = msg["path_so_far"]
        if len(path_so_far) >= len(msg_spath):
            #print(f"Finished")
            return None
        if dest != self.devid:
            print(f"Weird that {dest} is not {self.devid:}")
            return None
        new_dest = msg_spath[len(path_so_far)] # Get the next item
        new_path_so_far = path_so_far + [new_dest]
        return (new_dest, new_path_so_far)

    def propogate_hb(self, msg):
        #msg_spath = msg["shortest_path"]
        #path_so_far = msg["path_so_far"]
        #if len(msg_spath) == 0:
        #    msg_spath = path_so_far + self.spath[1:]
        #    print(f"{self.devid} : Likely reroute : updating msg_path to {msg_spath}")
        
        new_route = self.get_route(msg)
        if new_route is None:
            return
        (new_dest, new_path_so_far) = new_route

        new_msg = msg
        new_msg["dest"] = new_dest
        msg["path_so_far"] = new_path_so_far
        new_msg["last_sender"] = self.devid
        new_msg["last_ts"] = time.time_ns()
        succ = self.fcomm.send_to_network(new_msg, self.devid, new_dest)
        #if not succ:
        #    print(f"{self.devid} Sending failed to {new_dest}, trying other neighbours : {self.neighbours_seen}")
        #    avoidlist = new_path_so_far # Avoid everything the message has been on.
        #    for n in self.neighbours_seen:
        #        if n in avoidlist:
        #            continue
        #        print(f"{self.devid} sending HB to {new_dest} failed, trying to send to {n}, avoiding {avoidlist}")
        #        new_msg["dest"] = n
        #        msg["path_so_far"] = path_so_far + [n]
        #        if n not in avoidlist:
        #            avoidlist.append(n)
        #        msg['msg_spath'] = []
        #        new_msg["last_sender"] = self.devid
        #        new_msg["last_ts"] = time.time_ns()
        #        succ = self.fcomm.send_to_network(new_msg, self.devid, new_dest)
        #        if succ:
        #            print(f"{self.devid} : Successfully sent to {n}")
        #            break

    def propogate_image(self, msg):
        new_route = self.get_route(msg)
        if new_route is None:
            return
        
        (new_dest, new_path_so_far) = new_route
        print(f" ==== SENDING IMAGE FROM {self.devid} to {new_dest}")
        new_msg = msg
        new_msg["dest"] = new_dest
        msg["path_so_far"] = new_path_so_far
        new_msg["last_sender"] = self.devid
        new_msg["last_ts"] = time.time_ns()
        self.fcomm.send_to_network(new_msg, self.devid, new_dest)

    def process_msg(self, msg):
        mtype = msg["message_type"]
        if mtype == constants.MESSAGE_TYPE_SCAN:
            source = msg["source"]
            if source not in self.neighbours_seen:
                self.neighbours_seen.append(source)
        if mtype == constants.MESSAGE_TYPE_HEARTBEAT:
            self.propogate_hb(msg)
        if mtype == constants.MESSAGE_TYPE_SPATH:
            self.propogate_spath(msg)
        if mtype == constants.MESSAGE_TYPE_PHOTO:
            self.propogate_image(msg)

    def check_event(self):
        if self.cam is None:
            return
        image_ts = time.time_ns()
        (imfile, imdatastr) = self.cam.take_picture()
        self.image_count = self.image_count + 1
        event_found = self.detector.ImageHasPerson(imfile)
        if event_found:
            print(f"###### {self.devid} saw an event, photo at {imfile} ######")
            self.send_image(time.time_ns(), imdatastr, image_ts)
            self.event_count = self.event_count + 1
