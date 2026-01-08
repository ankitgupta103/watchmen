import time
from machine import UART

# Configuration
UART_ID = 1              # UART port on OpenMV
BAUDRATE = 115200        # EC200U module baud rate

uart = UART(UART_ID, BAUDRATE, timeout=2000)


def send_at(cmd, wait_ms=1000):
    """Send AT command to module and return response."""
    uart.write((cmd + "\r\n").encode())
    end = time.ticks_ms() + wait_ms
    resp = b""
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        if uart.any():
            resp += uart.read()
        time.sleep_ms(10)
    return resp


def check_response(resp, expected="OK"):
    """Check if response contains expected string."""
    return expected.encode() in resp


def connect_internet():
    """Connect to internet using EC200U module."""
    print("Initializing EC200U module...")
    time.sleep_ms(2000)  # Wait for module to initialize
    
    # Test AT command
    if not check_response(send_at("AT", 500)):
        print("ERROR: No AT response!")
        return False
    print("Module responding...")
    
    # Disable echo
    send_at("ATE0", 500)
    
    # Check network registration
    print("Checking network registration...")
    resp = send_at("AT+CREG?", 2000)
    if b"+CREG:" in resp:
        try:
            print("Network status:", resp.decode("ascii").strip())
        except:
            print("Network status:", resp)
    
    # Check PDP context status first
    print("Checking PDP context status...")
    resp = send_at("AT+QIACT?", 2000)
    already_connected = False
    try:
        text = resp.decode("ascii")
        if "+QIACT:" in text:
            # Check if context 1 is already active
            if "1,1" in text or ",1," in text:
                already_connected = True
                print("PDP context already active!")
    except:
        pass
    
    # Activate PDP context if not already connected
    if not already_connected:
        print("Activating internet connection...")
        resp = send_at("AT+QIACT=1", 5000)
        if check_response(resp):
            print("Internet connected!")
            return True
        else:
            try:
                print("Connection failed:", resp.decode("ascii").strip())
            except:
                print("Connection failed:", resp)
            return False
    else:
        print("Internet already connected!")
        return True


def format_speed(bytes_per_sec):
    """Format speed in readable format (KB/s or MB/s)."""
    if bytes_per_sec >= 1024 * 1024:
        return "%.2f MB/s" % (bytes_per_sec / (1024 * 1024))
    else:
        return "%.2f KB/s" % (bytes_per_sec / 1024)


def speed_test(url, expected_size_kb=10):
    """Test download speed by downloading a file."""
    print(f"\nTesting download speed...")
    print(f"URL: {url}")
    
    # Configure HTTP
    send_at('AT+QHTTPCFG="contextid",1', 1000)
    send_at('AT+QHTTPCFG="requestheader",0', 1000)
    
    # Set URL
    print("Setting URL...")
    url_len = len(url)
    uart.write(f'AT+QHTTPURL={url_len},80\r\n'.encode())
    
    # Wait for CONNECT prompt
    end = time.ticks_ms() + 3000
    got_prompt = False
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        if uart.any():
            data = uart.read()
            if b"CONNECT" in data:
                got_prompt = True
                break
        time.sleep_ms(10)
    
    if not got_prompt:
        print("Failed to get CONNECT prompt!")
        return None
    
    # Send URL data
    time.sleep_ms(100)
    uart.write(url.encode())
    time.sleep_ms(500)
    
    # Wait for OK response
    end = time.ticks_ms() + 2000
    url_set = False
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        if uart.any():
            data = uart.read()
            if b"OK" in data:
                url_set = True
                break
        time.sleep_ms(10)
    
    if not url_set:
        print("Failed to set URL!")
        return None
    
    # Start download and measure time
    print("Downloading...")
    start_time = time.ticks_ms()
    resp = send_at("AT+QHTTPGET=80", 20000)  # 20 second timeout
    end_time = time.ticks_ms()
    
    # Check HTTP status
    http_status = None
    try:
        text = resp.decode("ascii")
        if "+QHTTPGET:" in text:
            for line in text.split("\n"):
                if "+QHTTPGET:" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        try:
                            http_status = int(parts[1].strip().split(",")[0])
                            print(f"HTTP Status: {http_status}")
                        except:
                            pass
    except:
        pass
    
    if not check_response(resp) or (http_status and http_status != 200):
        print("Download failed!")
        try:
            print(resp.decode("ascii"))
        except:
            print(resp)
        return None
    
    # Read data to get actual size
    print("Reading data...")
    read_resp = send_at("AT+QHTTPREAD=80", 10000)
    
    # Calculate elapsed time
    elapsed_sec = (time.ticks_diff(end_time, start_time)) / 1000.0
    
    # Try to extract actual size from response
    actual_size = None
    try:
        text = read_resp.decode("ascii")
        if "+QHTTPREAD:" in text:
            for line in text.split("\n"):
                if "+QHTTPREAD:" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        try:
                            # Format: +QHTTPREAD: <actual_read_length>
                            size_str = parts[1].strip().split(",")[0]
                            actual_size = int(size_str)
                            break
                        except:
                            pass
    except:
        pass
    
    # Calculate speed
    if actual_size and actual_size > 0:
        speed = actual_size / elapsed_sec
        print(f"\nDownloaded: {actual_size} bytes in {elapsed_sec:.2f} seconds")
        print(f"Speed: {format_speed(speed)}")
        return speed
    elif elapsed_sec > 0:
        # Fallback: use expected size
        estimated_size = expected_size_kb * 1024
        speed = estimated_size / elapsed_sec
        print(f"\nTime: {elapsed_sec:.2f} seconds")
        print(f"Estimated speed: {format_speed(speed)} (based on {expected_size_kb}KB)")
        print("Note: Could not read actual data size, using estimate")
        return speed
    
    return None


def main():
    """Main function to run speed test."""
    print("=" * 40)
    print("EC200U Internet Speed Test")
    print("=" * 40)
    
    # Connect to internet
    if not connect_internet():
        print("Failed to connect. Exiting.")
        return
    
    # Test with a small file first (1KB) for quick test
    print("\n--- Quick Test (1KB) ---")
    speed = speed_test("http://httpbin.org/bytes/1024", expected_size_kb=1)
    
    if speed:
        print("\n--- Larger Test (10KB) ---")
        speed = speed_test("http://httpbin.org/bytes/10240", expected_size_kb=10)
        print("\nSpeed test completed!")
    else:
        print("\nSpeed test failed!")


if __name__ == "__main__":
    main()

