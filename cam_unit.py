import time
import communicator

LOCATION_HOME = "28.4241,77.0358"
LOCATION_SPAZE = "28.4203,77.0402"
LOCATION_CLUB = "28.4264,77.0335"
LOCATIONS = [LOCATION_HOME, LOCATION_SPAZE, LOCATION_CLUB]
DEVICE_CAM = "DEVICE_CAM"

def parse_latlong(locstr):
    parts = locstr.split(",")
    if len(parts) != 2:
        print("ERROR Parsing latlong : " + locstr)
        quit()
    lat = float(parts[0])
    lng = float(parts[1])
    print ("initializing as %f,%f" % (lat,lng))
    return (lat, lng)

class CamUnit:
    def __init__(self, comm):
        self.network_id = -1
        self.device_id = ""
        self.lat = 0.0
        self.lng = 0.0
        self.neighbourhood = None
        self.min_hops_from_command_central = -1
        self.comm = comm

    def is_registered(self):
        return self.network_id > 0

    def registerMyself(self):
        (self.lat, self.lng) = parse_latlong(LOCATION_HOME)
        # TODO Make this asynchronous.
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
    comm = communicator.Communicator(DEVICE_CAM, "xyz")
    unit = CamUnit(comm)
    unit.registerMyself()
    unit.send_heartbeat()

if __name__=="__main__":
    main()
