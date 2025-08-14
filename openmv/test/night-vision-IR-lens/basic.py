# import sensor, image, time

# sensor.reset()
# sensor.set_pixformat(sensor.GRAYSCALE)  # IR camera = no need for RGB
# sensor.set_framesize(sensor.HD)
# sensor.set_auto_gain(False)             # Turn off AGC
# sensor.set_auto_whitebal(False)         # Turn off AWB
# sensor.set_auto_exposure(True)          # Use automatic exposure
# sensor.set_gainceiling(128)              # Increase gain ceiling (1, 2, 4, 8, 16, 32, 64, 128)
# sensor.skip_frames(time=2000)

# clock = time.clock()

# while True:
#     clock.tick()
#     img = sensor.snapshot()
#     print(clock.fps())


import sensor, image, time, ml

# Initialize camera
sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)  # Better for IR lens
sensor.set_framesize(sensor.HD)         # Higher resolution for better detection
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)
sensor.set_auto_exposure(True)
sensor.set_gainceiling(8)
sensor.skip_frames(time=2000)

# Load the person detection model
model = ml.Model("/rom/person_detect.tflite")
_, model_h, model_w, _ = model.input_shape[0]
print("Model expects input size:", model_w, "x", model_h)

clock = time.clock()

while True:
    clock.tick()
    img = sensor.snapshot()

    # Optional: convert to RGB if needed by model
    if img.format() != image.RGB565:
        img = img.to_rgb565()

    stride = 20  # Slide the window across the image
    best_conf = 0
    best_box = None

    for y in range(0, img.height() - model_h + 1, stride):
        for x in range(0, img.width() - model_w + 1, stride):
            tile = img.copy(roi=(x, y, model_w, model_h))
            result = model.predict([tile])[0].flatten().tolist()
            label, confidence = sorted(zip(model.labels, result), key=lambda x: x[1], reverse=True)[0]

            if label == "person" and confidence > best_conf:
                best_conf = confidence
                best_box = (x, y, model_w, model_h)

    # Draw best detection
    if best_box and best_conf > 0.7:
        x, y, w, h = best_box
        img.draw_rectangle(x, y, w, h, color=(255, 0, 0), thickness=2)
        img.draw_string(x, y - 10, "person: {:.2f}".format(best_conf), color=(255, 0, 0))
        print("Person detected! Confidence:", best_conf)

    print("FPS:", clock.fps())
