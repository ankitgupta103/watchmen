import os
import time
import network
import ujson as json
from mqtt import MQTTClient
import ssl

# Configuration - move these to constants.py
WIFI_SSID = "A"
WIFI_KEY = "123456789"
VYOM_ROOT_DIR = "/sdcard/image1"
MACHINE_CONFIG_FILE = f"{VYOM_ROOT_DIR}/machine_config.json"
WATCHMEN_ORGANIZATION_ID = 20
S3_BUCKET_NAME = "vyomos"
AWS_IOT_ENDPOINT = "a1k0jxthwpkkce-ats.iot.ap-south-1.amazonaws.com"


def file_exists(path):
    """Check if a file exists - MicroPython compatible."""
    try:
        os.stat(path)
        return True
    except OSError:
        return False


class VyomMqttClient:
    """
    Fixed MQTT client for OpenMV connecting to AWS IoT Core
    """

    def __init__(self, config_path=None):
        """Initialize the client by reading IoT configuration from config file."""
        self.client = None
        self.config_path = config_path or MACHINE_CONFIG_FILE
        self.config = self._load_config(self.config_path)

        if not self.config:
            raise Exception(f"Failed to load configuration file: {self.config_path}")

        # Extract IoT credentials
        iot_config = self.config.get("IOT", {})
        self.thing_arn = iot_config.get("thing_arn")
        self.thing_name = iot_config.get("thing_name")
        self.policy_name = iot_config.get("policy_name")

        # Certificate data will be loaded as binary DER format
        self.certificate = None
        self.private_key = None

        # Validate required credentials
        if not self.thing_name:
            raise Exception("Configuration missing required thing_name")

    def _load_config(self, path):
        """Load the JSON configuration file."""
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

    def _load_certificates_der(self):
        """
        Load DER format certificates for OpenMV compatibility.
        Certificates must be converted to DER format beforehand.
        """
        print("Loading DER format certificates...")
        try:
            # Load private key in DER format
            with open("private.der", "rb") as f:
                self.private_key = f.read()

            # Load certificate in DER format
            with open("certificate.der", "rb") as f:
                self.certificate = f.read()

            print("DER certificates loaded successfully.")
            return True
        except Exception as e:
            print(f"Error loading DER certificates: {e}")
            return False

    def connect(self, ssid=None, key=None, port=8883):
        """Connect to Wi-Fi and establish secure MQTT connection."""
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

        # 2. Load DER certificates
        if not self._load_certificates_der():
            return False

        # 3. Set up time synchronization (required for SSL)
        try:
            import ntptime

            ntptime.settime()
            print("Time synchronized via NTP")
        except Exception as e:
            print(f"Warning: NTP sync failed: {e}")

        # 4. Create and connect MQTT client with proper SSL params for OpenMV
        print(f"Connecting to MQTT broker at {AWS_IOT_ENDPOINT}...")
        try:
            # OpenMV compatible SSL parameters
            ssl_params = {
                "key": self.private_key,
                "cert": self.certificate,
                "server_hostname": AWS_IOT_ENDPOINT,
                "cert_reqs": ssl.CERT_REQUIRED,
            }

            self.client = MQTTClient(
                client_id=self.thing_name,
                server=AWS_IOT_ENDPOINT,
                port=port,
                ssl_params=ssl_params,
                keepalive=60,
            )

            self.client.connect()
            print("MQTT Connection Successful!")
            return True

        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            return False

    def publish_message(self, message, message_type, filename, machine_id=None):
        """Construct topic path and publish message."""
        if not self.client:
            print("Error: MQTT client is not connected.")
            return None

        if not all([message, message_type, filename]):
            print("Error: message, message_type, and filename are required.")
            return None

        # Use thing_name if machine_id not provided
        machine_id = machine_id or self.thing_name

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
        """Disconnect the client."""
        if self.client:
            try:
                self.client.disconnect()
                print("MQTT client disconnected.")
            except Exception as e:
                print(f"Error disconnecting MQTT client: {e}")


# Test function with fixes
def test_mqtt_client():
    """Test function to demonstrate MQTT client usage."""
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

                # Fixed: Use thing_name instead of machine_id
                published_topic = client.publish_message(
                    message=message_payload,
                    message_type=message_type,
                    filename=file_name,
                    machine_id=client.thing_name,  # Fixed attribute name
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


# Main execution
if __name__ == "__main__":
    print("=== MQTT Client Test ===")
    test_mqtt_client()
