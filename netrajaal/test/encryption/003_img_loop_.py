import os
import gc
import utime
import machine
import sensor
import random

# Initialize RTC
rtc = machine.RTC()
rtc.datetime((2025, 1, 1, 0, 0, 0, 0, 0))

# Setup filesystem
def get_fs_root():
    try:
        os.listdir('/sdcard')
        return "/sdcard"
    except OSError:
        print("SD card not found, using /flash")
        return "/flash"

def create_dir(path):
    try:
        parts = [p for p in path.split('/') if p]
        parent = '/' + '/'.join(parts[:-1])
        if parts[-1] not in os.listdir(parent):
            os.mkdir(path)
    except OSError as e:
        print(f"Failed to create {path}: {e}")

FS_ROOT = get_fs_root()
MY_IMAGE_DIR = f"{FS_ROOT}/myimages1"
create_dir(MY_IMAGE_DIR)

# Initialize camera
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.HD)

def get_epoch_ms():
    return utime.time_ns() // 1_000_000

def get_rand_str(len=3):
    # Input: None; Output: str random 3-letter uppercase identifier
    rstr = ""
    for i in range(len):
        rstr += chr(65+random.randint(0,25))
    return rstr


# Main capture loop
def main():
    image_limit = 5
    capture_count = 0
    SLEEP_TIME = 2
    print("Starting image capture...")

    for i in range(image_limit):
        img = None
        try:
            capture_count += 1
            print(f"Capturing image #{capture_count}")
            
            img = sensor.snapshot()
            raw_path = f"{MY_IMAGE_DIR}/{get_epoch_ms()}_{get_rand_str()}_raw.jpg"
            img.save(raw_path)
            utime.sleep_ms(10)
            # # os.sync()
            # utime.sleep_ms(10)
            os.sync()  # Force filesystem sync to SD card
            utime.sleep_ms(1600)  # Increased delay to ensure FAT filesystem fully commits
            print(f"Saved: {raw_path}")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if img:
                del img
            gc.collect()
            utime.sleep_ms(10)
        
        utime.sleep(SLEEP_TIME)
        print(i)

if __name__ == "__main__":
    main()