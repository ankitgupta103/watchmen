import ujson as json
import network
import time
import os
from mqtt import MQTTClient  # Assumes mqtt.py library is on the device

# TODO: File paths for storing the certificates temporarily on the device's filesystem (Anand)
CERT_FILE = "/cert.pem"
KEY_FILE = "/key.pem"


class VyomMqttClient:
    """
    A wrapper for the MQTTClient to connect to AWS IoT Core using credentials
    from the machine_config.json file.
    """

    def __init__(self, config_path, aws_endpoint):
        """
        Initializes the client by reading configuration.

        Args:
            config_path (str): The full path to the machine_config.json file.
            aws_endpoint (str): The AWS IoT Core endpoint URL.
        """
        self.client = None
        self.config = self._load_config(config_path)
        if not self.config:
            raise Exception("Failed to load or parse configuration file.")

        self.aws_endpoint = aws_endpoint
        self.machine_id = self.config.get("MACHINE", {}).get("machine_id")
        self.org_id = self.config.get("MACHINE", {}).get("organization_id")
        self.thing_name = self.config.get("IOT", {}).get("thing_name")

        if not all([self.machine_id, self.org_id, self.thing_name]):
            raise Exception("Configuration is missing required MACHINE or IOT details.")

    def _load_config(self, path):
        """Loads the JSON configuration file."""
        print(f"Loading configuration from: {path}")
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (OSError, ValueError) as e:
            print(f"Error: Could not read or parse config file at {path}. {e}")
            return None

    def _write_certs_to_files(self):
        """
        Writes the certificate and key from config to temporary files,
        which is required by the MQTT library.
        """
        print("Writing certificates to temporary files...")
        try:
            iot_config = self.config.get("IOT", {})
            cert = iot_config.get("certificate")
            key = iot_config.get("private_key")

            if not cert or not key:
                raise Exception("Certificate or Private Key not found in config.")

            with open(CERT_FILE, "w") as f:
                f.write(cert)
            with open(KEY_FILE, "w") as f:
                f.write(key)
            print("Certificates written successfully.")
            return True
        except Exception as e:
            print(f"Error writing certificates: {e}")
            return False

    # TODO: Update this to use the actual internet connection logic. (Anand)
    def connect(self, ssid, key, port=8883):
        """
        Connects to Wi-Fi, syncs time, and establishes a secure MQTT connection.

        Args:
            ssid (str): The Wi-Fi network SSID.
            key (str): The Wi-Fi network password.
            port (int): The MQTT broker port (8883 for AWS IoT).
        """
        # 1. Connect to Wi-Fi
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        if not wlan.isconnected():
            print(f'Connecting to Wi-Fi network "{ssid}"...')
            wlan.connect(ssid, key)
            while not wlan.isconnected():
                time.sleep_ms(500)
        print("Wi-Fi Connected. IP:", wlan.ifconfig()[0])

        # 2. Write certs to files
        if not self._write_certs_to_files():
            return False

        # 3. Instantiate and connect the MQTT client
        print(f"Connecting to MQTT broker at {self.aws_endpoint}...")
        try:
            self.client = MQTTClient(
                client_id=self.thing_name,
                server=self.aws_endpoint,
                port=port,
                ssl=True,
                ssl_params={"certfile": CERT_FILE, "keyfile": KEY_FILE},
            )
            self.client.connect()
            print("MQTT Connection Successful!")
            return True
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            return False

    def publish_message(self, message, message_type, filename, s3_bucket):
        """
        Constructs the topic path, publishes a message, and returns the topic.

        Args:
            message (str): The payload to publish.
            message_type (str): The type of message (e.g., 'image', 'log').
            filename (str): The name of the file associated with the message.
            s3_bucket (str): The S3 bucket name for the topic.

        Returns:
            str: The full topic path the message was published to, or None on failure.
        """
        if not self.client:
            print("Error: MQTT client is not connected.")
            return None

        # Get current date in yyyy-mm-dd format
        # Note: The RTC should be synced for this to be accurate.
        # The OpenMV IDE often syncs the clock on connection.
        year, month, day, _, _, _, _, _ = time.localtime()
        date_str = f"{year:04d}-{month:02d}-{day:02d}"

        # Construct the topic
        topic = (
            f"{s3_bucket}/{self.org_id}/_all_/{date_str}/"
            f"{self.machine_id}/_all_/{message_type}/{filename}"
        )

        try:
            print(f"Publishing to topic: {topic}")
            self.client.publish(topic, message)
            print("Message published.")
            return topic
        except Exception as e:
            print(f"Failed to publish message: {e}")
            return None

    def disconnect(self):
        """Disconnects the client and cleans up certificate files."""
        if self.client:
            self.client.disconnect()
            print("MQTT client disconnected.")
        try:
            os.remove(CERT_FILE)
            os.remove(KEY_FILE)
            print("Cleaned up certificate files.")
        except OSError:
            print("Error cleaning up certificate files or files may not exist.")
            pass  # Files may not exist if creation failed
