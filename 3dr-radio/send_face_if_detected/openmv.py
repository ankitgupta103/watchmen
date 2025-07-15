import sensor, image, machine, os, time, random, ubinascii

# UART setup
uart = machine.UART(1, baudrate=56700, timeout_char=1000)
led = machine.LED("LED_RED")

# Camera setup
sensor.reset()
sensor.set_pixformat(sensor.RGB565)  # High-quality color
sensor.set_framesize(sensor.QVGA)    # 320x240
sensor.skip_frames(time=2000)

# Load face cascade
face_cascade = image.HaarCascade("/rom/haarcascade_frontalface.cascade", stages=15)

# Ensure folder exists
if "people" not in os.listdir():
    os.mkdir("people")

def send_image_base64(filepath):
    try:
        with open(filepath, "rb") as f:
            uart.write(b"<START>\n")
            print("[UART] Sent <START>")
            while True:
                chunk = f.read(64)
                if not chunk:
                    break
                b64 = ubinascii.b2a_base64(chunk)
                uart.write(b64)  # already ends with \n
                time.sleep_ms(10)  # prevent buffer overrun
            uart.write(b"<END>\n")
            print("[UART] Sent <END>")
    except Exception as e:
        print("[ERROR]", e)

print("Ready to detect and send high-quality images...")

while True:
    img = sensor.snapshot()
    faces = img.find_features(face_cascade, threshold=0.5, scale_factor=1.5)

    if faces:
        print("[INFO] Face detected.")
        led.on()

        filename = "people/person_%d.jpg" % random.getrandbits(16)
        try:
            img.save(filename, quality=90)
            print("[INFO] Image saved:", filename)
            send_image_base64(filename)
        except Exception as e:
            print("[ERROR] Save/send failed:", e)

        led.off()
        time.sleep(2)

    # For seding image snapshots without detection:

    # filename = "people/person_%d.jpg" % random.getrandbits(16)
    # try:
    #    img.save(filename, quality=100)
    #    print("[INFO] Image saved:", filename)
    #    send_image_base64(filename)
    # except Exception as e:
    #    print("[ERROR] Save/send failed:", e)

    # led.off()
    # time.sleep(2)
