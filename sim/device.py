import json
import time
import constants

class Device:
    def __init__(self, devid, fcomm, ncomm):
        self.devid = devid
        self.neighbours_seen = []
        self.spath = []
        self.fcomm = fcomm
        self.ncomm = ncomm
        if fcomm is None and ncomm is None:
            print("At least one communicator")
            return None
        if fcomm is not None and ncomm is not None:
            print("At most one communicator")
            return None
        self.cam = None
        self.detector = None
        self.image_count = 0
        self.event_count = 0

    def send_message(self, msg, dest=None):
        if self.fcomm is not None:
            return self.fcomm.send_to_network(msg, self.devid, dest)
        if self.ncomm is not None:
            msgstr = json.dumps(msg)
            return self.ncomm.send_message(msgstr, dest)

    def get_next_on_spath(self):
        if len(self.spath) <= 1 or self.spath[0] != self.devid:
            print(f"{self.devid} : No next path yet")
            return None
        return self.spath[1]

    def send_scan(self, ts):
        scan_msg = {
                constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_SCAN,
                constants.JK_SOURCE : self.devid,
                constants.JK_LAST_SENDER : self.devid,
                constants.JK_SOURCE_TIMESTAMP : ts,
                }
        # Failure Here is OK, since it is a discovery and alternative paths would be discovered.
        self.send_message(scan_msg)

    def make_hb_msg(self, ts):
        if self.spath == None or len(self.spath) < 2 or self.spath[0] != self.devid:
            print(f"{self.devid} : Spath is not adequate {self.spath}")
            return None
        hb_msg = {
                constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_HEARTBEAT,
                constants.JK_SOURCE : self.devid,
                constants.JK_SOURCE_TIMESTAMP : ts,
                # Payload
                constants.JK_NEIGHBOURS : self.neighbours_seen,
                constants.JK_IMAGE_COUNT : self.image_count,
                constants.JK_EVENT_COUNT : self.event_count,
                constants.JK_SHORTEST_PATH : self.spath,
                # Routing info
                constants.JK_DEST : None, # Will get rerouted
                constants.JK_PATH_SO_FAR : [],
                constants.JK_LAST_TS : ts
                }
        return hb_msg

    def make_image_msg(self, ts, image_data, image_ts):
        # TODO this will need to be stored until we have spath
        if self.spath == None or len(self.spath) < 2 or self.spath[0] != self.devid:
            return None
        image_msg = {
                constants.JK_MESSAGE_TYPE : constants.MESSAGE_TYPE_PHOTO,
                constants.JK_SOURCE : self.devid,
                constants.JK_SOURCE_TIMESTAMP : ts,
                # Payload
                constants.JK_IMAGE_DATA : image_data,
                constants.JK_IMAGE_TS : image_ts,
                # Routing info
                constants.JK_DEST : None, # Will get rerouted
                constants.JK_PATH_SO_FAR : [],
                constants.JK_LAST_TS : ts
                }
        return image_msg

    def spread_spath(self, msg):
        source = msg[constants.JK_SOURCE]
        dest = msg[constants.JK_DEST]
        source_ts = msg[constants.JK_SOURCE_TIMESTAMP]
        spath1 = msg[constants.JK_SHORTEST_PATH]
        if len(self.spath) == 0 or len(spath1) < len(self.spath):
            print(f" ********* {self.devid} : Updating spath from {self.spath} to {spath1[::-1]}")
            self.spath = spath1[::-1]

            for neighbour in self.neighbours_seen:
                if neighbour in spath1:
                    continue
                new_msg = msg
                new_msg[constants.JK_DEST] = neighbour
                msg[constants.JK_SHORTEST_PATH] = spath1 + [neighbour]
                # Failure Here is OK, since it is a discovery and alternative paths would be discovered.
                self.send_message(new_msg, neighbour)

    def get_next_dest(self, msg):
        path_so_far = msg[constants.JK_PATH_SO_FAR]
        new_dest = self.get_next_on_spath()
        if new_dest in path_so_far:
            print(f"{self.devid} : new_dest : {new_dest} is in {path_so_far}")
            return None
        return new_dest
    
    def propogate_msg_to_next(self, msg, new_dest):
        new_msg = msg
        new_msg[constants.JK_DEST] = new_dest
        msg[constants.JK_PATH_SO_FAR] = msg[constants.JK_PATH_SO_FAR] + [self.devid]
        new_msg[constants.JK_LAST_TS] = time.time_ns()
        succ = self.send_message(new_msg, new_dest)
        return succ

    def propogate_message(self, msg):
        new_dest = self.get_next_dest(msg)
        sent = False
        if new_dest is not None:
            sent = self.propogate_msg_to_next(msg, new_dest)
        path_so_far = msg[constants.JK_PATH_SO_FAR]
        if not sent:
            print(f"{self.devid} : Failed to send to {new_dest} : Trying to find alternative route : path_so_far {path_so_far}")
            for n in self.neighbours_seen:
                if n in path_so_far or n == new_dest:
                    continue
                new_dest = n
                sent = self.propogate_msg_to_next(msg, new_dest)
                if sent:
                    print(f"{self.devid} : Finally succeeded to deliver to {new_dest}, path_so_far : {path_so_far}")
                    break

    def send_hb(self, ts):
        msg = self.make_hb_msg(ts)
        if msg is not None:
            self.propogate_message(msg)

    def send_image(self, ts, imdatastr, image_ts):
        msg = self.make_image_msg(ts, imdatastr, image_ts)
        if msg is not None:
            self.propogate_message(msg)

    def process_msg(self, msg):
        mtype = msg[constants.JK_MESSAGE_TYPE]
        if mtype == constants.MESSAGE_TYPE_SCAN:
            source = msg[constants.JK_SOURCE]
            if source not in self.neighbours_seen:
                self.neighbours_seen.append(source)
        if mtype == constants.MESSAGE_TYPE_SPATH:
            self.spread_spath(msg)
        # Passthrough routing
        if mtype == constants.MESSAGE_TYPE_HEARTBEAT:
            self.propogate_message(msg)
        if mtype == constants.MESSAGE_TYPE_PHOTO:
            self.propogate_message(msg)

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
