# Advanced Frame Differencing Example
#
# This example demonstrates using frame differencing with your OpenMV Cam. This
# example is advanced because it preforms a background update to deal with the
# backgound image changing overtime.

import sensor, image, os, time
import ml
import machine

high_threshold = (30, 100)
TRIGGER_THRESHOLD = 35

BG_UPDATE_FRAMES = 50 # How many frames before blending.
BG_UPDATE_BLEND = 128 # How much to blend by... ([0-256]==[0.0-1.0]).
blob_cx_trh=100
sensor.reset() # Initialize the camera sensor.

sensor.set_pixformat(sensor.RGB565) # or sensor.RGB565
sensor.set_framesize(sensor.HD) # or sensor.QQVGA (or others)
sensor.skip_frames(time = 2000) # Let new settings take affect.
sensor.set_auto_whitebal(False) # Turn off white balance.
clock = time.clock() # Tracks FPS.

# Take from the main frame buffer's RAM to allocate a second frame buffer.
# There's a lot more RAM in the frame buffer than in the MicroPython heap.
# However, after doing this you have a lot less RAM for some algorithms...
# So, be aware that it's a lot easier to get out of RAM issues now. However,
# frame differencing doesn't use a lot of the extra space in the frame buffer.
# But, things like AprilTags do and won't work if you do this...
extra_fb = sensor.alloc_extra_fb(sensor.width(), sensor.height(), sensor.RGB565)

print("About to save background image...")
sensor.skip_frames(time = 2000) # Give the user time to get ready.
extra_fb.replace(sensor.snapshot())
print("Saved background image - Now frame differencing!")

triggered = False

MODEL_PATH = "/rom/person_detect.tflite"
model = ml.Model(MODEL_PATH)
print(" Model loaded:", model)
CONFIDENCE_THRESHOLD = 0.5

led = machine.LED("LED_RED")

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

frame_count = 0
while(True):
    clock.tick() # Track elapsed milliseconds between snapshots().
    img = sensor.snapshot() # Take a picture and return the image.

    frame_count += 1
    if (frame_count > BG_UPDATE_FRAMES):
        frame_count = 0
    
        # Blend in new frame. We're doing 256-alpha here because we want to
        # blend the new frame into the backgound. Not the background into the
        # new frame which would be just alpha. Blend replaces each pixel by
        # ((NEW*(alpha))+(OLD*(256-alpha)))/256. So, a low alpha results in
        # low blending of the new image while a high alpha results in high
        # blending of the new image. We need to reverse that for this update.
    
        img.blend(extra_fb, alpha=(256-BG_UPDATE_BLEND))
        extra_fb.replace(img)

    # Replace the image with the "abs(NEW-OLD)" frame difference.
    imorig = img
    img.difference(extra_fb)

    hist = img.get_histogram()
    
    # This code below works by comparing the 99th percentile value (e.g. the
    # non-outlier max value against the 90th percentile value (e.g. a non-max
    # value. The difference between the two values will grow as the difference
    # image seems more pixels change.
    
    diff = hist.get_percentile(0.99).l_value() - hist.get_percentile(0.90).l_value()
    print(hist.get_percentile(0.99).l_value())
    print(hist.get_percentile(0.90).l_value())
    detected, conf = detect_person(img)
    print(f"Motion = {diff}, person conf = {conf}")
    isperson = diff > 25 and conf > 0.25
    fname = f"/sdcard/person_{frame_count}_{isperson}_{diff}_{int(conf*100)}.jpg"
    print(fname)
    imorig.save(fname)
    led.on()
    sensor.skip_frames(time = 2000)
    led.off()
    sensor.skip_frames(time = 2000)
