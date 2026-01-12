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

def send_data(data, host, port):
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5 second timeout

        # Connect to laptop
        print(f"Connecting to {host}:{port}...")
        sock.connect((host, port))
        print("Connected!")

        # Send data
        if isinstance(data, str):
            data = data.encode('utf-8')

        sock.sendall(data)
        print(f"Sent {len(data)} bytes")

        # Optionally receive acknowledgment
        try:
            response = sock.recv(1024)
            print("Response:", response.decode('utf-8'))
        except:
            pass

        sock.close()
        return True

    except Exception as e:
        print(f"Error sending data: {e}")
        return False

def main():
    """Main function"""
    try:
        # Connect to WiFi
        wlan = connect_wifi(WIFI_SSID, WIFI_PASSWORD)

        counter = 0
        while True:
            timestamp = time.ticks_ms()
            data = f"Data packet #{counter}, Timestamp: {timestamp}, Status: OK\n"

            send_data(data, LAPTOP_IP, LAPTOP_PORT)

            counter += 1
            time.sleep(2)  # Send every 2 seconds

    except KeyboardInterrupt:
        print("Stopped by user")
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()
