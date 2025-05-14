import time
import communicator

import constants

LOCATION_HOME = (28.4241,77.0358)
LOCATION_SPAZE = (28.4203,77.0402)
LOCATION_CLUB = (28.4264,77.0335)
LOCATIONS = [LOCATION_HOME, LOCATION_SPAZE, LOCATION_CLUB]
DEVICE_CAM = "DEVICE_CAM"

def get_device_id_str():
    file = open(constants.RPI_SERIAL_FILENAME, "r")
    content = file.read()
    serial_id_str = content.rstrip()
    if len(serial_id_str) < 10 or len(serial_id_str) > 20:
        print(f"Incorrect serial ID : {content} in {constants.RPI_SERIAL_FILENAME}")
        quit(-1)
    print(f"device_id_str = {serial_id_str}")
    return serial_id_str

class CamUnit:
    def __init__(self, comm, device_id_str):
        self.network_id = -1
        self.device_id = device_id_str
        self.latlng = LOCATION_HOME
        self.neighbourhood = None
        self.min_hops_from_command_central = -1
        self.comm = comm

    def is_registered(self):
        return self.network_id > 0

    def register_myself(self):
        (self.network_id, self.neighbourhood) = self.comm.register_unit(self.lat, self.lng)
        print ("Registered device with ID %d at location %s,%s" % (self.network_id, self.lat, self.lng))
        print ("It's neighbourhood looks like : %s" % self.neighbourhood)

    def get_picture(self):
        pass

    def send_heartbeat(self):
        ts = time.time()
        self.neighbourhood = self.comm.send_heartbeat(ts)
        pass

def main():
    get_device_id_str()
    comm = communicator.Communicator(DEVICE_CAM, get_device_id_str())
    unit = CamUnit(comm)
    unit.register_myself()
    # TODO wait for response asynchronously
    unit.send_heartbeat()

if __name__=="__main__":
    main()
