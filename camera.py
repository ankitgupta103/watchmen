import time
import os
import io
import base64
from PIL import Image
from picamera2 import Picamera2, Preview

def image2string(imagefile):
    r""" Convert Pillow image to string. """
    image = Image.open(imagefile)
    # image.show()
    image = image.convert('RGB')
    img_bytes_arr = io.BytesIO()
    image.save(img_bytes_arr, format="JPEG")
    img_bytes_arr.seek(0)
    img_bytes_arr = img_bytes_arr.read()
    img_bytes_arr_encoded = base64.b64encode(img_bytes_arr)
    res = img_bytes_arr_encoded.decode('utf-8')
    return res

class Camera:
    def __init__(self, devid, o_dir="/tmp/camera_captures"):
        self.devid = devid
        self.output_dir = o_dir
        self.cam = Picamera2()

        #preview_config = self.cam.create_preview_configuration(main={"size": (800, 600)})
        #self.cam.configure(preview_config)
        #self.cam.start_preview(Preview.QTGL)
        self.capture_config = self.cam.create_still_configuration()

        self.cam.start()
        time.sleep(2)

    def start(self):
        print(f"Making outout directory {self.output_dir}")
        os.makedirs(self.output_dir, exist_ok=True)

    def take_picture(self):
        ts_ns = time.time_ns()
        fname = f"{self.output_dir}/capture_{self.devid}_{ts_ns}.jpg"
        try:
            # self.cam.switch_mode_and_capture_file(self.capture_config, fname)
            self.cam.capture_file(fname)
        except Exception as e:
            print("Couldn't take picture")
            print(e)
            return ("", "")
        print(f"... Written image to file : {fname}")
        imstr = image2string(fname)
        return (fname, imstr)

def main():
    cam = Camera("dsdsdsrwrdews", o_dir="/tmp/camera_captures_test")
    cam.start()
    (imfile, imstr) = cam.take_picture()

if __name__=="__main__":
    main()
