import os
import sys
import time
import network
import ujson as json  # MicroPython uses 'ujson' for JSON operations

# Try different HTTP libraries based on what's available
try:
    import requests as http_lib

    print("Using 'requests' library")
except ImportError:
    try:
        import urequests as http_lib

        print("Using 'urequests' library")
    except ImportError:
        print("Error: No HTTP library available. Using socket implementation.")
        http_lib = None

VYOM_ROOT_DIR = "/vyom/vyomcloudbridge"

# The full path to the machine configuration file.
MACHINE_CONFIG_FILE = f"{VYOM_ROOT_DIR}/machine_config.json"


# --- API Configuration ---
BASE_API_URL = "https://api.vyomiq.io"
MACHINE_REGISTER_API_URL = f"{BASE_API_URL}/device/register/watchmen/"

# Organization ID for watchmen devices.
WATCHMEN_ORGANIZATION_ID = 20

# AWS IoT endpoint and S3 bucket name.
AWS_IOT_ENDPOINT = "a1k0jxthwpkkce-ats.iot.ap-south-1.amazonaws.com"
S3_BUCKET_NAME = "vyomos"

# Device UID and Device Name.
DEVICE_UID = "watchmen-device-01"
DEVICE_NAME = "Watchmen Device MicroPython"

# --- Wi-Fi Configuration ---
# TODO: IMPORTANT: Replace with your network credentials
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_KEY = "YOUR_WIFI_PASSWORD"


def connect_wifi(ssid=None, password=None, timeout=30):
    """
    Connect to WiFi network.

    Args:
        ssid (str): WiFi network name. If None, uses WIFI_SSID from constants
        password (str): WiFi password. If None, uses WIFI_KEY from constants
        timeout (int): Connection timeout in seconds

    Returns:
        bool: True if connected successfully, False otherwise
    """
    if ssid is None:
        ssid = WIFI_SSID
    if password is None:
        password = WIFI_KEY

    if ssid == "YOUR_WIFI_SSID" or password == "YOUR_WIFI_PASSWORD":
        print(
            "Error: Please update WIFI_SSID and WIFI_KEY in the script with your actual WiFi credentials!"
        )
        return False

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print(f"Already connected to WiFi. IP: {wlan.ifconfig()[0]}")
        return True

    print(f'Connecting to WiFi network "{ssid}"...')
    wlan.connect(ssid, password)

    # Wait for connection
    start_time = time.time()
    while not wlan.isconnected() and (time.time() - start_time) < timeout:
        time.sleep_ms(500)
        print(".", end="")

    print()  # New line after dots

    if wlan.isconnected():
        ip_info = wlan.ifconfig()
        print(f"WiFi Connected! IP: {ip_info[0]}, Gateway: {ip_info[2]}")
        return True
    else:
        print(f"Failed to connect to WiFi within {timeout} seconds")
        print("Please check your WiFi credentials and network availability")
        return False


def socket_post_request(url, data, headers=None):
    """
    Make a POST request using raw sockets when HTTP libraries aren't available.
    This is a fallback implementation for OpenMV.
    """
    import socket
    import ssl

    if headers is None:
        headers = {}

    try:
        # Parse URL
        if url.startswith("https://"):
            protocol = "https"
            url = url[8:]
            port = 443
            use_ssl = True
        elif url.startswith("http://"):
            protocol = "http"
            url = url[7:]
            port = 80
            use_ssl = False
        else:
            raise ValueError("URL must start with http:// or https://")

        # Split host and path
        if "/" in url:
            host, path = url.split("/", 1)
            path = "/" + path
        else:
            host = url
            path = "/"

        # Handle port in host
        if ":" in host:
            host, port_str = host.split(":")
            port = int(port_str)

        print(f"Connecting to {host}:{port} via {protocol}")

        # Convert data to JSON string
        json_data = json.dumps(data)

        # Build HTTP request
        request_lines = [
            f"POST {path} HTTP/1.1",
            f"Host: {host}",
            "Content-Type: application/json",
            f"Content-Length: {len(json_data)}",
            "Connection: close",
            "User-Agent: OpenMV-Watchmen/1.0",
        ]

        # Add custom headers
        for key, value in headers.items():
            if key.lower() not in ["host", "content-length", "connection"]:
                request_lines.append(f"{key}: {value}")

        request_lines.append("")  # Empty line before body
        request_lines.append(json_data)

        request = "\r\n".join(request_lines)

        # Create socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(30)  # 30 second timeout

        try:
            # Resolve hostname
            try:
                addr_info = socket.getaddrinfo(host, port)
                ip_addr = addr_info[0][-1][0]
                print(f"Resolved {host} to {ip_addr}")
            except Exception as e:
                print(f"DNS resolution failed for {host}: {e}")
                raise

            # Connect
            print("Establishing connection...")
            s.connect((ip_addr, port))
            print("Connected to server")

            # Wrap with SSL if needed
            if use_ssl:
                print("Starting SSL handshake...")
                s = ssl.wrap_socket(s)
                print("SSL connection established")

            # Send request
            print("Sending HTTP request...")
            s.send(request.encode())
            print("Request sent, waiting for response...")

            # Read response
            response = b""
            while True:
                try:
                    chunk = s.recv(1024)
                    if not chunk:
                        break
                    response += chunk
                    # For simple responses, break after getting headers + some body
                    if len(response) > 4096:  # Reasonable limit
                        break
                except:
                    break

            response_str = response.decode("utf-8", errors="ignore")
            print(f"Received response ({len(response)} bytes)")

            # Parse response
            if not response_str:
                raise Exception("Empty response received")

            lines = response_str.split("\r\n")
            if not lines:
                raise Exception("Invalid response format")

            status_line = lines[0]
            print(f"Status line: {status_line}")

            # Extract status code
            try:
                status_code = int(status_line.split()[1])
            except (IndexError, ValueError):
                raise Exception(f"Invalid status line: {status_line}")

            # Find body
            body_start = response_str.find("\r\n\r\n")
            if body_start != -1:
                body = response_str[body_start + 4 :]
                try:
                    response_data = json.loads(body) if body.strip() else {}
                except:
                    response_data = {"text": body}
            else:
                response_data = {}

            # Create response object similar to requests
            class SocketResponse:
                def __init__(self, status_code, data):
                    self.status_code = status_code
                    self.data = data

                def json(self):
                    return self.data

                def close(self):
                    pass

            return SocketResponse(status_code, response_data)

        finally:
            try:
                s.close()
            except:
                pass

    except Exception as e:
        print(f"Socket request failed: {e}")
        raise


def register_machine():
    """
    Register a watchmen device with VyomIQ using MicroPython libraries.

    Returns:
        tuple: (success: bool, error: str)
    """
    print("\n=== Watchmen Device Registration (MicroPython) ===\n")

    # Check if config file already exists
    try:
        # In MicroPython, os.stat is a reliable way to check for file existence.
        os.stat(MACHINE_CONFIG_FILE)
        config_exists = True
    except OSError:
        config_exists = False

    if config_exists:
        print(f"Configuration file already exists at: {MACHINE_CONFIG_FILE}")
        try:
            # Read existing configuration
            with open(MACHINE_CONFIG_FILE, "r") as f:
                config = json.load(f)

            machine_info = config.get("MACHINE")
            if machine_info:
                machine_id = machine_info.get("machine_id", "Unknown")
                machine_uid = machine_info.get("machine_uid", "Unknown")
                machine_name = machine_info.get("machine_name", "Unknown")

                print("\n--- Existing Device Details ---")
                print(f"Machine ID: {machine_id}")
                print(f"Machine UID: {machine_uid}")
                print(f"Machine Name: {machine_name}")

                print("Device already registered. Skipping registration.")
                return True, ""
            else:
                print(
                    "Warning: Configuration file exists but appears to be invalid. Re-registering..."
                )
        except Exception as e:
            print(f"Error reading configuration file: {str(e)}")
            print("Re-registering...")
    else:
        print("No configuration file found. Starting registration...")

    # Connect to WiFi first
    print("\n--- Connecting to WiFi ---")
    if not connect_wifi():
        return (
            False,
            "Failed to connect to WiFi. Please check your network credentials.",
        )

    # Create payload JSON
    payload = {
        "name": DEVICE_NAME,
        "machine_uid": DEVICE_UID,
        "organization_id": WATCHMEN_ORGANIZATION_ID,
    }

    print(f"Registration payload: {payload}")

    # Make API call to register device
    print(f"\nRegistering device with VyomIQ at: {MACHINE_REGISTER_API_URL}")
    response = None
    try:
        # Try different HTTP libraries
        if http_lib:
            print("Using HTTP library for request...")
            response = http_lib.post(
                MACHINE_REGISTER_API_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response_data = response.json()
            status_code = response.status_code
        else:
            # Fallback to socket implementation
            print("Using socket fallback for HTTP request...")
            response = socket_post_request(
                MACHINE_REGISTER_API_URL, payload, {"Content-Type": "application/json"}
            )
            response_data = response.json()
            status_code = response.status_code

        print(f"Received HTTP status: {status_code}")
        print(f"Response data: {response_data}")

        # Check response
        if status_code == 200:
            if response_data.get("status") == 200:
                print("Device registration successful!")

                # Create directory if it doesn't exist.
                # os.makedirs is not in MicroPython, so we create one level.
                try:
                    os.mkdir(VYOM_ROOT_DIR)
                except OSError as e:
                    # Error code 17 means directory already exists, which is fine.
                    if e.args[0] != 17:
                        raise

                # Prepare configuration data using a standard Python dictionary
                config_data = {}
                machine_data = response_data.get("data", {})
                config_data["MACHINE"] = {
                    "machine_id": str(machine_data.get("id", "")),
                    "machine_uid": machine_data.get("machine_uid", ""),
                    "machine_name": machine_data.get("name", ""),
                    "machine_model_id": str(machine_data.get("machine_model", "")),
                    "machine_model_name": machine_data.get("machine_model_name", ""),
                    "machine_model_type": machine_data.get("machine_model_type", ""),
                    "organization_id": str(machine_data.get("current_owner", "")),
                    "organization_name": machine_data.get("current_owner_name", ""),
                    "created_at": machine_data.get("created_at", ""),
                    "updated_at": machine_data.get("updated_at", ""),
                    "session_id": machine_data.get("session_id", ""),
                }

                # Save IoT credentials if present
                if "iot_data" in machine_data:
                    iot_data = machine_data["iot_data"]
                    config_data["IOT"] = {
                        "thing_name": iot_data.get("thing_name"),
                        "thing_arn": iot_data.get("thing_arn"),
                        "policy_name": iot_data.get("policy_name"),
                        "certificate": iot_data.get("certificate", {}).get(
                            "certificatePem"
                        ),
                        "private_key": iot_data.get("certificate", {})
                        .get("keyPair", {})
                        .get("PrivateKey"),
                        "public_key": iot_data.get("certificate", {})
                        .get("keyPair", {})
                        .get("PublicKey"),
                        "root_ca": iot_data.get("root_ca"),
                    }

                # Save configuration as a JSON file
                with open(MACHINE_CONFIG_FILE, "w") as f:
                    json.dump(config_data, f)

                print(f"Configuration saved to {MACHINE_CONFIG_FILE}")
                print(f"Device Model ID: {machine_data.get('machine_model', 'N/A')}")

                return True, ""
            else:
                error_msg = (
                    f"Registration failed with status: {response_data.get('status')}"
                )
                print(f"Error: {error_msg}")
                print(f"Response: {response_data}")
                return False, error_msg
        else:
            error_msg = f"HTTP error {status_code}"
            if response_data:
                error_msg += f": {response_data}"
            print(f"Error: {error_msg}")
            return False, error_msg

    except OSError as e:
        # OSError is the common exception for network errors in MicroPython
        error_msg = f"Network or File I/O error during registration: {e}"
        print(f"Error: {error_msg}")
        print("Common causes:")
        print("- WiFi not connected or unstable")
        print("- DNS resolution failure")
        print("- Server unreachable")
        print("- SSL/TLS handshake failure")
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error during registration: {str(e)}"
        print(f"Error: {error_msg}")
        return False, error_msg
    finally:
        # Ensure the response is closed to free up memory
        if response and hasattr(response, "close"):
            response.close()


def setup():
    """
    Perform the minimal Watchmen device setup process.

    Returns:
        bool: True if setup completed successfully, False otherwise
    """
    print("\n=== Starting Watchmen Device Setup (MicroPython) ===\n")

    # Test WiFi credentials first
    if WIFI_SSID == "YOUR_WIFI_SSID" or WIFI_KEY == "YOUR_WIFI_PASSWORD":
        print("ERROR: Please update the WiFi credentials at the top of this script!")
        print("Current values:")
        print(f'WIFI_SSID = "{WIFI_SSID}"')
        print(f'WIFI_KEY = "{WIFI_KEY}"')
        print("\nPlease change these to your actual WiFi network name and password.")
        return False

    # Register the device
    registration_success, error = register_machine()
    if not registration_success:
        print(f"Device registration failed: {error}")
        return False

    print("\n=== Watchmen Device Setup Completed Successfully ===")
    print(f"Configuration saved to: {MACHINE_CONFIG_FILE}")
    return True


if __name__ == "__main__":
    success = setup()

    # Exit with appropriate status code
    if not success:
        print("Setup failed. Exiting.")
        sys.exit(1)
    else:
        print("Setup successful.")
