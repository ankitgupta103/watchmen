import sensor, image, machine, os, time, random

uart = machine.UART(1, baudrate=57600, timeout_char=1000)
led = machine.LED("LED_RED")

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)

face_cascade = image.HaarCascade("/rom/haarcascade_frontalface.cascade", stages=15)

if "people" not in os.listdir():
    os.mkdir("people")

CHUNK_SIZE = 240

def send_file_over_uart(filepath):
    try:
        with open(filepath, "rb") as f:
            uart.write(b"<START>\n")
            print("[UART] Sending <START>")

            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                uart.write(chunk)
                print(f"[UART] Sent {len(chunk)} bytes")

            uart.write(b"<END>\n")
            print("[UART] Sending <END>")
            return True

    except Exception as e:
        print("[ERROR] UART send failed:", e)
        return False

print("Ready to detect and send image without ACKs...")

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
            send_file_over_uart(filename)
        except Exception as e:
            print("[ERROR] Save/send failed:", e)

        led.off()
        time.sleep(2)
