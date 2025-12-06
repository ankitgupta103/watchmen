# BridgeX-ESP - Two-Node LoRa Communication

ESP32 project with SX1262 LoRa driver for bidirectional communication between two ESP32 boards.

## Hardware Connections

```
ESP32          SX1262 Module
------         -------------
GPIO17  -----> TX (UART TX)
GPIO16  <----- RX (UART RX)
GPIO4   -----> M0 (Mode control)
GPIO5   -----> M1 (Mode control)
3.3V    -----> VCC
GND     -----> GND
```

## How to Test on Both Devices

### Step 1: Flash Node 1 (First ESP32)

1. **Set NODE_ID to 1** in `main/main.c`:
   ```c
   #define NODE_ID 1
   ```

2. **Put ESP32 in boot mode** (IMPORTANT - Do this FIRST):
   - **Disconnect** USB cable
   - **Press and HOLD** the **BOOT** button
   - **Connect** USB cable (while holding BOOT)
   - **Press and release** the **RESET** button (still holding BOOT)
   - **Release** the **BOOT** button
   - Device should now be in download mode

3. **Build and flash** (run immediately after boot mode):
   ```bash
   source $HOME/esp/esp-idf/export.sh
   idf.py build
   idf.py -p /dev/ttyACM0 flash
   ```

   **If flashing fails**, try:
   ```bash
   # Try lower baud rate
   idf.py -p /dev/ttyACM0 flash --baud 115200
   
   # Or even lower
   idf.py -p /dev/ttyACM0 flash --baud 9600
   ```

### Step 2: Flash Node 2 (Second ESP32)

1. **Set NODE_ID to 2** in `main/main.c`:
   ```c
   #define NODE_ID 2
   ```

2. **Put ESP32 in boot mode** (same as Step 1 above)

3. **Build and flash**:
   ```bash
   idf.py build
   idf.py -p /dev/ttyACM1 flash
   ```
   
   **If flashing fails**, try lower baud rate:
   ```bash
   idf.py -p /dev/ttyACM1 flash --baud 115200
   ```

### Step 3: Monitor Both Devices

**Terminal 1 - Monitor Node 1**:
```bash
idf.py -p /dev/ttyACM0 monitor
```

**Terminal 2 - Monitor Node 2**:
```bash
idf.py -p /dev/ttyACM1 monitor
```

## Expected Output

### Node 1 (Address 0x0001)
```
I (xxxx) LORA_COMM: Node-1 - LoRa Communication
I (xxxx) LORA_COMM: My Address: 0x0001
I (xxxx) LORA_COMM: Target Address: 0x0002
I (xxxx) LORA_COMM: SX1262 initialized successfully!
I (xxxx) LORA_COMM: >>> [SEND] To 0x0002: Hello from Node-1! Message #1
I (xxxx) LORA_COMM:     ✓ Message sent successfully
I (xxxx) LORA_COMM: <<< [RECEIVE] 25 bytes:
I (xxxx) LORA_COMM:     Message: Hello from Node-2! Message #1
I (xxxx) LORA_COMM:     RSSI: -85 dBm
```

### Node 2 (Address 0x0002)
```
I (xxxx) LORA_COMM: Node-2 - LoRa Communication
I (xxxx) LORA_COMM: My Address: 0x0002
I (xxxx) LORA_COMM: Target Address: 0x0001
I (xxxx) LORA_COMM: SX1262 initialized successfully!
I (xxxx) LORA_COMM: >>> [SEND] To 0x0001: Hello from Node-2! Message #1
I (xxxx) LORA_COMM:     ✓ Message sent successfully
I (xxxx) LORA_COMM: <<< [RECEIVE] 25 bytes:
I (xxxx) LORA_COMM:     Message: Hello from Node-1! Message #1
I (xxxx) LORA_COMM:     RSSI: -82 dBm
```

## Configuration

Both nodes must have:
- Same frequency: 868 MHz (default)
- Same network ID: 0 (default)
- Same air speed: 2400 bps (default)
- Different addresses: 0x0001 (Node 1) and 0x0002 (Node 2)

## Troubleshooting

### Flashing Fails with "serial TX path seems to be down"

**This error means: Device is detected and in download mode, but the TX wire (ESP32 TX → Computer RX) is not working.**

#### Quick Diagnostic Test

Run this to verify the connection:
```bash
# Test if you can READ from device (RX path works)
timeout 3 cat /dev/ttyACM0 | strings
# If you see "waiting for download" or boot messages, RX path works ✓

# Test if you can WRITE to device (TX path)
python3 -c "import serial; s=serial.Serial('/dev/ttyACM0', 115200); s.write(b'test'); s.close(); print('Write test completed')"
# If this works without error, TX path should work ✓
```

#### Solutions (in order of likelihood):

1. **Check TX Wire Connection** (Most Common Issue):
   - **ESP32 TX pin → USB-to-Serial RX pin** (this is the broken path!)
   - Verify the wire is properly connected and not loose
   - Check for broken wire (use multimeter continuity test)
   - Ensure good contact (no oxidation on pins)

2. **Manual Boot Mode Entry** (Critical Timing):
   - **Disconnect** USB cable completely
   - **Press and HOLD** the **BOOT** button
   - **Connect** USB cable (while holding BOOT)
   - **Press and release** the **RESET** button (still holding BOOT)
   - **Release** the **BOOT** button
   - **Within 5 seconds**, run flash command:
     ```bash
     idf.py -p /dev/ttyACM0 flash --baud 115200
     ```

3. **Try Different Baud Rates** (Lower = More Reliable):
   ```bash
   # Try 115200 first
   idf.py -p /dev/ttyACM0 flash --baud 115200
   
   # If fails, try 9600 (very slow but more reliable)
   idf.py -p /dev/ttyACM0 flash --baud 9600
   
   # If fails, try 230400 (faster, sometimes works)
   idf.py -p /dev/ttyACM0 flash --baud 230400
   ```

4. **Check USB-to-Serial Adapter**:
   - If using external USB-to-Serial adapter (CP2102, CH340, FT232):
     - Verify adapter is working (test with another device)
     - Check if drivers are installed correctly
     - Try a different adapter if available
   - If using ESP32's built-in USB (ESP32-S2/S3):
     - Try different USB cable (must be data-capable)
     - Try different USB port on computer
     - Check if USB port provides enough power

5. **Verify Pin Connections**:
   - **ESP32 Development Board**: Usually has auto-reset circuit
     - Check if BOOT button is working (should put device in download mode)
     - Some boards need EN pin pulled low during boot
   - **Bare ESP32 Module**: Requires manual connections
     - TX: GPIO1 (UART0_TX) → USB-to-Serial RX
     - RX: GPIO3 (UART0_RX) → USB-to-Serial TX
     - GND: Common ground
     - 3.3V: Power supply

6. **Hardware Reset Before Flash**:
   ```bash
   # Manually reset device, then immediately flash
   python3 -c "import serial; s=serial.Serial('/dev/ttyACM0', 115200); s.setDTR(False); s.setRTS(True); import time; time.sleep(0.1); s.setDTR(True); s.setRTS(False); s.close()"
   idf.py -p /dev/ttyACM0 flash --baud 115200
   ```

7. **Use esptool Directly** (Bypass idf.py):
   ```bash
   source $HOME/esp/esp-idf/export.sh
   python3 $HOME/.espressif/python_env/idf5.1_py3.10_env/bin/esptool.py \
     --chip esp32 --port /dev/ttyACM0 --baud 115200 \
     --before default_reset --after hard_reset \
     write_flash --flash_mode dio --flash_freq 40m --flash_size 2MB \
     0x1000 build/bootloader/bootloader.bin \
     0x8000 build/partition_table/partition-table.bin \
     0x10000 build/BridgeX-ESP.bin
   ```

#### Still Not Working?

If all above fail, the issue is likely:
- **Broken TX wire** (most common) - replace the wire
- **Faulty USB-to-Serial adapter** - try different adapter
- **Damaged ESP32 UART TX pin** - try different ESP32 board
- **USB port power issue** - try powered USB hub or different port

### No Messages Received
- Verify both nodes have same frequency, network ID, and air speed
- Check antennas are connected
- Ensure modules are within range (< 10 meters for initial test)
- Verify power supply is stable (3.3V)

### Flashing Success Indicators

When flashing works correctly, you'll see:
```
Connecting...
Detecting chip type... ESP32
Writing at 0x00001000... (bootloader)
Writing at 0x00010000... (application)
Writing at 0x00008000... (partition table)
Hash of data verified.
Leaving...
Hard resetting via RTS pin...
```

If you see "Hash of data verified" and "Leaving...", the flash was successful!

### Port Permission Issues

If you get "Permission denied" errors:
```bash
# Add user to dialout group (one-time setup)
sudo usermod -a -G dialout $USER
# Log out and log back in for changes to take effect

# Or temporarily fix permissions
sudo chmod 666 /dev/ttyACM0
```

### Check for Other Processes Using Port

If port is busy:
```bash
# Check what's using the port
lsof /dev/ttyACM0

# Kill processes using the port
sudo fuser -k /dev/ttyACM0
```

## Project Structure

```
BridgeX-ESP/
├── main/
│   ├── main.c          # Main application (two-node communication)
│   ├── sx1262.h        # SX1262 driver header
│   ├── sx1262.c        # SX1262 driver implementation
│   └── CMakeLists.txt  # Build configuration
├── CMakeLists.txt      # Project build configuration
├── sdkconfig          # ESP-IDF configuration
└── README.md          # This file
```

## Quick Reference

### Build Commands
```bash
source $HOME/esp/esp-idf/export.sh
idf.py build                    # Build project
idf.py -p /dev/ttyACM0 flash    # Flash to device
idf.py -p /dev/ttyACM0 monitor  # Monitor serial output
idf.py fullclean                # Clean build
```

### Configuration
- **Node ID**: Set `NODE_ID` in `main/main.c` (1 or 2)
- **Frequency**: 868 MHz (default, can be changed in code)
- **Network ID**: 0 (default, must match on both nodes)
- **Air Speed**: 2400 bps (default, must match on both nodes)
- **Addresses**: 0x0001 (Node 1), 0x0002 (Node 2)
