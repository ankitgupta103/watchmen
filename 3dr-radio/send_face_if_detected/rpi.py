import serial

PORT = "/dev/ttyUSB0"  # Adjust to your 3DR USB port
BAUD = 57600
CHUNK_SIZE = 240

ser = serial.Serial(PORT, BAUD, timeout=1)
image_count = 1

print("Receiver started. Waiting for image...")

while True:
    # Wait for <START>
    while True:
        line = ser.readline()
        if b"<START>" in line:
            print("Image start detected.")
            break

    filename = f"image_{image_count}.jpg"
    with open(filename, "wb") as f:
        buffer = b""
        while True:
            byte = ser.read(1)
            if not byte:
                continue

            buffer += byte

            # Check if <END> marker is received
            if b"<END>" in buffer:
                end_index = buffer.find(b"<END>")
                f.write(buffer[:end_index])  # Write only up to <END>
                print("Image end detected.")
                break

            # Write data in chunks or flush as needed
            if len(buffer) >= CHUNK_SIZE:
                f.write(buffer[:CHUNK_SIZE])
                buffer = buffer[CHUNK_SIZE:]

    print(f"Image saved as {filename}\n")
    image_count += 1
