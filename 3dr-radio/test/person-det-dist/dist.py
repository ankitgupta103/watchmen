import sensor 
import ml

clock = time.clock()
image_count = 0


clock_start = utime.ticks_ms()
MODEL_PATH = "/rom/person_detect.tflite"
model = ml.Model(MODEL_PATH)
print("Model loaded:", model)

IMG_DIR = "/sdcard/images/"
CONFIDENCE_THRESHOLD = 0.5

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.HD)
sensor.skip_frames(time=2000)