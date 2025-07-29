# TODO - Important
# Note: This script is only for the MicroPython version of the Watchmen device.
# Update the constants below to match your setup.

import os
import sys
import time
import network
import ujson as json  # MicroPython uses 'ujson' for JSON operations

# Try different HTTP libraries
try:
    import requests as http_lib

    print("Using 'requests' library")
except ImportError:
    try:
        import urequests as http_lib

        print("Using 'urequests' library")
    except ImportError:
        print("Error: No HTTP library available.")
        sys.exit(1)

# Configuration
VYOM_ROOT_DIR = "/vyom/vyomcloudbridge"
MACHINE_CONFIG_FILE = f"{VYOM_ROOT_DIR}/machine_config.json"
FALLBACK_CONFIG_FILE = "machine_config.json"

# API Configuration
BASE_API_URL = "https://api.vyomiq.io"
MACHINE_REGISTER_API_URL = f"{BASE_API_URL}/device/register/watchmen/"
WATCHMEN_ORGANIZATION_ID = 20

# Device Configuration
DEVICE_UID = "watchmenOPENMV02"
DEVICE_NAME = "WatchmenMP03"

# Wi-Fi Configuration - UPDATE THESE!
WIFI_SSID = "A"
WIFI_KEY = "123456789"


def file_exists(path):
    """Check if a file exists - MicroPython compatible."""
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def create_directory_recursive(path):
    """Create directory recursively for MicroPython."""
    try:
        os.stat(path)
        return True
    except OSError:
        pass

    path_parts = path.strip("/").split("/")
    current_path = ""

    for part in path_parts:
        if part:
            current_path = current_path + "/" + part if current_path else "/" + part
            try:
                os.mkdir(current_path)
            except OSError as e:
                if e.args[0] != 17:  # Directory already exists
                    print(f"Warning: Could not create directory {current_path}")
                    return False
    return True


def connect_wifi(timeout=30):
    """Connect to WiFi network."""
    if WIFI_SSID == "YOUR_WIFI_SSID" or WIFI_KEY == "YOUR_WIFI_PASSWORD":
        print("Error: Please update WIFI_SSID and WIFI_KEY!")
        return False

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print(f"Already connected to WiFi. IP: {wlan.ifconfig()[0]}")
        return True

    print(f'Connecting to WiFi network "{WIFI_SSID}"...')
    wlan.connect(WIFI_SSID, WIFI_KEY)

    start_time = time.time()
    while not wlan.isconnected() and (time.time() - start_time) < timeout:
        time.sleep_ms(500)
        print(".", end="")

    print()

    if wlan.isconnected():
        ip_info = wlan.ifconfig()
        print(f"WiFi Connected! IP: {ip_info[0]}")
        return True
    else:
        print(f"Failed to connect to WiFi within {timeout} seconds")
        return False


def register_machine():
    """Register a watchmen device with VyomIQ."""
    print("\n=== Watchmen Device Registration ===\n")

    # Check if already registered
    config_file_to_use = None
    if file_exists(MACHINE_CONFIG_FILE):
        config_file_to_use = MACHINE_CONFIG_FILE
    elif file_exists(FALLBACK_CONFIG_FILE):
        config_file_to_use = FALLBACK_CONFIG_FILE

    if config_file_to_use:
        print(f"Configuration file exists at: {config_file_to_use}")
        try:
            with open(config_file_to_use, "r") as f:
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
                print(f"Config file path: {config_file_to_use}")
                return True, ""
            else:
                print(
                    "Warning: Configuration file exists but appears to be invalid. Re-registering..."
                )
        except Exception as e:
            print(f"Error reading config: {e}. Re-registering...")

    # Connect to WiFi
    print("Connecting to WiFi...")
    if not connect_wifi():
        return False, "Failed to connect to WiFi"

    # Registration payload
    payload = {
        "name": DEVICE_NAME,
        "machine_uid": DEVICE_UID,
        "organization_id": WATCHMEN_ORGANIZATION_ID,
    }

    print(f"Registering device: {DEVICE_NAME}")

    try:
        # Make API call
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "MicroPython-Watchmen/1.0",
        }

        json_payload = json.dumps(payload)
        response = http_lib.post(
            MACHINE_REGISTER_API_URL, data=json_payload, headers=headers
        )

        print(f"Response status: {response.status_code}")

        # Parse response
        try:
            response_data = response.json()
        except:
            print("Failed to parse JSON response")
            return False, "Invalid response format"

        if response.status_code == 200 and response_data.get("status") == 200:
            print("Registration successful!")

            # Prepare configuration
            machine_data = response_data.get("data", {})
            config_data = {
                "MACHINE": {
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
            }

            # Add IoT credentials if present
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

            # Print configuration (without indent parameter for ujson compatibility)
            print("\n=== DEVICE CONFIGURATION ===")
            print(json.dumps(config_data))
            print("=== END CONFIGURATION ===\n")

            # Save configuration
            config_saved = False
            if create_directory_recursive(VYOM_ROOT_DIR):
                try:
                    with open(MACHINE_CONFIG_FILE, "w") as f:
                        json.dump(config_data, f)
                    print(f"Configuration saved to {MACHINE_CONFIG_FILE}")
                    config_saved = True
                except OSError as e:
                    print(f"Failed to write to {MACHINE_CONFIG_FILE}: {e}")

            # Fallback location
            if not config_saved:
                try:
                    with open(FALLBACK_CONFIG_FILE, "w") as f:
                        json.dump(config_data, f)
                    print(f"Configuration saved to {FALLBACK_CONFIG_FILE}")
                    config_saved = True
                except OSError as e:
                    print(f"Failed to write to {FALLBACK_CONFIG_FILE}: {e}")

            if not config_saved:
                print("Warning: Could not save configuration to file.")
                print("Configuration printed above - copy manually if needed.")

            return True, ""

        else:
            error_msg = f"Registration failed: {response_data.get('error', {}).get('message', 'Unknown error')}"
            print(f"Error: {error_msg}")
            return False, error_msg

    except Exception as e:
        error_msg = f"Registration error: {str(e)}"
        print(f"Error: {error_msg}")
        return False, error_msg

    finally:
        if "response" in locals() and hasattr(response, "close"):
            try:
                response.close()
            except:
                pass


def setup():
    """Perform Watchmen device setup."""
    print("\n=== Starting Watchmen Device Setup ===\n")

    # Check WiFi credentials
    if WIFI_SSID == "YOUR_WIFI_SSID" or WIFI_KEY == "YOUR_WIFI_PASSWORD":
        print("ERROR: Please update WiFi credentials in the script!")
        print(f'WIFI_SSID = "{WIFI_SSID}"')
        print(f'WIFI_KEY = "{WIFI_KEY}"')
        return False

    # Register device
    success, error = register_machine()
    if not success:
        print(f"Registration failed: {error}")
        return False

    print("\n=== Setup Completed Successfully ===")
    return True


if __name__ == "__main__":
    success = setup()
    if not success:
        print("Setup failed.")
        sys.exit(1)
    else:
        print("Setup successful.")
