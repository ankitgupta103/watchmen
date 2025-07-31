# Combined MQTT Client for OpenMV Camera with AWS IoT Core Support
# Includes umqtt.py and ussl.py implementations

import os
import time
import network
import ujson as json
import ubinascii
import socket
import struct
import select
import sys

# =============================================================================
# CONSTANTS
# =============================================================================

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

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def file_exists(path):
    """Check if file exists."""
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
    """Write DER file from PEM or binary DER data."""
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


# =============================================================================
# SSL MODULE (ussl.py implementation)
# =============================================================================

try:
    from micropython import const
except (ImportError, AttributeError):

    def const(x):
        return x


import ssl


def wrap_socket(sock, ssl_params={}):
    """Wrap socket with SSL."""
    keyfile = ssl_params.get("keyfile", None)
    certfile = ssl_params.get("certfile", None)
    cafile = ssl_params.get("cafile", None)
    cadata = ssl_params.get("cadata", None)
    ciphers = ssl_params.get("ciphers", None)
    verify = ssl_params.get("verify_mode", ssl.CERT_NONE)
    hostname = ssl_params.get("server_hostname", None)

    # Use MicroPython SSL to wrap socket
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    if hasattr(ctx, "set_default_verify_paths"):
        ctx.set_default_verify_paths()
    if hasattr(ctx, "check_hostname") and verify != ssl.CERT_REQUIRED:
        ctx.check_hostname = False

    ctx.verify_mode = verify

    if keyfile is not None and certfile is not None:
        ctx.load_cert_chain(certfile, keyfile)

    if ciphers is not None:
        ctx.set_ciphers(ciphers)

    if cafile is not None or cadata is not None:
        ctx.load_verify_locations(cafile=cafile, cadata=cadata)

    return ctx.wrap_socket(sock, server_hostname=hostname)


# =============================================================================
# MQTT MODULE (umqtt.py implementation)
# =============================================================================


class MQTTException(Exception):
    pass


class MQTTClient:
    def __init__(
        self,
        client_id,
        server,
        port,
        ssl_params,
        user=None,
        password=None,
        keepalive=0,
        callback=None,
    ):
        self.client_id = client_id
        self.server = server
        self.port = port
        self.ssl_params = ssl_params
        self.user = user
        self.pswd = password
        self.keepalive = keepalive
        self.cb = callback
        self.sock = None
        self.pid = 0
        self.lw_topic = None
        self.lw_msg = None
        self.lw_qos = 0
        self.lw_retain = False

    def _send_str(self, s):
        self.sock.write(struct.pack("!H", len(s)))
        self.sock.write(s)

    def _recv_len(self):
        n = 0
        sh = 0
        while 1:
            b = self.sock.read(1)[0]
            n |= (b & 0x7F) << sh
            if not b & 0x80:
                return n
            sh += 7

    def set_callback(self, f):
        self.cb = f

    def set_last_will(self, topic, msg, retain=False, qos=0):
        assert 0 <= qos <= 2
        assert topic
        self.lw_topic = topic
        self.lw_msg = msg
        self.lw_qos = qos
        self.lw_retain = retain

    def connect(self, clean_session=True, timeout=5.0):
        addr = socket.getaddrinfo(self.server, self.port)[0][-1]

        if self.sock is not None:
            self.sock.close()
            self.sock = None

        self.sock = socket.socket()
        self.sock.settimeout(timeout)

        if sys.implementation.name == "micropython":
            self.sock.connect(addr)
            self.sock = wrap_socket(self.sock, self.ssl_params)
        else:
            self.sock = wrap_socket(self.sock, self.ssl_params)
            self.sock.connect(addr)

        premsg = bytearray(b"\x10\0\0\0\0\0")
        msg = bytearray(b"\x04MQTT\x04\x02\0\0")

        sz = 10 + 2 + len(self.client_id)
        msg[6] = clean_session << 1
        if self.user is not None:
            sz += 2 + len(self.user) + 2 + len(self.pswd)
            msg[6] |= 0xC0
        if self.keepalive:
            assert self.keepalive < 65536
            msg[7] |= self.keepalive >> 8
            msg[8] |= self.keepalive & 0x00FF
        if self.lw_topic:
            sz += 2 + len(self.lw_topic) + 2 + len(self.lw_msg)
            msg[6] |= 0x4 | (self.lw_qos & 0x1) << 3 | (self.lw_qos & 0x2) << 3
            msg[6] |= self.lw_retain << 5

        i = 1
        while sz > 0x7F:
            premsg[i] = (sz & 0x7F) | 0x80
            sz >>= 7
            i += 1
        premsg[i] = sz

        self.sock.write(premsg[0 : i + 2])
        self.sock.write(msg)
        self._send_str(self.client_id)
        if self.lw_topic:
            self._send_str(self.lw_topic)
            self._send_str(self.lw_msg)
        if self.user is not None:
            self._send_str(self.user)
            self._send_str(self.pswd)
        resp = self.sock.read(4)
        assert resp[0] == 0x20 and resp[1] == 0x02
        if resp[3] != 0:
            raise MQTTException(resp[3])
        return resp[2] & 1

    def disconnect(self):
        self.sock.write(b"\xe0\0")
        self.sock.close()

    def ping(self):
        self.sock.write(b"\xc0\0")

    def publish(self, topic, msg, retain=False, qos=0):
        pkt = bytearray(b"\x30\0\0\0")
        pkt[0] |= qos << 1 | retain
        sz = 2 + len(topic) + len(msg)
        if qos > 0:
            sz += 2
        assert sz < 2097152
        i = 1
        while sz > 0x7F:
            pkt[i] = (sz & 0x7F) | 0x80
            sz >>= 7
            i += 1
        pkt[i] = sz
        self.sock.write(pkt[0 : i + 1])
        self._send_str(topic)
        if qos > 0:
            self.pid += 1
            pid = self.pid
            struct.pack_into("!H", pkt, 0, pid)
            self.sock.write(pkt[0:2])
        self.sock.write(msg)
        if qos == 1:
            while 1:
                op = self.wait_msg()
                if op == 0x40:
                    sz = self.sock.read(1)
                    assert sz == b"\x02"
                    rcv_pid = self.sock.read(2)
                    rcv_pid = rcv_pid[0] << 8 | rcv_pid[1]
                    if pid == rcv_pid:
                        return
        elif qos == 2:
            assert 0

    def subscribe(self, topic, qos=0):
        assert self.cb is not None, "Subscribe callback is not set"
        pkt = bytearray(b"\x82\0\0\0")
        self.pid += 1
        struct.pack_into("!BH", pkt, 1, 2 + 2 + len(topic) + 1, self.pid)
        self.sock.write(pkt)
        self._send_str(topic)
        self.sock.write(qos.to_bytes(1, "little"))
        while 1:
            op = self.wait_msg()
            if op == 0x90:
                resp = self.sock.read(4)
                assert resp[1] == pkt[2] and resp[2] == pkt[3]
                if resp[3] == 0x80:
                    raise MQTTException(resp[3])
                return

    def wait_msg(self):
        res = self.sock.read(1)
        if res is None or res == b"":
            return None
        if res == b"\xd0":  # PINGRESP
            sz = self.sock.read(1)[0]
            assert sz == 0
            return None
        op = res[0]
        if op & 0xF0 != 0x30:
            return op
        sz = self._recv_len()
        topic_len = self.sock.read(2)
        topic_len = (topic_len[0] << 8) | topic_len[1]
        topic = self.sock.read(topic_len)
        sz -= topic_len + 2
        if op & 6:
            pid = self.sock.read(2)
            pid = pid[0] << 8 | pid[1]
            sz -= 2
        msg = self.sock.read(sz)
        self.cb(topic, msg)
        if op & 6 == 2:
            pkt = bytearray(b"\x40\x02\0\0")
            struct.pack_into("!H", pkt, 2, pid)
            self.sock.write(pkt)
        elif op & 6 == 4:
            assert 0

    def check_msg(self):
        r, w, e = select.select([self.sock], [], [], 0.05)
        if len(r):
            return self.wait_msg()


# =============================================================================
# VYOM MQTT CLIENT CLASS
# =============================================================================


class VyomMqttClient:
    """
    MQTT client for OpenMV using credentials from config with AWS IoT Core support.
    Uses built-in umqtt and ussl implementations.
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
        """Load configuration from JSON file."""
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
        """Convert and write certificate files to DER format."""
        try:
            write_der_file_from_pem_or_der(CERT_DER_FILE, self.certificate)
            write_der_file_from_pem_or_der(KEY_DER_FILE, self.private_key)
            write_der_file_from_pem_or_der(ROOT_CA_DER_FILE, self.root_ca)
            print("Certificate files prepared successfully.")
            return True
        except Exception as e:
            print("Error writing DER files from PEM:", e)
            return False

    def connect(self, ssid=None, key=None, port=8883):
        """Connect to WiFi and MQTT broker."""
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
            # Create SSL parameters for AWS IoT Core
            ssl_params = {
                "keyfile": KEY_DER_FILE,
                "certfile": CERT_DER_FILE,
                "cafile": ROOT_CA_DER_FILE,
                "verify_mode": ssl.CERT_REQUIRED,
                "server_hostname": AWS_IOT_ENDPOINT,
            }

            self.client = MQTTClient(
                client_id=self.thing_name,
                server=AWS_IOT_ENDPOINT,
                port=port,
                ssl_params=ssl_params,
                keepalive=60,
            )

            self.client.connect(clean_session=True, timeout=10.0)
            print("MQTT Connection Successful!")
            return True
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            return False

    def publish_message(self, message, message_type, filename, machine_id):
        """Publish message to AWS IoT Core."""
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
            # Convert message to bytes if it's a string
            if isinstance(message, str):
                message = message.encode("utf-8")

            self.client.publish(topic, message, retain=False, qos=0)
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

        # Clean up DER files
        for fpath in [CERT_DER_FILE, KEY_DER_FILE, ROOT_CA_DER_FILE]:
            try:
                if file_exists(fpath):
                    os.remove(fpath)
                    print(f"Removed {fpath}")
            except OSError as e:
                print(f"Error removing {fpath}: {e}")


# =============================================================================
# TEST FUNCTION
# =============================================================================


def test_mqtt_client():
    """Test the MQTT client functionality."""
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

                print("-" * 50)
                time.sleep(2)
        else:
            print("Failed to establish connection.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if client:
            client.disconnect()


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    print("=== Combined MQTT Client Test for OpenMV ===")
    test_mqtt_client()
