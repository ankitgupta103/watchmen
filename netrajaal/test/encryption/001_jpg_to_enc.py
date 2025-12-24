import os
import gc
import utime

import enc
import image

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

# Initialize encryption node
creator = 221
encnode = enc.EncNode(creator)

# ---------------------------------------------------------------------------
# Main Task: Encrypt JPG image and save as ENC
# ---------------------------------------------------------------------------
def main():
    print("INFO, Starting JPG to ENC conversion test...")
    
    
    # input file
    jpg_filepath = f"{MY_IMAGE_DIR}/221_1735689810000_raw.jpg"
    # output file
    enc_filepath = f"{MY_IMAGE_DIR}/221_1735689810000_testing.enc"
    
    
    # read raw file
    try:
        img = image.Image(jpg_filepath)
        imgbytes = img.bytearray()
        print(f"DEBUG, [IMG] Captured image, size: {len(imgbytes)} bytes")
    except Exception as e:
        print(f"ERROR, [IMG] Failed read raw image file: {e}")
        return
        
    # Encrypt image immediately
    enc_msgbytes = None
    try:
        enc_msgbytes = enc.encrypt_hybrid(imgbytes, encnode.get_pub_key())
        print(f"DEBUG, [IMG] Saving encrypted image to {enc_filepath} : encrypted size = {len(enc_msgbytes)} bytes...")
        # Save encrypted bytes to binary file
        with open(enc_filepath, "wb") as f:
            f.write(enc_msgbytes)
        os.sync()  # Force filesystem sync to SD card
        utime.sleep_ms(500)
        print(f"INFO, [IMG] Saved encrypted image: {enc_filepath}: encrypted size = {len(enc_msgbytes)} bytes")
    except Exception as e:
        print(f"ERROR, [IMG] Failed to save encrypted image: {e}")
        return
    finally:
        # Explicitly clean up image objects
        if imgbytes is not None:
            del imgbytes
        if img is not None:
            del img
        if enc_msgbytes is not None:
            del enc_msgbytes
        # Help GC reclaim memory
        gc.collect()

if __name__ == "__main__":
    main()
