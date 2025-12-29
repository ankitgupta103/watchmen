import os
import gc
import utime
import machine
import image
import sensor


# Set RTC initial time
rtc = machine.RTC()
rtc.datetime((2025, 1, 1, 0, 0, 0, 0, 0))
    
    
# Filesystem setup
def get_fs_root_for_storage():
    has_sdcard = True
    try:
        os.listdir('/sdcard')
    except OSError:
        print(f"ERROR, SD card not found, using `/flash` memory...")
        has_sdcard = False
    if has_sdcard:
        return "/sdcard"
    else:
        return "/flash"

def create_dir_if_not_exists(dir_path):
    try:
        parts = [p for p in dir_path.split('/') if p]
        if len(parts) < 2:
            print(f"WARNING, Invalid directory path (no parent): {dir_path}")
            return
        parent = '/' + '/'.join(parts[:-1])
        dir_name = parts[-1]
        if dir_name not in os.listdir(parent):
            os.mkdir(dir_path)
            print(f"INFO, Created {dir_path}")
        else:
            try:
                os.listdir(dir_path)
            except OSError:
                print(f"ERROR, dir:{dir_path} exists but not a directory, so deleting and recreating")
                try:
                    os.remove(dir_path)
                    os.mkdir(dir_path)
                    print(f"INFO, Removed file {dir_path} and created directory")
                except OSError as e:
                    print(f"ERROR, Failed to remove file {dir_path} and create directory: {e}")
    except OSError as e:
        print(f"ERROR, Failed to create/access {dir_path}: {e}")

FS_ROOT = get_fs_root_for_storage()
MY_IMAGE_DIR = f"{FS_ROOT}/myimages"
create_dir_if_not_exists(MY_IMAGE_DIR)

# Initialize sensor
print("INFO, Initializing camera sensor...")
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.HD)
print("INFO, Camera sensor initialized")

# Initialize encryption node

def get_epoch_ms(): # get epoch milliseconds, eg. 1381791310000
    return utime.time_ns() // 1_000_000


# ---------------------------------------------------------------------------
# Main Task: Continuously capture images, save raw and encrypted versions
# ---------------------------------------------------------------------------
def main():
    capture_count = 0
    SLEEP_TIME = 2
    print("INFO, main image capture loop started...")
    
    
    
    while True:
        img = None
        loaded_bytes = None
        try:
            # Get timestamp for this capture
            event_epoch_ms = get_epoch_ms()
            capture_count += 1
            print(f"INFO, 🅾🅾🅾🅾🅾🅾❯❯ Capturing image #{capture_count}... ❮❮🅾🅾🅾🅾🅾🅾")
            
            # Capture image
            img = sensor.snapshot()
            print(f"DEBUG, Image captured, size: {len(img.bytearray())} bytes")
            
            # Save raw image
            try:
                raw_path = f"{MY_IMAGE_DIR}/{event_epoch_ms}_raw.jpg"
                print(f"DEBUG, Saving raw image to {raw_path} : imbytesize = {len(img.bytearray())}")
                
                # For SD card, save to flash first then copy (workaround for SD card buffering issues)
                if FS_ROOT == "/sdcard":
                    # Save to flash first (this works reliably)
                    temp_path = f"/flash/temp_{event_epoch_ms}_raw.jpg"
                    img.save(temp_path)
                    utime.sleep_ms(200)  # Brief delay for flash write
                    os.sync()  # Ensure flash write is complete
                    utime.sleep_ms(200)
                    
                    # Verify the flash file was saved correctly
                    try:
                        flash_stat = os.stat(temp_path)
                        flash_size = flash_stat[6]
                        print(f"INFO, Saved raw image to flash: {temp_path}: flash file size = {flash_size} bytes, raw image size = {len(img.bytearray())} bytes")
                        if flash_size == 0:
                            raise Exception("Flash file is empty after save")
                        if flash_size < 1000:  # JPEG should be at least a few KB
                            raise Exception(f"Flash file suspiciously small: {flash_size} bytes")
                    except Exception as verify_error:
                        print(f"ERROR, Flash file verification failed: {verify_error}")
                        raise
                    
                    # Now copy from flash to SD card using file operations
                    try:
                        # Remove destination file if it exists (to avoid partial write issues)
                        try:
                            os.remove(raw_path)
                        except OSError:
                            pass  # File doesn't exist, which is fine
                        
                        # Read entire file from flash into memory
                        with open(temp_path, "rb") as src:
                            file_data = src.read()
                        
                        file_size = len(file_data)
                        print(f"DEBUG, Read {file_size} bytes from flash file")
                        
                        if file_size == 0:
                            raise Exception("Source file is empty")
                        
                        # Write entire file to SD card in one operation
                        print(f"DEBUG, Writing {file_size} bytes to SD card: {raw_path}")
                        try:
                            with open(raw_path, "wb") as dst:
                                bytes_written = dst.write(file_data)
                                if bytes_written != file_size:
                                    raise Exception(f"Write incomplete: wrote {bytes_written} of {file_size} bytes")
                                print(f"DEBUG, Wrote {bytes_written} bytes to file handle")
                        except OSError as e:
                            print(f"ERROR, SD card write failed: {e}")
                            # Check if SD card is still accessible
                            try:
                                os.listdir('/sdcard')
                                print(f"DEBUG, SD card is still accessible")
                            except OSError as sd_error:
                                print(f"ERROR, SD card is no longer accessible: {sd_error}")
                            raise
                        
                        # Close file explicitly and wait before sync
                        # The 'with' statement should close it, but add delay to be safe
                        utime.sleep_ms(200)
                        
                        # Ensure SD card write is complete
                        try:
                            os.sync()
                            utime.sleep_ms(500)
                        except Exception as sync_error:
                            print(f"WARNING, Sync failed: {sync_error}")
                        
                        # Verify the file was written correctly
                        try:
                            written_stat = os.stat(raw_path)
                            written_size = written_stat[6]
                            if written_size != file_size:
                                print(f"ERROR, File size mismatch! Expected {file_size}, got {written_size}")
                                raise Exception(f"File copy incomplete: {written_size} != {file_size}")
                            print(f"DEBUG, Verified copy: {written_size} bytes written to SD card")
                        except Exception as verify_error:
                            print(f"ERROR, Failed to verify copied file: {verify_error}")
                            raise
                        
                        # Clean up temp file
                        # try:
                        #     os.remove(temp_path)
                        # except:
                        #     pass
                        print(f"INFO, Saved raw image to SD card via flash: {raw_path}: raw size = {len(img.bytearray())} bytes")
                    except Exception as e:
                        print(f"ERROR, Failed to copy image from flash to SD card: {e}")
                        # Try to clean up temp file
                        # try:
                        #     os.remove(temp_path)
                        # except:
                        #     pass
                        continue
                else:
                    # For flash memory, save directly (this works fine)
                    img.save(raw_path)
                    utime.sleep_ms(200)
                    os.sync()
                    print(f"INFO, Saved raw image: {raw_path}: raw size = {len(img.bytearray())} bytes")
            except Exception as e:
                print(f"ERROR, Failed to save raw image: {e}")
                continue
            
            
            # Read raw file to get image bytes (use different variable to avoid overwriting original img)
            # Only read if we successfully saved the file
            try:
                # Verify file exists and has content before reading
                file_stat = os.stat(raw_path)
                if file_stat[6] == 0:  # Check file size
                    print(f"ERROR, Saved file is empty: {raw_path}")
                    continue
                print(f"DEBUG, File exists, size: {file_size} bytes")
                # Use different variable name to avoid overwriting original img object
                loaded_img = image.Image(raw_path)
                loaded_bytes = loaded_img.bytearray()
                del loaded_img  # Clean up immediately
                gc.collect()
                print(f"INFO, Read image file, size: {len(loaded_bytes)} bytes")
            except Exception as e:
                print(f"ERROR, Failed to read image file: {e}")
                loaded_bytes = None  # Ensure it's set to None on error
                continue
                
                
            print(f"INFO, Successfully captured and saved image #{capture_count}")
            
        except Exception as e:
            print(f"ERROR, Unexpected error in image capture and saving: {e}")
        finally:
            # Explicitly clean up image object
            if img is not None:
                del img
            if loaded_bytes is not None:
                del loaded_bytes
            # Help GC reclaim memory immediately
            gc.collect()
            # Additional small delay to ensure cleanup completes
            utime.sleep_ms(1600)
        
        # Wait 1 second before next capture
        print(f"DEBUG, Waiting {SLEEP_TIME} second before next capture...")
        utime.sleep(SLEEP_TIME)

if __name__ == "__main__":
    main()

