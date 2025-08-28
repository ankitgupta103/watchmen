from machine import Pin
import time
import ml
import sensor
import image

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

# ====== TURNING IR EMITTER ON ========================
p1_pin = Pin('P14', Pin.OUT)  # Configure as output
def turn_ON_IR_emitter():
    p1_pin.on()                  # Make it HIGH
    # or
    # p1_pin.value(1)             # Alternative way to make it HIGH
def turn_OFF_IR_emitter():
    p1_pin.value(0)
turn_ON_IR_emitter()
# ======================================================

# Initialize PIR sensor pin (adjust pin number based on your wiring)
# Connect PIR sensor output to a digital pin
PIR_PIN = Pin('P13', Pin.IN, Pin.PULL_DOWN)  # Adjust pin as needed

MODEL_PATH = "/sdcard/custom_person_det.tflite"
MODEL_INPUT_SIZE = 256

class Detector:
    def __init__(self):
        self.model = ml.Model(MODEL_PATH)

    def check_thermal_body(self):
        """Check if thermal body is present in PIR sensor path"""
        is_thermal = PIR_PIN.value()
        if is_thermal:
            print(f"PIR DETECTED THERMAL BODY")
            return True
        else:
            return False

    def resize_image(self, img, target_size):
        w = img.width()
        h = img.height()
        if w > h:
            scale_factor = target_size / h
        else:
            scale_factor = target_size / w
        print(f"Scale factor : {scale_factor}, target size = {target_size}, {h}, {w}")
        # img = img.scale(x_scale=scale_factor, y_scale=scale_factor, hint=image.BICUBIC)
        x_offset = (img.width() - target_size) // 2
        y_offset = (img.height() - target_size) // 2
        # img = img.crop(roi=(x_offset, y_offset, target_size, target_size))
        return img
        # --- Run Inference ---

    def check_image(self):
        img = sensor.snapshot()
        # img = resize_image(img, MODEL_INPUT_SIZE)
        prediction_output = self.model.predict([img])

        # The model returns a list containing one main tensor.
        if isinstance(prediction_output, list) and len(prediction_output) > 0:
            # The tensor shape is (1, 5, 1344). We access the first (and only) item.
            tensor = prediction_output[0]

            # The confidence scores are the first row of the main data block.
            confidence_scores = tensor[0][4]

            # The highest value in this list is our max confidence for a person.
            max_confidence = max(confidence_scores)
            if max_confidence > 0.5:
                print(f"Image detection with confidence {max_confidence}")
                return True
        else:
            # If the output format is unexpected, return 0.
            print(f"  ⚠️ Unexpected model output")
        return False

    def check_person(self):
        return self.check_thermal_body() or self.check_image()

def main():
    d = Detector()
    for i in range(100):
        time.sleep_ms(500)
        person_detected = d.check_person()
        print(f"Person detected = {person_detected}")

if __name__ == "__main__":
    main()
