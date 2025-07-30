import sensor
import ml
import time
import random

clock = time.clock()
image_count = 0


MODEL_PATH = "/rom/person_detect.tflite"
model = ml.Model(MODEL_PATH)
print("Model loaded:", model)

IMG_DIR = "/sdcard/images1/"
CONFIDENCE_THRESHOLD = 0.5

sensor.reset()

# RGB565 is required for ml model
# JPEG is for best quality
sensor.set_pixformat(sensor.RGB565)

# HD for 1280x720 res
# SXGA for 1280x720 high quality images
# QVGA for 320x240 (best balance for person detection)
# VGA 640x480 — gives more spatial resolution
# SVGA 800x600 — better for long distance, use only if no memory issues
sensor.set_framesize(sensor.SXGA)

sensor.skip_frames(time=3000)

sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)
sensor.set_auto_exposure(False)



def detect_person(img):
    prediction = model.predict([img])
    scores = zip(model.labels, prediction[0].flatten().tolist())
    scores = sorted(scores, key=lambda x: x[1], reverse=True)  # Highest confidence first
    p_conf = 0.0
    for label, conf in scores:
        if label == "person":
            p_conf = conf
            if conf >= CONFIDENCE_THRESHOLD:
                return (True, p_conf)
    return (False, p_conf)

# def person_detection_loop():
#     global image_count
#     while True:
#         img = sensor.snapshot()
#         time.sleep(1)
#         print(len(img.bytearray()))
#         image_count += 1
#         print(f"Image count: {image_count}")
#         person_detected, confidence = detect_person(img)
#         if person_detected:
#             r = get_rand(6)
#             raw_path = f"{IMG_DIR}raw_{r}_{person_detected}_{confidence:.2f}.jpg"
#             img2 = image.Image(320, 240, image.RGB565, buffer=img.bytearray())
#             print(f"Saving image to {raw_path}")
#             img2.save(raw_path)
#         time.sleep(1)

def person_detection_loop():
    global image_count
    while True:
        try:
            sensor.__write_reg(0x3022, 0x03)
            print("Autofocus triggered")
        except Exception as e:
            print("Autofocus failed:", e)
        img = sensor.snapshot()
        image_count += 1
        print(f"Image count: {image_count}")
        person_detected, confidence = detect_person(img)
        # if person_detected:
        #     r = get_rand(6)
        #     raw_path = f"{IMG_DIR}raw_{r}_{person_detected}_{confidence:.2f}.jpg"
        #     print(f"Saving image to {raw_path}")
        #     img.save(raw_path)  # Save directly without reconstructing

        r = get_rand(6)
        raw_path = f"{IMG_DIR}raw_{r}_{person_detected}_{confidence:.2f}.jpg"
        print(f"Saving image to {raw_path}")
        img.save(raw_path)  # Save directly without reconstructing
        time.sleep(1)


def get_rand(n):
    rstr = ""
    for i in range(n):
        rstr += chr(65+random.randint(0,25))
    return rstr

def get_input_size_expected():
    print(model.input_width())
    print(model.input_height())
    print(model.input_channels())

while True:
    # person_detection_loop()
    get_input_size_expected()


