import time
import image
import json
import socket
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
            fname = f"/tmp/recompiled_{random.randint(1000,2000)}.jpg"
            print(f"Saving image to {fname}")
            im.save(fname)
            im.show()
    except:
        print(f"Error loadig json {msgstr}")

class DevUnit:
    def __init__(self, devid):
        self.devid = devid
        self.rf = RFComm(devid)
        self.rf.add_node(self)
        self.rf.keep_reading()

    def process_message(self, mst, msgstr):
        if is_node_passthrough(self.devid):
            next_dest = get_next_dest(self.devid)
            if next_dest == None:
                print(f"{self.devid} Weird no dest for {self.devid}")
                return
            self.rf.send_message(msgstr, mst, next_dest)
        if is_node_src(self.devid):
            print(f"{self.devid}: Src should not be getting any messages")
        if is_node_dest(self.devid):
            print(f"########## Messsage receive at command center : {msgstr}")
            save_image(msgstr)

    def send_img(self):
        imgfile = "pencil.jpg"
        next_dest = get_next_dest(self.devid)
        if next_dest == None:
            print(f"{self.devid} Weird no dest for {self.devid}")
            return
        mst = constants.MESSAGE_TYPE_PHOTO
        im = {"i_m" : "Image metadata",
              "i_d" : image.image2string(imgfile)}
        msgstr = json.dumps(im)
        self.rf.send_message(msgstr, mst, next_dest)

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
