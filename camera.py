import time
import os
from picamera2 import Picamera2, Preview

class Camera:
    def __init__(self, devid, o_dir="/tmp/camera_captures"):
        self.devid = devid
        self.output_dir = o_dir
        self.cam = Picamera2()
        self.cam.start()
        time.sleep(2)

    def start(self):
        print(f"Making outout directory {self.output_dir}")
        os.makedirs(self.output_dir, exist_ok=True)

    def take_picture(self):
        ts_ns = time.time_ns()
        fname = f"{self.output_dir}/capture_{self.devid}_{ts_ns}.jpg"
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
    cam = Camera("dsdsdsrwrdews", o_dir="/tmp/camera_captures_test")
    cam.start()
    cam.take_picture()

if __name__=="__main__":
    main()
