import time
import os
from picamera2 import Picamera2, Preview
import device_info

class Camera:
    def __init__(self, dinfo, o_dir="/tmp/camera_captures"):
        self.dinfo = dinfo
        self.output_dir = o_dir
        self.picam2 = Picamera2()

    def start(self):
        os.makedirs(self.output_dir, exist_ok=True)
        self.picam2.start()

    def take_picture(self):
        ts_ns = time.time_ns()
        fname = f"{self.output_dir}/capture_{self.dinfo.device_id_str}_{ts_ns}.jpg"
        print(f"Will write image to file : {fname}")
        # TODO image is a little zoomed in
        self.picam2.capture_file(fname)
        print(f"... Write image to file : {fname}")
        return fname

def main():
    dinfo = device_info.DeviceInfo("2b46c5c95aea7306")
    cam = Camera(dinfo)
    cam.start()
    cam.take_picture()

if __name__=="__main__":
    main()
