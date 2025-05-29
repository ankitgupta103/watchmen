import time
import os
import io
import json
import base64
import image
from PIL import Image # Should remove
from picamera2 import Picamera2, Preview

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
    fpath = "/home/ankit/test.jpg"
    image_file = Image.open(fpath)
    fp = f"/home/ankit/test_20.jpg"
    image_file.save(fp, quality=20)
    im = image.image2string(fp)
    print(len(im))
    chunks = []
    while len(im) > 0:
        msg = {"d" : im[0:100]}
        chunks.append(json.dumps(msg).encode())
        im = im[100:]
    print(len(chunks))
    new_img = ""
    for chunk in chunks:
        m = json.loads(chunk.decode().strip())
        cd = m["d"]
        new_img = new_img + cd
    print(len(new_img))
    im2 = image.imstrtoimage(new_img)
    im2.show()
    im2.save("/home/ankit/test_new.jpg")
    
    #cam = Camera("dsdsdsrwrdews", o_dir="/tmp/camera_captures_test")
    #cam.start()
    #(imfile, imstr) = cam.take_picture()

if __name__=="__main__":
    main()
