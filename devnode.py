import time
import threading
import os
import communicator
import detect
import camera
import constants
import device_info

def get_device_id_str():
    file = open(constants.RPI_SERIAL_FILENAME, "r")
    content = file.read()
    serial_id_str = content.rstrip().lstrip().rstrip(os.linesep)[:-1] # TODO last char still remains @!!!!@#E@$@$@
    if len(serial_id_str) != 16:
        print(f"Incorrect serial ID : {content} in {constants.RPI_SERIAL_FILENAME}")
        quit(-1)
    return serial_id_str

class DevNode:
    def __init__(
            self,
            dinfo,
            comm,
            p_detector,
            check_freq_sec=10,
            hb_freq_sec=30):
        self.dinfo = dinfo
        self.comm = comm
        self.cam = camera.Camera(self.dinfo)
        self.cam.start()
        self.p_detector = p_detector
        self.p_detector.set_debug_mode()
        self.check_freq_sec = check_freq_sec
        self.hb_freq_sec = hb_freq_sec
        # TODO Topology, or should this go in device info
        # self.neighbourhood = None
        # self.min_hops_from_command_central = -1

    def is_registered(self):
        return self.network_id > 0

    def register_myself(self):
        print (f"Registered device with ID {self.dinfo.device_id} at location {self.dinfo.gps}")
        self.comm.register(self.dinfo)
        # TODO Handle callback to complete registration

    def check_human(self):
        fname = self.cam.take_picture()
        if fname == "":
            print("No picture available")
            return
        p_found = self.p_detector.ImageHasPerson(fname)
        if p_found:
            print(f"####### Human found ######")
            print(f"Check file {fname} ")
            # Notify Network
        else:
            print("No human detected.")

    def keep_checking_human(self):
        while True:
            ts = time.time()
            print(f"Checked at time --- {ts}")
            self.check_human()
            time.sleep(self.check_freq_sec)

    def send_heartbeat(self, ts):
        self.neighbourhood = self.comm.send_heartbeat(ts)

    def keep_sending_heartbeat(self):
        while True:
            ts = time.time()
            print(f"Sending heartbeat at {ts}")
            self.send_heartbeat(ts)
            time.sleep(self.hb_freq_sec)

def main():
    device_id_str = get_device_id_str()
    p_detector = detect.Detector()
    dinfo = device_info.DeviceInfo(device_id_str)
    comm = communicator.Communicator()
    devnode = DevNode(dinfo, comm, p_detector)
    #devnode.register_myself()
    thread_cam = threading.Thread(target=devnode.keep_checking_human)
    thread_heartbeat = threading.Thread(target=devnode.keep_sending_heartbeat)
    
    thread_cam.start()
    time.sleep(3)
    thread_heartbeat.start()

    thread_cam.join()
    thread_heartbeat.join()

if __name__=="__main__":
    main()
