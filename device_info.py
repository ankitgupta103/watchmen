import time
import constants

LOCATION_HOME = (28.4241,77.0358)
LOCATION_SPAZE = (28.4203,77.0402)
LOCATION_CLUB = (28.4264,77.0335)

def hardcoded_gps(device_id_str):
    print("Here1")
    if device_id_str == "9eccfdf8c851a5ef":
        return LOCATION_HOME
    if device_id_str == "2b46c5c95aea7306":
        return LOCATION_CLUB

# Basically a struct
class DeviceInfo:
    def __init__(self, device_id_str):
        self.device_type = constants.DEVICE_TYPE_CAM
        self.device_id = -1 # Network ID, will be available later
        self.device_id_str = device_id_str # Always available.
        self.gps = hardcoded_gps(device_id_str)
        time_at_start_secs = 0 # Time when it came up.
        print(f"Initializing device with id={self.device_id_str}, at location {self.gps}")

