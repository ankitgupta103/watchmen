import os
import gc

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

# ---------------------------------------------------------------------------
# Main Task: Decrypt encrypted image and save as JPG
# ---------------------------------------------------------------------------
def main():
    print("INFO, Starting ENC to JPG conversion test...")
    creator = 221
    encnode = enc.EncNode(creator)
    
    
    
    # input file
    enc_filepath = f"{MY_IMAGE_DIR}/221_1735689700000.enc"
    # output file
    jpg_file_path = f"{MY_IMAGE_DIR}/221_1735689700000_raw_testing.jpg"
    
    
    
    print(f"DEBUG, [IMG] Processing: {enc_filepath}")
    enc_msgbytes = None

    try:
        print(f"DEBUG, [IMG] Reading encrypted image of creator: {creator}, file: {enc_filepath}")
        with open(enc_filepath, "rb") as f:
            enc_msgbytes = f.read()
        print(f"DEBUG, [IMG] Read encrypted image of creator: {creator}, file: {len(enc_msgbytes)} bytes")
    except Exception as e:
        print(f"ERROR, [IMG] Failed to read encrypted image from file, {enc_filepath}, e: {e}")
        return
                
    print(f"INFO, [IMG] Received image of size {len(enc_msgbytes)}")
    img_bytes = None
    img = None
    try:
        img_bytes = enc.decrypt_hybrid(enc_msgbytes, encnode.get_prv_key(creator))
        img = image.Image(320, 240, image.JPEG, buffer=img_bytes)
        print(f"INFO, [IMG] Saving to file {jpg_file_path}, img_size: {len(img_bytes)} bytes")
        img.save(jpg_file_path)
    except Exception as e:
        print(f"ERROR, [IMG] Failed to decrypt and save image: {e}")
    finally:
        # Explicitly clean up image objects
        if img_bytes is not None:
            del img_bytes
        if img is not None:
            del img
        # Help GC reclaim memory
        gc.collect()

if __name__ == "__main__":
    main()
