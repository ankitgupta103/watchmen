# OpenMV RT1062 WiFi Data Transfer

## Setup Instructions

### 1. Create WiFi Hotspot on Laptop

#### On Linux:
```bash
# Using nmcli (NetworkManager)
nmcli device wifi hotspot ssid=A password=123456789
```

### 2. Find Your Laptop's Hotspot IP Address

The hotspot IP is usually the gateway IP. 

To find it:
```bash
# Linux/macOS
ip addr show | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig
```

Look for the IP address of the hotspot interface.

### 3. Configure OpenMV Script

1. Edit `openmv_wifi_sender.py`:
   - Set `WIFI_SSID` to your laptop hotspot name
   - Set `WIFI_PASSWORD` to your hotspot password
   - Set `LAPTOP_IP` to your laptop's hotspot IP address
   - Adjust `LAPTOP_PORT` if needed (default: 5000)

2. Upload the script to your OpenMV device:
   - Open OpenMV IDE
   - Connect your OpenMV RT1062
   - Copy `openmv_wifi_sender.py` to the device (save as `main.py` or run directly)

### 4. Start Laptop Receiver

On your laptop, run:
```bash
python3 laptop_receiver.py
```

The server will display its IP address. Make sure the OpenMV script uses this IP.

### 5. Run OpenMV Script

Run the script on your OpenMV device. It will:
1. Connect to your WiFi hotspot
2. Send data every 2 seconds to your laptop
3. Display connection status and data transmission

## Customizing Data Transmission

Edit the `main()` function in `openmv_wifi_sender.py` to send your specific data:

```python
# Example: Send sensor data
sensor_data = {
    "temperature": 25.5,
    "humidity": 60,
    "timestamp": time.ticks_ms()
}
data = json.dumps(sensor_data) + "\n"
send_data(data, LAPTOP_IP, LAPTOP_PORT)
```
