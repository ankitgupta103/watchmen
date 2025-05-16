import time
import os
from picamera2 import Picamera2, Preview
import device_info

class Camera:
    def __init__(self, dinfo, o_dir="/tmp/camera_captures"):
        self.dinfo = dinfo
        self.output_dir = o_dir
        self.cam = Picamera2()
        self.cam.start()
        time.sleep(2)

    def start(self):
        print(f"Making outout directory {self.output_dir}")
        os.makedirs(self.output_dir, exist_ok=True)

    def take_picture(self):
        ts_ns = time.time_ns()
        fname = f"{self.output_dir}/capture_{self.dinfo.device_id_str}_{ts_ns}.jpg"
        print(f" ==== Will write image to file : {fname}")
        try:
            self.cam.capture_file(fname)
        except Exception as e:
            print("Couldn't take picture")
            print(e)
            return ""
        print(f"... Written image to file : {fname}")
        return fname

def main():
    dinfo = device_info.DeviceInfo("2b46c5c95aea7306")
    cam = Camera(dinfo, o_dir="/tmp/camera_captures_test")
    cam.start()
    cam.take_picture()

if __name__=="__main__":
    main()
