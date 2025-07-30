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

# Only the Root CA needs to be written to a file
ROOT_CA_FILE = "root_ca.pem"


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
        self.thing_arn = iot_config.get("thing_arn")
        self.thing_name = iot_config.get("thing_name")
        self.policy_name = iot_config.get("policy_name")
        self.certificate = iot_config.get("certificate")
        self.private_key = iot_config.get("private_key")
        self.root_ca = iot_config.get("root_ca")

        # Validate required credentials
        missing_credentials = []
        if not self.thing_name:
            missing_credentials.append("thing_name")
        if not self.certificate:
            missing_credentials.append("certificate")
        if not self.private_key:
            missing_credentials.append("private_key")
        if not self.root_ca:
            missing_credentials.append("root_ca")

        if missing_credentials:
            raise Exception(
                f"Configuration is missing required IoT credentials: {', '.join(missing_credentials)}"
            )

    def _load_config(self, path):
        """
        Loads the JSON configuration file.
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

    def _write_ca_cert_to_file(self):
        """
        Writes the Root CA from config to a temporary file.
        """
        print("Writing Root CA certificate to file...")
        try:
            with open(ROOT_CA_FILE, "w") as f:
                f.write(self.root_ca)
            print("Root CA written successfully.")
            return True
        except Exception as e:
            print(f"Error writing Root CA certificate: {e}")
            return False

    def connect(self, ssid=None, key=None, port=8883):
        """
        Connects to Wi-Fi and establishes a secure MQTT connection.
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
            timeout = 30
            start_time = time.time()
            while not wlan.isconnected() and (time.time() - start_time) < timeout:
                time.sleep_ms(500)

            if not wlan.isconnected():
                print("Failed to connect to Wi-Fi network.")
                return False

        print("Wi-Fi Connected. IP:", wlan.ifconfig()[0])

        # 2. Write CA cert to file
        if not self._write_ca_cert_to_file():
            return False

        # 3. Instantiate and connect the MQTT client
        print(f"Connecting to MQTT broker at {AWS_IOT_ENDPOINT}...")
        try:
            self.client = MQTTClient(
                client_id=self.thing_name,
                server=AWS_IOT_ENDPOINT,
                port=port,
                ssl_params={
                    "key": self.private_key,  # Pass key content directly
                    "cert": self.certificate,  # Pass cert content directly
                    "ca_certs": ROOT_CA_FILE,  # Pass CA cert as a file path
                },
            )
            self.client.connect()
            print("MQTT Connection Successful!")
            return True
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            return False

    def publish_message(self, message, message_type, filename, machine_id):
        """
        Constructs the topic path and publishes a message.
        """
        if not self.client:
            print("Error: MQTT client is not connected.")
            return None

        if not all([message, message_type, filename, machine_id]):
            print("Error: All parameters are required.")
            return None

        try:
            year, month, day, _, _, _, _, _ = time.localtime()
            date_str = f"{year:04d}-{month:02d}-{day:02d}"
        except Exception as e:
            print(f"Error getting current date: {e}")
            date_str = "1970-01-01"

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
        Disconnects the client and cleans up the CA certificate file.
        """
        if self.client:
            try:
                self.client.disconnect()
                print("MQTT client disconnected.")
            except Exception as e:
                print(f"Error disconnecting MQTT client: {e}")

        # Clean up CA certificate file
        try:
            if file_exists(ROOT_CA_FILE):
                os.remove(ROOT_CA_FILE)
            print("Cleaned up certificate file.")
        except OSError as e:
            print(f"Error cleaning up certificate file: {e}")


# --- Test Function ---
def test_mqtt_client():
    """
    Test function to demonstrate MQTT client usage.
    """
    client = None
    try:
        print("Initializing MQTT Client...")
        client = VyomMqttClient(config_path=MACHINE_CONFIG_FILE)

        if client.connect():
            print("Connection successful. Starting message publishing...")
            counter = 0
            while counter < 3:
                counter += 1
                message_payload = f"Hello from OpenMV! Test message number {counter}"
                message_type = "log"
                file_name = f"test_log_{counter}.txt"

                published_topic = client.publish_message(
                    message=message_payload,
                    message_type=message_type,
                    filename=file_name,
                    machine_id=client.machine_id,
                )
                if published_topic:
                    print(f"Successfully published to: {published_topic}")
                else:
                    print("Failed to publish. Check connection.")
                print("-" * 20)
                time.sleep(2)
        else:
            print("Failed to establish connection.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if client:
            client.disconnect()


# --- Main Execution ---
if __name__ == "__main__":
    print("=== MQTT Client Test ===")
    test_mqtt_client()
