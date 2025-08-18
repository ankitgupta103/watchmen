# main_camera_cellular.py
# Main script for device e076465dd7194025 (machine_id: 222)
# Captures and uploads images every 30 seconds via cellular

import sensor
import image
import time
import ubinascii
import gc
import machine
import binascii
import sys
import enc

# Import the cellular driver module
from cellular_driver import ProductionBulkCellular

# Constants
MACHINE_ID = 222  # For device e076465dd7194025
IMAGE_CAPTURE_INTERVAL = 30  # seconds
URL = "https://n8n.vyomos.org/webhook/watchmen-detect"

# Global variables
cellular_system = None
image_count = 0

def init_camera():
    """Initialize the camera sensor"""
    print("Initializing camera...")
    sensor.reset()
    sensor.set_pixformat(sensor.RGB565)
    sensor.set_framesize(sensor.WQXGA2)  # 320x240
    sensor.skip_frames(time=2000)
    print("✓ Camera initialized")

def capture_image():
    """Capture an image from the camera"""
    global image_count
    image_count += 1

    print(f"\n=== Capturing Image #{image_count} ===")
    img = sensor.snapshot()

    # Convert to JPEG for smaller size
    img_jpeg = img.compress(quality=70)

    return img_jpeg

def prepare_image_payload(img_jpeg):
    """Prepare the image payload for upload"""
    # Get image bytes
    img_bytes = img_jpeg.bytearray()
    encimb = encrypt_if_needed("P", img_bytes)
    imgbytes = ubinascii.b2a_base64(encimb)

    # # Convert to base64
    # img_base64 = ubinascii.b2a_base64(img_bytes).decode('utf-8').strip()

    # Create payload
    payload = {
        "machine_id": MACHINE_ID,
        "message_type": "event",
        "image": imgbytes,
        "image_count": image_count,
        "device_info": {
            "memory_free": gc.mem_free(),
            "uptime_ms": time.ticks_ms()
        }
    }

    return payload

def encrypt_if_needed(mst, msg):
    # if not ENCRYPTION_ENABLED:
    #     return msg
    if mst in ["H"]:
        # Must be less than 117 bytes
        if len(msg) > 117:
            print(f"Message {msg} is lnger than 117 bytes, cant encrypt via RSA")
            return msg
        msgbytes = enc.encrypt_rsa(msg, enc.load_rsa_pub())
        print(f"{mst} : Len msg = {len(msg)}, len msgbytes = {len(msgbytes)}")
        return msgbytes
    if mst == "P":
        msgbytes = enc.encrypt_hybrid(msg, enc.load_rsa_pub())
        print(f"{mst} : Len msg = {len(msg)}, len msgbytes = {len(msgbytes)}")
        return msgbytes
    return msg

def init_cellular():
    """Initialize the cellular connection"""
    global cellular_system

    print("\n=== Initializing Cellular System ===")
    cellular_system = ProductionBulkCellular(machine_id=MACHINE_ID)

    if not cellular_system.initialize():
        print("✗ Cellular initialization failed!")
        return False

    print("✓ Cellular system ready")
    return True

def upload_image(img_jpeg):
    """Upload an image via cellular"""
    global cellular_system

    if not cellular_system:
        print("✗ Cellular system not initialized")
        return False

    # Check connection health
    if not cellular_system.check_connection():
        print("Connection lost - attempting reconnect...")
        if not cellular_system.reconnect():
            print("✗ Reconnection failed")
            return False

    # Prepare payload
    payload = prepare_image_payload(img_jpeg)

    # Upload
    result = cellular_system.upload_data(payload, URL)

    if result and result.get('status_code') == 200:
        print(f"✓ Image #{image_count} uploaded successfully")
        print(f"  Upload time: {result.get('upload_time', 0):.2f}s")
        print(f"  Data size: {result.get('data_size', 0)/1024:.2f} KB")
        return True
    else:
        print(f"✗ Failed to upload image #{image_count}")
        if result:
            print(f"  HTTP Status: {result.get('status_code', 'Unknown')}")
        return False

def main():
    """Main function - captures and uploads images every 30 seconds"""

    # Verify device ID
    uid = binascii.hexlify(machine.unique_id())
    print(f"Running on device: {uid.decode()}")

    if uid != b'e076465dd7194025':
        print("✗ Error: This script is configured for device e076465dd7194025")
        print(f"  Current device: {uid.decode()}")
        sys.exit(1)

    print(f"✓ Device verified: Machine ID {MACHINE_ID}")

    # Initialize systems
    init_camera()

    if not init_cellular():
        print("✗ Failed to initialize cellular - exiting")
        return

    print(f"\n=== Starting Image Capture Loop ===")
    print(f"Capturing and uploading every {IMAGE_CAPTURE_INTERVAL} seconds")

    consecutive_failures = 0
    max_failures = 5

    try:
        while True:
            loop_start = time.ticks_ms()

            # Capture image
            try:
                img_jpeg = capture_image()
                print(f"✓ Image captured: {len(img_jpeg.bytearray())} bytes")
            except Exception as e:
                print(f"✗ Image capture error: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    print("Too many failures - restarting...")
                    machine.reset()
                time.sleep(IMAGE_CAPTURE_INTERVAL)
                continue

            # Upload image
            try:
                success = upload_image(img_jpeg)

                if success:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    print(f"Upload failures: {consecutive_failures}/{max_failures}")

                    if consecutive_failures >= max_failures:
                        print("Max failures reached - attempting full reconnect...")
                        if not cellular_system.reconnect():
                            print("Reconnect failed - restarting system...")
                            machine.reset()
                        consecutive_failures = 0

            except Exception as e:
                print(f"✗ Upload error: {e}")
                consecutive_failures += 1

            # Memory cleanup
            gc.collect()
            print(f"Memory free: {gc.mem_free()} bytes")

            # Calculate time to next capture
            loop_time = time.ticks_diff(time.ticks_ms(), loop_start) / 1000
            sleep_time = max(0, IMAGE_CAPTURE_INTERVAL - loop_time)

            if sleep_time > 0:
                print(f"\nNext capture in {sleep_time:.1f} seconds...")
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n=== Shutting Down ===")
        if cellular_system:
            cellular_system.shutdown()
        print("✓ System stopped")
    except Exception as e:
        print(f"\n=== System Error ===")
        print(f"Error: {e}")
        if cellular_system:
            cellular_system.shutdown()
        # Restart the system after critical error
        machine.reset()

# Optional: Create a simple async version if you prefer asyncio
import uasyncio as asyncio

async def async_capture_and_upload():
    """Async version of capture and upload loop"""
    global image_count

    while True:
        try:
            # Capture
            image_count += 1
            print(f"\n=== Async Capture #{image_count} ===")
            img = sensor.snapshot()
            img_jpeg = img.compress(quality=70)

            # Upload
            payload = prepare_image_payload(img_jpeg)
            result = cellular_system.upload_data(payload, URL)

            if result and result.get('status_code') == 200:
                print(f"✓ Async upload successful")
            else:
                print(f"✗ Async upload failed")

            # Cleanup
            gc.collect()

        except Exception as e:
            print(f"Async error: {e}")

        # Wait for next capture
        await asyncio.sleep(IMAGE_CAPTURE_INTERVAL)

async def async_main():
    """Async main function"""
    print("=== Async Mode ===")

    # Initialize
    init_camera()
    if not init_cellular():
        return

    # Create capture task
    asyncio.create_task(async_capture_and_upload())

    # Run forever
    while True:
        await asyncio.sleep(3600)

# Run the appropriate main function
if __name__ == "__main__":
    # Choose between sync and async mode
    USE_ASYNC = False  # Set to True to use async mode

    if USE_ASYNC:
        try:
            asyncio.run(async_main())
        except KeyboardInterrupt:
            print("Stopped")
    else:
        main()
