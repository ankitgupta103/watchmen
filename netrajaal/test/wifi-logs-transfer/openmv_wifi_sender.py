import network
import socket
import time

WIFI_SSID = "A"
WIFI_PASSWORD = "123456789"

LAPTOP_IP = "10.42.0.1"     
LAPTOP_PORT = 5000  

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
    print("Subnet mask:", wlan.ifconfig()[1])
    print("Gateway:", wlan.ifconfig()[2])
    print("DNS:", wlan.ifconfig()[3])

    return wlan

def create_persistent_connection(host, port, max_retries=3):
    """Create and return a persistent TCP connection"""
    for attempt in range(max_retries):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)  # Connection timeout
            
            print(f"Connecting to {host}:{port}... (attempt {attempt + 1}/{max_retries})")
            sock.connect((host, port))
            print("Connected! Connection established and kept alive.")
            
            # Set socket options to keep connection alive
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            return sock
            
        except Exception as e:
            print(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry
            else:
                raise
    
    return None

def send_data_persistent(sock, data):
    """Send data over existing persistent connection"""
    try:
        # Check if socket is still valid
        if sock is None:
            return False, None
            
        # Encode data if needed
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Send data
        sock.sendall(data)
        print(f"Sent {len(data)} bytes")
        
        # Optionally receive acknowledgment
        try:
            sock.settimeout(1)  # Short timeout for ACK
            response = sock.recv(1024)
            if response:
                print("Response:", response.decode('utf-8'))
        except socket.timeout:
            # No response, that's okay
            pass
        except:
            pass
        finally:
            sock.settimeout(10)  # Reset timeout for next operation
        
        return True, sock
        
    except (OSError, socket.error) as e:
        error_code = getattr(e, 'errno', None)
        print(f"Error sending data: {e} (errno: {error_code})")
        # Connection likely broken, close socket
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

def main():
    """Main function"""
    sock = None
    
    try:
        # Connect to WiFi
        wlan = connect_wifi(WIFI_SSID, WIFI_PASSWORD)
        
        # Create persistent connection
        sock = create_persistent_connection(LAPTOP_IP, LAPTOP_PORT)
        
        if sock is None:
            print("Failed to establish connection. Exiting.")
            return
        
        print("\nConnection established. Starting data transmission...\n")
        
        counter = 0
        while True:
            timestamp = time.ticks_ms()
            data = f"Data packet #{counter}, Timestamp: {timestamp}, Status: OK\n"
            
            # Send data over persistent connection
            success, sock = send_data_persistent(sock, data)
            
            if not success:
                # Connection lost, try to reconnect
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
        # Clean up connection
        if sock:
            try:
                sock.close()
                print("Connection closed.")
            except:
                pass

if __name__ == "__main__":
    main()