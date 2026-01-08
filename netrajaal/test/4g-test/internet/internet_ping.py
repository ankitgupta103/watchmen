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
    
    # Activate PDP context (connect to internet)
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


def ping(host="8.8.8.8", count=4):
    """Ping a host using AT+QPING command."""
    print(f"\nPinging {host}...")
    
    # AT+QPING=<context_id>,<host>,<ping_count>,<timeout>
    cmd = f'AT+QPING=1,"{host}",{count},5'
    resp = send_at(cmd, 10000)
    
    # Parse ping response
    try:
        text = resp.decode("ascii")
        print("Ping response:")
        print(text)
        
        # Check for ping results
        if "+QPING:" in text:
            lines = text.split("\n")
            for line in lines:
                if "+QPING:" in line:
                    print(line.strip())
    except:
        print("Raw response:", resp)
    
    return resp


def main():
    """Main function to connect and ping."""
    print("=" * 40)
    print("EC200U Internet Connection & Ping Test")
    print("=" * 40)
    
    # Connect to internet
    if not connect_internet():
        print("Failed to connect. Exiting.")
        return
    
    # Ping Google DNS
    ping("8.8.8.8", count=4)
    
    # Ping another host
    time.sleep(2)
    ping("google.com", count=2)
    
    print("\nTest completed!")


if __name__ == "__main__":
    main()

