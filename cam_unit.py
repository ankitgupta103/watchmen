import time
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

class CamUnit:
    def __init__(self, dinfo, comm, p_detector):
        self.dinfo = dinfo
        self.comm = comm
        self.cam = camera.Camera(self.dinfo)
        self.p_detector = p_detector
        self.p_detector.set_debug_mode()
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
        p_found = self.p_detector.ImageHasPerson(fname)
        if p_found:
            print(f"####### Human found ######")
            print(f"Check file {fname} ")
            # Notify Network

    def send_heartbeat(self):
        ts = time.time()
        self.neighbourhood = self.comm.send_heartbeat(ts)

def main():
    device_id_str = get_device_id_str()
    p_detector = detect.Detector()
    dinfo = device_info.DeviceInfo(device_id_str)
    comm = communicator.Communicator()
    unit = CamUnit(dinfo, comm, p_detector)
    unit.register_myself()
    for i in range(10):
        print(f"Checked at time --- {i}")
        unit.check_human()
        time.sleep(10)
        
    # TODO wait for response asynchronously
    unit.send_heartbeat()

if __name__=="__main__":
    main()
