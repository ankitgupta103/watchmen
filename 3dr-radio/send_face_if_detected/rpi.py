import serial
import base64

PORT = "/dev/ttyUSB0"  # Change to the correct port
BAUD = 56700

ser = serial.Serial(PORT, BAUD, timeout=1)
image_count = 1

print("Receiver started. Waiting for image...")

while True:
    # Wait for <START>
    while True:
        line = ser.readline()
        if b"<START>" in line:
            print("Start of image detected.")
            break

    filename = f"test_image_{image_count}.jpg"
    with open(filename, "wb") as f:
        while True:
            line = ser.readline()
            if not line:
                continue
            if b"<END>" in line:
                print("End of image detected.")
                break
            try:
                decoded = base64.b64decode(line.strip())
                f.write(decoded)
            except Exception as e:
                print("[ERROR] Base64 decode failed:", e)

    print(f"Image saved as {filename}\n")
    image_count += 1
