import sensor, image, time, ml

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)  # IR lens sees IR best in grayscale
sensor.set_framesize(sensor.HD)       # Smaller frame for faster detection
# sensor.set_auto_gain(False)             # Turn off AGC for consistent brightness
# sensor.set_auto_whitebal(False)         # Not needed for grayscale
sensor.set_auto_exposure(True)          # Auto exposure if manual not available
sensor.skip_frames(time=2000)

# Load the person detection model
model = ml.Model("/rom/person_detect.tflite")
_, model_h, model_w, _ = model.input_shape[0]
print("Model expects input size:", model_w, "x", model_h)

clock = time.clock()

while True:
    clock.tick()
    img = sensor.snapshot()

    stride = 1  # Smaller stride = more accurate, but slower
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

    if best_box and best_conf > 0.6:  # Lowered threshold for low-light
        x, y, w, h = best_box
        img.draw_rectangle(x, y, w, h, color=255)
        img.draw_string(x, y - 10, "person: {:.2f}".format(best_conf), color=255)
        print("Person detected! Confidence:", best_conf)

    print("FPS:", clock.fps())
