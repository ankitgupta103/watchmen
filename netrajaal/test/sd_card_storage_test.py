"""
SD Card Storage Error Reproduction Script
This script reproduces the SD card storage issues on OpenMV RT1062:
- Issue 1: File not found immediately after saving
- Issue 2: EIO errors when reading files
- Issue 3: ENOENT errors for files that should exist
"""

import sensor
import image
import os
import utime
import gc

# Configuration
FS_ROOT = "/sdcard"  # SD card root
TEST_IMAGE_DIR = f"{FS_ROOT}/test_images"
TEST_COUNT = 100  # Number of test iterations
DELAY_AFTER_SAVE_MS = 500  # Delay after saving before reading (milliseconds)

def create_test_dir():
    """Create test directory if it doesn't exist"""
    try:
        if "test_images" not in os.listdir(FS_ROOT):
            os.mkdir(TEST_IMAGE_DIR)
            print(f"[INIT] Created directory: {TEST_IMAGE_DIR}")
        else:
            print(f"[INIT] Directory already exists: {TEST_IMAGE_DIR}")
    except Exception as e:
        print(f"[ERROR] Failed to create directory {TEST_IMAGE_DIR}: {e}")
        return False
    return True

def test_raw_image_save_and_read(iteration):
    """
    Test Issue 1: Save raw image and immediately read it back
    This reproduces "Could not find the file" error
    """
    print(f"\n[TEST {iteration}] === Testing Raw Image Save/Read ===")
    
    try:
        # Capture image
        print(f"[TEST {iteration}] Capturing image...")
        img = sensor.snapshot()
        img_bytes = img.bytearray()
        img_size = len(img_bytes)
        print(f"[TEST {iteration}] Captured image size: {img_size} bytes")
        
        # Save raw image
        raw_path = f"{TEST_IMAGE_DIR}/test_{iteration}_raw.jpg"
        print(f"[TEST {iteration}] Saving raw image to {raw_path}...")
        img.save(raw_path)
        print(f"[TEST {iteration}] Saved raw image: {raw_path}")
        
        # Delay before reading (as in original code)
        utime.sleep_ms(DELAY_AFTER_SAVE_MS)
        
        # Try to read the file back immediately
        print(f"[TEST {iteration}] Attempting to read image from {raw_path}...")
        try:
            read_img = image.Image(raw_path)
            read_img_bytes = read_img.bytearray()
            read_size = len(read_img_bytes)
            print(f"[TEST {iteration}] ✓ SUCCESS: Read image back, size: {read_size} bytes")
            
            # Verify sizes match
            if read_size == img_size:
                print(f"[TEST {iteration}] ✓ Image sizes match correctly")
            else:
                print(f"[TEST {iteration}] ✗ WARNING: Size mismatch! Original: {img_size}, Read: {read_size}")
            
            del read_img
            del read_img_bytes
        except Exception as read_error:
            print(f"[TEST {iteration}] ✗ FAILED: Could not read image file: {read_error}")
            return False
        
        del img
        del img_bytes
        gc.collect()
        return True
        
    except Exception as e:
        print(f"[TEST {iteration}] ✗ ERROR during save/read test: {e}")
        return False

def test_encrypted_file_save_and_read(iteration):
    """
    Test Issues 2 & 3: Save encrypted bytes and read them back
    This reproduces EIO and ENOENT errors
    """
    print(f"\n[TEST {iteration}] === Testing Encrypted File Save/Read ===")
    
    try:
        # Capture image and get bytes
        print(f"[TEST {iteration}] Capturing image for encryption test...")
        img = sensor.snapshot()
        img_bytes = img.bytearray()
        img_size = len(img_bytes)
        print(f"[TEST {iteration}] Captured image size: {img_size} bytes")
        
        # Simulate encryption (just use raw bytes for simplicity)
        enc_bytes = img_bytes  # In real code, this would be encrypted
        enc_filepath = f"{TEST_IMAGE_DIR}/test_{iteration}.enc"
        
        # Save encrypted bytes
        print(f"[TEST {iteration}] Saving encrypted file to {enc_filepath}...")
        with open(enc_filepath, "wb") as f:
            f.write(enc_bytes)
        print(f"[TEST {iteration}] Saved encrypted file: {enc_filepath} ({len(enc_bytes)} bytes)")
        
        # Delay before reading
        utime.sleep_ms(DELAY_AFTER_SAVE_MS)
        
        # Try to read the encrypted file back
        print(f"[TEST {iteration}] Attempting to read encrypted file from {enc_filepath}...")
        try:
            with open(enc_filepath, "rb") as f:
                read_enc_bytes = f.read()
            read_size = len(read_enc_bytes)
            print(f"[TEST {iteration}] ✓ SUCCESS: Read encrypted file, size: {read_size} bytes")
            
            # Verify sizes match
            if read_size == len(enc_bytes):
                print(f"[TEST {iteration}] ✓ Encrypted file sizes match correctly")
            else:
                print(f"[TEST {iteration}] ✗ WARNING: Size mismatch! Original: {len(enc_bytes)}, Read: {read_size}")
            
            del read_enc_bytes
        except Exception as read_error:
            error_code = str(read_error)
            if "EIO" in error_code or "[Errno 5]" in error_code:
                print(f"[TEST {iteration}] ✗ FAILED with EIO error: {read_error}")
            elif "ENOENT" in error_code or "[Errno 2]" in error_code:
                print(f"[TEST {iteration}] ✗ FAILED with ENOENT (file not found) error: {read_error}")
            else:
                print(f"[TEST {iteration}] ✗ FAILED: Could not read encrypted file: {read_error}")
            return False
        
        del img
        del img_bytes
        del enc_bytes
        gc.collect()
        return True
        
    except Exception as e:
        print(f"[TEST {iteration}] ✗ ERROR during encrypted file test: {e}")
        return False

def main():
    """Main test loop"""
    print("=" * 60)
    print("SD Card Storage Error Reproduction Script")
    print("=" * 60)
    
    # Initialize sensor
    sensor.reset()
    sensor.set_pixformat(sensor.RGB565)
    sensor.set_framesize(sensor.QVGA)  # 320x240
    sensor.skip_frames(time=2000)
    print("[INIT] Sensor initialized")
    
    # Create test directory
    if not create_test_dir():
        print("[ERROR] Failed to create test directory. Exiting.")
        return
    
    # Run tests
    success_count = 0
    raw_save_read_failures = 0
    encrypted_file_failures = 0
    
    for i in range(1, TEST_COUNT + 1):
        print(f"\n{'=' * 60}")
        print(f"ITERATION {i} of {TEST_COUNT}")
        print(f"{'=' * 60}")
        
        # Test 1: Raw image save/read
        if test_raw_image_save_and_read(i):
            success_count += 1
        else:
            raw_save_read_failures += 1
        
        # Small delay between tests
        utime.sleep_ms(100)
        
        # Test 2: Encrypted file save/read
        if test_encrypted_file_save_and_read(i):
            success_count += 1
        else:
            encrypted_file_failures += 1
        
        # Delay between iterations
        utime.sleep_ms(200)
        
        # Print progress every 10 iterations
        if i % 10 == 0:
            print(f"\n[PROGRESS] Completed {i}/{TEST_COUNT} iterations")
            print(f"[STATS] Raw image failures: {raw_save_read_failures}")
            print(f"[STATS] Encrypted file failures: {encrypted_file_failures}")
    
    # Final summary
    print(f"\n{'=' * 60}")
    print("TEST SUMMARY")
    print(f"{'=' * 60}")
    total_tests = TEST_COUNT * 2  # Two tests per iteration
    print(f"Total tests run: {total_tests}")
    print(f"Successful tests: {success_count}")
    print(f"Failed tests: {total_tests - success_count}")
    print(f"Raw image save/read failures: {raw_save_read_failures}")
    print(f"Encrypted file failures: {encrypted_file_failures}")
    print(f"Success rate: {(success_count / total_tests) * 100:.2f}%")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
