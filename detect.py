import sys
import os
import cv2
from ultralytics import YOLO

YOLOMODELNAME="yolov8n.pt"

testfilename="testhumanforest.jpg"
testdir="/Users/ankitgupta/yolo/testdata/"
#mname="yolo11n.pt"

def has_person(results):
    #print(results)
    for r in results:
        x = r.summary()
        print(f"Box = {r.boxes.xywh}")
        print(f"Box = {r.boxes.xywhn}")
        print(f"Box = {r.boxes.xyxyn}")
        print(f"Box = {r.boxes.xyxy}")
        for o in x:
            print(f"detected object = {o['name']}")
            if o["name"] == "person":
                return True
    return False

def is_image_file(file_path):
    return file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'))

class Detector:
    def __init__(self):
        self.modelname = YOLOMODELNAME
        self.model = YOLO(self.modelname)
        self.model.info()
        self.debug_mode = False

    def set_debug_mode(self):
        self.debug_mode = True

    def ImageHasPerson(self, fname):
        fpath = fname
        image = cv2.imread(fpath)
        resized_image = cv2.resize(image, (640, 640))
        results = self.model(resized_image)
        has_p = has_person(results)
        if (has_p):
            print("Person found in image " + fname)
            if self.debug_mode:
                for r in results:
                    r.show()
        return has_p

def eval_dir(detector, dname):
    filenames = os.listdir(dname)
    image_files = []
    for f in filenames:
        fpath = os.path.join(dname, f)
        if os.path.isfile(fpath) and is_image_file(fpath):
            image_files.append(fpath)
        else:
            print("Not an image file : " + fpath)
    print ("Found %d image files." % len(image_files))
    people_images = []
    for imf in image_files:
        has_p = detector.ImageHasPerson(imf)
        if has_p:
            people_images.append(imf)
    for f in people_images:
        print(f)
    print ("Found people in %d out of %d images." % (len(people_images), len(image_files)))

def main():
    detector = Detector()
    detector.set_debug_mode()
    #detector.ImageHasPerson(sys.argv[1])
    eval_dir(detector, "/Users/ankitgupta/watchmen/src/testdata/t11/")

if __name__=="__main__":
    main()
