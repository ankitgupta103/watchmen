import os
import time
import network
import ujson as json
import ubinascii

from mqtt import MQTTClient  # Your MQTT implementation

# Configuration
WIFI_SSID = "A"
WIFI_KEY = "123456789"
VYOM_ROOT_DIR = "/sdcard/image1"
MACHINE_CONFIG_FILE = f"{VYOM_ROOT_DIR}/machine_config.json"
WATCHMEN_ORGANIZATION_ID = 20
S3_BUCKET_NAME = "vyomos"
AWS_IOT_ENDPOINT = "a1k0jxthwpkkce-ats.iot.ap-south-1.amazonaws.com"

# Generated temp files
CERT_DER_FILE = "certificate.der"
KEY_DER_FILE = "private_key.der"
ROOT_CA_DER_FILE = "root_ca.der"


def file_exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def pem_to_der_str(pem_data):
    """Convert PEM string to DER bytes."""
    lines = pem_data.split("\n")
    b64 = "".join(
        line.strip() for line in lines if not line.startswith("---") and line.strip()
    )
    return ubinascii.a2b_base64(b64)


def write_der_file_from_pem_or_der(filename, data):
    """Write DER file from PEM or binary DER or ASCII PEM (for CA)."""
    if ("-----BEGIN" in data) and ("-----END" in data):
        # PEM conversion
        der_data = pem_to_der_str(data)
        with open(filename, "wb") as f:
            f.write(der_data)
    else:
        # For root CA this allows either DER or PEM, both as binary
        with open(filename, "wb") as f:
            try:
                f.write(data if isinstance(data, bytes) else data.encode())
            except Exception:
                f.write(data)


class VyomMqttClient:
    """
    MQTT client for OpenMV using credentials from config (auto PEM-to-DER conversion).
    """

    def __init__(self, config_path=None):
        self.client = None
        self.config_path = config_path or MACHINE_CONFIG_FILE
        self.config = self._load_config(self.config_path)
        if not self.config:
            raise Exception(
                f"Failed to load or parse configuration file: {self.config_path}"
            )

        iot = self.config.get("IOT", {})
        self.thing_arn = iot.get("thing_arn")
        self.thing_name = iot.get("thing_name")
        self.policy_name = iot.get("policy_name")
        self.certificate = iot.get("certificate")
        self.private_key = iot.get("private_key")
        self.root_ca = iot.get("root_ca")

        # Validate required credentials
        missing = []
        if not self.thing_name:
            missing.append("thing_name")
        if not self.certificate:
            missing.append("certificate")
        if not self.private_key:
            missing.append("private_key")
        if not self.root_ca:
            missing.append("root_ca")
        if missing:
            raise Exception("Missing IoT credentials in config: " + ", ".join(missing))

    def _load_config(self, path):
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

    def _prepare_certificate_files(self):
        # Always (over)write to DER files each run (safe; files are cleaned up on disconnect)
        try:
            write_der_file_from_pem_or_der(CERT_DER_FILE, self.certificate)
            write_der_file_from_pem_or_der(KEY_DER_FILE, self.private_key)
            write_der_file_from_pem_or_der(ROOT_CA_DER_FILE, self.root_ca)
            return True
        except Exception as e:
            print("Error writing DER files from PEM:", e)
            return False

    def connect(self, ssid=None, key=None, port=8883):
        ssid = ssid or WIFI_SSID
        key = key or WIFI_KEY

        # 1. Wi-Fi connect
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        if not wlan.isconnected():
            print(f'Connecting to Wi-Fi network "{ssid}"...')
            wlan.connect(ssid, key)
            timeout = 30
            start_time = time.time()
            while not wlan.isconnected() and (time.time() - start_time) < timeout:
                time.sleep_ms(500)
            if not wlan.isconnected():
                print("Failed to connect to Wi-Fi network.")
                return False
        print("Wi-Fi Connected. IP:", wlan.ifconfig()[0])

        # 2. Prepare DER files
        if not self._prepare_certificate_files():
            return False

        print(f"Connecting to MQTT broker at {AWS_IOT_ENDPOINT}...")
        try:
            self.client = MQTTClient(
                client_id=self.thing_name,
                server=AWS_IOT_ENDPOINT,
                port=port,
                ssl_params={
                    "key": open(KEY_DER_FILE, "rb").read(),
                    "cert": open(CERT_DER_FILE, "rb").read(),
                    "ca_certs": ROOT_CA_DER_FILE,
                },
            )
            self.client.connect()
            print("MQTT Connection Successful!")
            return True
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            return False

    def publish_message(self, message, message_type, filename, machine_id):
        if not self.client:
            print("Error: MQTT client is not connected.")
            return None
        if not all([message, message_type, filename, machine_id]):
            print("Error: All parameters are required.")
            return None
        try:
            year, month, day, *_ = time.localtime()
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
        """Disconnects MQTT and cleans up certificate files."""
        if self.client:
            try:
                self.client.disconnect()
                print("MQTT client disconnected.")
            except Exception as e:
                print(f"Error disconnecting MQTT client: {e}")
        # Clean up DER/CA files
        for fpath in [CERT_DER_FILE, KEY_DER_FILE, ROOT_CA_DER_FILE]:
            try:
                if file_exists(fpath):
                    os.remove(fpath)
                    print(f"Removed {fpath}")
            except OSError as e:
                print(f"Error removing {fpath}: {e}")


# --- Test Function ---


def test_mqtt_client():
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
                    machine_id=client.thing_name,
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
