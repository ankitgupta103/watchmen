import os
import gc
import utime
import binascii
import machine
import sys

import enc
import image
import sensor

# -----------------------------------▼▼▼▼▼-----------------------------------
# Device ID Detection - Set my_addr dynamically based on device unique ID
# -----------------------------------▲▲▲▲▲-----------------------------------

DYNAMIC_SPATH = True  # Used in device ID detection logic

uid = binascii.hexlify(machine.unique_id())      # Returns 8 byte unique ID for board
# COMMAND CENTERS, OTHER NODES
my_addr = None
shortest_path_to_cc = []

if uid == b'e076465dd7194025':
    my_addr = 219
elif uid == b'e076465dd7193a09':
    my_addr = 225
    if not DYNAMIC_SPATH:
        shortest_path_to_cc = [219]
elif uid ==  b'e076465dd7090d1c':
    my_addr = 221
    if not DYNAMIC_SPATH:
        shortest_path_to_cc = [225, 219]
elif uid == b'e076465dd7091027':
    my_addr = 222
elif uid == b'e076465dd7091843':
    my_addr = 223
else:
    try:
        import omv
        board_id = omv.board_id()
    except:
        board_id = "unknown"
    print(f"Error: in 003_image_capture.py: Unknown device ID for {board_id}")
    sys.exit()

# Set RTC for consistent timestamps
rtc = machine.RTC()
rtc.datetime((2025, 1, 1, 0, 0, 0, 0, 0))
    
    
# Filesystem setup
def get_fs_root_for_storage():
    has_sdcard = True
    try:
        os.listdir('/sdcard')
        print(f"DEBUG, [FS] SD card available")
    except OSError:
        print(f"ERROR, [FS] SD card not found!")
        has_sdcard = False

    if has_sdcard:
        return "/sdcard"
    else:
        return "/flash"

def create_dir_if_not_exists(dir_path):
    try:
        parts = [p for p in dir_path.split('/') if p]
        if len(parts) < 2:
            print(f"WARNING, [FS] Invalid directory path (no parent): {dir_path}")
            return
        parent = '/' + '/'.join(parts[:-1])
        dir_name = parts[-1]
        if dir_name not in os.listdir(parent):
            os.mkdir(dir_path)
            print(f"INFO, [FS] Created {dir_path}")
        else:
            try:
                os.listdir(dir_path)
                print(f"INFO, [FS] {dir_path} directory already exists")
            except OSError:
                print(f"ERROR, dir:{dir_path} exists but not a directory, so deleting and recreating")
                try:
                    os.remove(dir_path)
                    os.mkdir(dir_path)
                    print(f"INFO, Removed file {dir_path} and created directory")
                except OSError as e:
                    print(f"ERROR, WARNING - Failed to remove file {dir_path} and create directory: {e}")
    except OSError as e:
        print(f"ERROR, [FS] Failed to create/access {dir_path}: {e}")

FS_ROOT = get_fs_root_for_storage()
print(f"INFO, [FS] Using FS_ROOT : {FS_ROOT}")
MY_IMAGE_DIR = f"{FS_ROOT}/myimages"
create_dir_if_not_exists(MY_IMAGE_DIR)

# Initialize sensor
print("INFO, [SENSOR] Initializing camera sensor...")
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.HD)
print("INFO, [SENSOR] Camera sensor initialized")

# Initialize encryption node
encnode = enc.EncNode(my_addr)
print(f"INFO, [ENC] Encryption node initialized for my_addr: {my_addr}")

def get_epoch_ms(): # get epoch milliseconds, eg. 1381791310000
    return utime.time_ns() // 1_000_000

def encrypt_if_needed(msg_typ, msg):
    # Input: msg_typ: str message type, msg: bytes; Output: bytes (possibly encrypted message)
    if msg_typ == "P":
        msgbytes = enc.encrypt_hybrid(msg, encnode.get_pub_key())
        print(f"DEBUG, {msg_typ} : Len msg = {len(msg)}, len msgbytes = {len(msgbytes)}")
        return msgbytes
    return msg

# ---------------------------------------------------------------------------
# Main Task: Continuously capture images, save raw and encrypted versions
# ---------------------------------------------------------------------------
def main():
    print("INFO, Starting continuous image capture test...")
    print("INFO, Capturing images every 1 second...")
    
    capture_count = 0
    
    while True:
        img = None
        imgbytes = None
        enc_msgbytes = None
        try:
            # Get timestamp for this capture
            event_epoch_ms = get_epoch_ms()
            capture_count += 1
            print(f"INFO, [CAPTURE] 🅾🅾🅾🅾🅾🅾❯❯ Capturing image #{capture_count}... ❮❮🅾🅾🅾🅾🅾🅾")
            
            # Capture image
            img = sensor.snapshot()
            print(f"DEBUG, [CAPTURE] Image captured, size: {len(img.bytearray())} bytes")
            
            # Save raw image
            try:
                raw_path = f"{MY_IMAGE_DIR}/{my_addr}_{event_epoch_ms}_raw.jpg"
                print(f"DEBUG, [CAPTURE] Saving raw image to {raw_path} : imbytesize = {len(img.bytearray())}")
                img.save(raw_path)
                os.sync()  # Force filesystem sync to SD card
                utime.sleep_ms(500)
                print(f"INFO, [CAPTURE] Saved raw image: {raw_path}: raw size = {len(img.bytearray())} bytes")
            except Exception as e:
                print(f"ERROR, [CAPTURE] Failed to save raw image: {e}")
                continue
            
            # Read raw file to get image bytes
            try:
                img = image.Image(raw_path)
                imgbytes = img.bytearray()
                print(f"INFO, [CAPTURE] Read image file, size: {len(imgbytes)} bytes")
            except Exception as e:
                print(f"ERROR, [CAPTURE] Failed read image file: {e}")
                continue
                
            # Encrypt image immediately
            try:
                enc_msgbytes = encrypt_if_needed("P", imgbytes)
                enc_filepath = f"{MY_IMAGE_DIR}/{my_addr}_{event_epoch_ms}.enc"
                print(f"DEBUG, [CAPTURE] Saving encrypted image to {enc_filepath} : encrypted size = {len(enc_msgbytes)} bytes...")
                # Save encrypted bytes to binary file
                with open(enc_filepath, "wb") as f:
                    f.write(enc_msgbytes)
                os.sync()  # Force filesystem sync to SD card
                utime.sleep_ms(500)
                print(f"INFO, [CAPTURE] Saved encrypted image: {enc_filepath}: encrypted size = {len(enc_msgbytes)} bytes")
            except Exception as e:
                print(f"ERROR, [CAPTURE] Failed to save encrypted image: {e}")
                continue
                
            print(f"INFO, [CAPTURE] Successfully captured and saved image #{capture_count}")
            
        except Exception as e:
            print(f"ERROR, [CAPTURE] Unexpected error in image capture and saving: {e}")
        finally:
            # Explicitly clean up image object
            if img is not None:
                del img
            if imgbytes is not None:
                del imgbytes
            if enc_msgbytes is not None:
                del enc_msgbytes
            # Help GC reclaim memory immediately
            gc.collect()
        
        # Wait 1 second before next capture
        print(f"DEBUG, [CAPTURE] Waiting 1 second before next capture...")
        utime.sleep(1)

if __name__ == "__main__":
    main()

