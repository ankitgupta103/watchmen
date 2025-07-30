# TODO - Important
# Note: This script is only for the MicroPython version of the Watchmen device.
# Update the constants in constants.py to match your setup.

import os
import time
import network
import ujson as json  # MicroPython uses 'ujson' for JSON operations
from mqtt import MQTTClient  # Assumes mqtt.py library is on the device

# TODO: Move to constants.py (Anand)
# Configuration
WIFI_SSID = "A"
WIFI_KEY = "123456789"
VYOM_ROOT_DIR = "/sdcard/image1"
MACHINE_CONFIG_FILE = f"{VYOM_ROOT_DIR}/machine_config.json"
WATCHMEN_ORGANIZATION_ID = 20
S3_BUCKET_NAME = "vyomos"
AWS_IOT_ENDPOINT = "a1k0jxthwpkkce-ats.iot.ap-south-1.amazonaws.com"

CERT_FILE = "cert.pem"
KEY_FILE = "key.pem"


def file_exists(path):
    """Check if a file exists - MicroPython compatible."""
    try:
        os.stat(path)
        return True
    except OSError:
        return False


class VyomMqttClient:
    """
    A wrapper for the MQTTClient to connect to AWS IoT Core using IoT credentials
    from the machine_config.json file.
    """

    def __init__(self, config_path=None):
        """
        Initializes the client by reading IoT configuration from config file.

        Args:
            config_path (str): The full path to the machine_config.json file.
                              Defaults to MACHINE_CONFIG_FILE from constants.

        Raises:
            Exception: If configuration file cannot be loaded or parsed,
                      or if required IoT credentials are missing.
        """
        self.client = None
        self.config_path = config_path or MACHINE_CONFIG_FILE
        self.config = self._load_config(self.config_path)

        if not self.config:
            raise Exception(
                f"Failed to load or parse configuration file: {self.config_path}"
            )

        # Extract only IoT credentials from config
        iot_config = self.config.get("IOT", {})
        self.thing_name = iot_config.get("thing_name")
        self.certificate = iot_config.get("certificate")
        self.private_key = iot_config.get("private_key")

        # Validate required credentials
        missing_credentials = []
        if not self.thing_name:
            missing_credentials.append("thing_name")
        if not self.certificate:
            missing_credentials.append("certificate")
        if not self.private_key:
            missing_credentials.append("private_key")

        if missing_credentials:
            raise Exception(
                f"Configuration is missing required IoT credentials: {', '.join(missing_credentials)}"
            )

    def _load_config(self, path):
        """
        Loads the JSON configuration file.

        Args:
            path (str): Path to the configuration file.

        Returns:
            dict: Parsed JSON configuration or None if loading fails.
        """
        print(f"Loading configuration from: {path}")
        try:
            with open(path, "r") as f:
                config = json.load(f)
                print("Configuration loaded successfully.")
                return config
        except OSError as e:
            print(f"Error: Could not read config file at {path}. {e}")
            return None
        except ValueError as e:
            print(f"Error: Could not parse JSON in config file at {path}. {e}")
            return None

    def _write_certs_to_files(self):
        """
        Writes the certificate and key from config to temporary files,
        which is required by the MQTT library.

        Returns:
            bool: True if certificates were written successfully, False otherwise.
        """
        print("Writing certificates to temporary files...")
        try:
            if not self.certificate or not self.private_key:
                raise Exception("Certificate or Private Key not found in config.")

            with open(CERT_FILE, "w") as f:
                f.write(self.certificate)
            with open(KEY_FILE, "w") as f:
                f.write(self.private_key)
            print("Certificates written successfully.")
            return True
        except Exception as e:
            print(f"Error writing certificates: {e}")
            return False

    def connect(self, ssid=None, key=None, port=8883):
        """
        Connects to Wi-Fi, syncs time, and establishes a secure MQTT connection.

        Args:
            ssid (str): The Wi-Fi network SSID. Defaults to WIFI_SSID from constants.
            key (str): The Wi-Fi network password. Defaults to WIFI_KEY from constants.
            port (int): The MQTT broker port (8883 for AWS IoT).

        Returns:
            bool: True if connection successful, False otherwise.
        """
        # Use default credentials if not provided
        ssid = ssid or WIFI_SSID
        key = key or WIFI_KEY

        # 1. Connect to Wi-Fi
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)

        if not wlan.isconnected():
            print(f'Connecting to Wi-Fi network "{ssid}"...')
            wlan.connect(ssid, key)

            # Wait for connection with timeout
            timeout = 30  # 30 seconds timeout
            start_time = time.time()
            while not wlan.isconnected() and (time.time() - start_time) < timeout:
                time.sleep_ms(500)

            if not wlan.isconnected():
                print("Failed to connect to Wi-Fi network.")
                return False

        print("Wi-Fi Connected. IP:", wlan.ifconfig()[0])

        # 2. Write certs to files
        if not self._write_certs_to_files():
            return False

        # 3. Instantiate and connect the MQTT client
        print(f"Connecting to MQTT broker at {AWS_IOT_ENDPOINT}...")
        try:
            # For OpenMV MicroPython, use the correct SSL syntax
            self.client = MQTTClient(
                client_id=self.thing_name,
                server=AWS_IOT_ENDPOINT,
                port=port,
                ssl=True,
                ssl_params={
                    "key": KEY_FILE,
                    "cert": CERT_FILE,
                }
            )
            self.client.connect()
            print("MQTT Connection Successful!")
            return True
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            return False

    def publish_message(self, message, message_type, filename, machine_id):
        """
        Constructs the topic path, publishes a message, and returns the topic.

        Args:
            message (str): The payload to publish.
            message_type (str): The type of message (e.g., 'image', 'log', 'event').
            filename (str): The name of the file associated with the message.
            machine_id (str): The machine ID for the topic.

        Returns:
            str: The full topic path the message was published to, or None on failure.
        """
        if not self.client:
            print("Error: MQTT client is not connected.")
            return None

        # Validate input parameters
        if not all([message, message_type, filename, machine_id]):
            print(
                "Error: All parameters (message, message_type, filename, machine_id) are required."
            )
            return None

        # Get current date in yyyy-mm-dd format
        # Note: The RTC should be synced for this to be accurate.
        # The OpenMV IDE often syncs the clock on connection.
        try:
            year, month, day, _, _, _, _, _ = time.localtime()
            date_str = f"{year:04d}-{month:02d}-{day:02d}"
        except Exception as e:
            print(f"Error getting current date: {e}")
            # Fallback to a default date if time is not available
            date_str = "1970-01-01"

        # Construct the topic
        topic = (
            f"{S3_BUCKET_NAME}/{WATCHMEN_ORGANIZATION_ID}/_all_/{date_str}/"
            f"{machine_id}/_all_/{message_type}/{filename}"
        )

        try:
            print(f"Publishing to topic: {topic}")
            self.client.publish(topic, message)
            print("Message published successfully.")
            return topic
        except Exception as e:
            print(f"Failed to publish message: {e}")
            return None

    def disconnect(self):
        """
        Disconnects the client and cleans up certificate files.
        """
        if self.client:
            try:
                self.client.disconnect()
                print("MQTT client disconnected.")
            except Exception as e:
                print(f"Error disconnecting MQTT client: {e}")

        # Clean up certificate files
        try:
            if file_exists(CERT_FILE):
                os.remove(CERT_FILE)
            if file_exists(KEY_FILE):
                os.remove(KEY_FILE)
            print("Cleaned up certificate files.")
        except OSError as e:
            print(f"Error cleaning up certificate files: {e}")


# --- Test Configuration ---
# Test device information - only machine data since IoT certs come from config
TEST_MACHINE_ID = "test_machine_123"


# --- Test Function ---
def test_mqtt_client():
    """
    Test function to demonstrate MQTT client usage.

    This function:
    1. Initializes the MQTT client with configuration
    2. Connects to Wi-Fi and MQTT broker
    3. Publishes test messages
    4. Cleans up connections and files
    """
    client = None
    try:
        # 1. Initialize the client with config path
        print("Initializing MQTT Client...")
        client = VyomMqttClient(config_path=MACHINE_CONFIG_FILE)

        # 2. Connect to Wi-Fi and the MQTT broker
        if client.connect():
            print("Connection successful. Starting message publishing...")

            # 3. Publish messages in a loop
            counter = 0
            while counter < 3:  # Limited to 3 messages for testing
                counter += 1
                message_payload = f"Hello from OpenMV! Test message number {counter}"

                # Example for publishing a log message
                message_type = "log"
                file_name = f"test_log_{counter}.txt"

                # Call the publish function with all required parameters
                published_topic = client.publish_message(
                    message=message_payload,
                    message_type=message_type,
                    filename=file_name,
                    machine_id=TEST_MACHINE_ID,
                )

                if published_topic:
                    print(f"Successfully published to: {published_topic}")
                else:
                    print("Failed to publish. Check connection.")

                print("-" * 20)
                time.sleep(2)  # Shorter delay for testing
        else:
            print("Failed to establish connection.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # 4. Clean up the connection and certificate files
        if client:
            client.disconnect()


# --- Main Execution ---
if __name__ == "__main__":
    print("=== MQTT Client Test ===")
    test_mqtt_client()
