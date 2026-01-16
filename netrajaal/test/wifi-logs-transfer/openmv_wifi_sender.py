import network
import socket
import time
import ujson
import ubinascii
import sensor
import image

WIFI_SSID = "A"
WIFI_PASSWORD = "123456789"

LAPTOP_IP = "10.42.0.1"     
LAPTOP_PORT = 5000  

# Dummy data constants
MACHINE_ID = 221
UPTIME_START = time.ticks_ms()

def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    print("Connecting to WiFi...")
    max_wait = 20
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print("Waiting for connection...")
        time.sleep(1)

    if wlan.status() != 3:
        raise RuntimeError("WiFi connection failed")

    print("WiFi connected!")
    print("IP address:", wlan.ifconfig()[0])
    return wlan

def create_persistent_connection(host, port, max_retries=3):
    """Create and return a persistent TCP connection"""
    for attempt in range(max_retries):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            
            print(f"Connecting to {host}:{port}... (attempt {attempt + 1}/{max_retries})")
            sock.connect((host, port))
            print("Connected! Connection established and kept alive.")
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            return sock
        except Exception as e:
            print(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise
    return None

def send_data_persistent(sock, data):
    """Send data over existing persistent connection"""
    try:
        if sock is None:
            return False, None
            
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        sock.sendall(data)
        print(f"Sent {len(data)} bytes")
        
        try:
            sock.settimeout(1)
            response = sock.recv(1024)
            if response:
                print("Response:", response.decode('utf-8'))
        except socket.timeout:
            pass
        except:
            pass
        finally:
            sock.settimeout(10)
        
        return True, sock
    except (OSError, socket.error) as e:
        print(f"Error sending data: {e}")
        try:
            sock.close()
        except:
            pass
        return False, None
    except Exception as e:
        print(f"Unexpected error: {e}")
        try:
            sock.close()
        except:
            pass
        return False, None

def create_heartbeat_data():
    """Create dummy heartbeat data"""
    uptime = time.ticks_diff(time.ticks_ms(), UPTIME_START) // 1000
    total_images = 10
    person_images = 5
    gps_coords = "28.6139,77.2090"  # Dummy GPS (Delhi)
    gps_staleness = 30
    neighbours = [222, 223]
    shortest_path = [221, 9]
    
    # Format: machine_id:uptime:total_images:person_images:gps:gps_staleness:neighbours:shortest_path
    hb_msg = f"{MACHINE_ID}:{uptime}:{total_images}:{person_images}:{gps_coords}:{gps_staleness}:{neighbours}:{shortest_path}"
    hb_bytes = hb_msg.encode()
    hb_data = ubinascii.b2a_base64(hb_bytes).decode().strip()
    
    epoch_ms = time.ticks_ms()
    payload = {
        "machine_id": MACHINE_ID,
        "message_type": "heartbeat",
        "heartbeat_data": hb_data,
        "epoch_ms": epoch_ms
    }
    return ujson.dumps(payload) + "\n"

def create_event_text_data():
    """Create dummy event text data"""
    epoch_ms = time.ticks_ms()
    gps_coords = "28.6139,77.2090"
    gps_staleness = 30
    
    # Format: machine_id:epoch_ms:gps:gps_staleness
    event_msg = f"{MACHINE_ID}:{epoch_ms}:{gps_coords}:{gps_staleness}"
    event_bytes = event_msg.encode()
    event_data = ubinascii.b2a_base64(event_bytes).decode().strip()
    
    payload = {
        "machine_id": MACHINE_ID,
        "message_type": "event_text",
        "event_data": event_data,
        "epoch_ms": epoch_ms
    }
    return ujson.dumps(payload) + "\n"

def create_image_data():
    """Capture and encode image from OpenMV camera"""
    epoch_ms = time.ticks_ms()
    
    try:
        # Capture image from camera
        img = sensor.snapshot()
        
        # Get image bytes
        img_bytes = img.bytearray()
        
        print(f"[IMG] Captured image, size: {len(img_bytes)} bytes")
        
        # Base64 encode image data
        img_data = ubinascii.b2a_base64(img_bytes).decode().strip()
        
        # Clean up image object
        del img
        
        payload = {
            "machine_id": MACHINE_ID,
            "message_type": "event",
            "image": img_data,
            "epoch_ms": epoch_ms
        }
        return ujson.dumps(payload) + "\n"
    except Exception as e:
        print(f"[IMG] Error capturing image: {e}")
        # Fallback to dummy data if capture fails
        dummy_image = b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000
        img_data = ubinascii.b2a_base64(dummy_image).decode().strip()
        payload = {
            "machine_id": MACHINE_ID,
            "message_type": "event",
            "image": img_data,
            "epoch_ms": epoch_ms
        }
        return ujson.dumps(payload) + "\n"

def main():
    """Main function"""
    sock = None
    
    try:
        # Initialize camera sensor
        sensor.reset()
        sensor.set_pixformat(sensor.RGB565)
        sensor.set_framesize(sensor.QVGA)  # 320x240
        sensor.skip_frames(time=2000)  # Let camera adjust
        print("Camera initialized")
        
        wlan = connect_wifi(WIFI_SSID, WIFI_PASSWORD)
        sock = create_persistent_connection(LAPTOP_IP, LAPTOP_PORT)
        
        if sock is None:
            print("Failed to establish connection. Exiting.")
            return
        
        print("\nConnection established. Starting data transmission...\n")
        
        counter = 0
        while True:
            # Rotate between heartbeat, event_text, and image
            msg_type = counter % 3
            
            if msg_type == 0:
                # Send heartbeat
                data = create_heartbeat_data()
                print(f"[HB] Sending heartbeat #{counter // 3}")
            elif msg_type == 1:
                # Send event text
                data = create_event_text_data()
                print(f"[TXT] Sending event text #{counter // 3}")
            else:
                # Send image
                data = create_image_data()
                print(f"[IMG] Sending image #{counter // 3}")
            
            success, sock = send_data_persistent(sock, data)
            
            if not success:
                print("\nConnection lost. Attempting to reconnect...")
                sock = create_persistent_connection(LAPTOP_IP, LAPTOP_PORT)
                if sock is None:
                    print("Reconnection failed. Retrying in 5 seconds...")
                    time.sleep(5)
                    continue
                print("Reconnected successfully!\n")
            
            counter += 1
            time.sleep(2)  # Send every 2 seconds

    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        if sock:
            try:
                sock.close()
                print("Connection closed.")
            except:
                pass

if __name__ == "__main__":
    main()
