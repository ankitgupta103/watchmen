# Combined MQTT Client for OpenMV Camera with AWS IoT Core Support
# Fixed version with proper socket creation and SSL connection

import os
import time
import network
import ujson as json
import ubinascii
import socket
import struct
import select
import sys
import ntptime
import machine

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
MQTT_CLIENT_ID = "hqDev"

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
    # First, handle escaped newlines from JSON strings
    if "\\n" in pem_data:
        pem_data = pem_data.replace("\\n", "\n")

    # Split into lines and extract base64 content
    lines = pem_data.split("\n")
    b64 = "".join(
        line.strip() for line in lines if not line.startswith("---") and line.strip()
    )

    if not b64:
        raise ValueError("No base64 content found in PEM data")

    return ubinascii.a2b_base64(b64)


def write_der_file_from_pem_or_der(filename, data):
    """Write DER file from PEM or binary DER data."""
    print(f"Processing certificate data for {filename}")

    # Handle string data (from JSON config)
    if isinstance(data, str):
        # Check if it's PEM format
        if ("-----BEGIN" in data) and ("-----END" in data):
            print(f"Converting PEM to DER for {filename}")

            # Handle escaped newlines from JSON
            if "\\n" in data:
                print("Found escaped newlines, converting...")
                data = data.replace("\\n", "\n")

            # Convert PEM to DER
            try:
                der_data = pem_to_der_str(data)
                with open(filename, "wb") as f:
                    f.write(der_data)
                print(f"Successfully wrote DER file: {filename}")
                return
            except Exception as e:
                print(f"Error converting PEM to DER: {e}")
                raise
        else:
            # Assume it's already DER data as string, encode to bytes
            with open(filename, "wb") as f:
                f.write(data.encode("utf-8"))
            return

    # Handle binary data
    elif isinstance(data, bytes):
        # Check if it's PEM format in bytes
        if b"-----BEGIN" in data and b"-----END" in data:
            # Convert bytes PEM to string, then to DER
            pem_string = data.decode("utf-8")
            if "\\n" in pem_string:
                pem_string = pem_string.replace("\\n", "\n")
            der_data = pem_to_der_str(pem_string)
            with open(filename, "wb") as f:
                f.write(der_data)
        else:
            # Already DER data in bytes
            with open(filename, "wb") as f:
                f.write(data)
    else:
        raise ValueError(f"Unsupported data type for {filename}: {type(data)}")


def sync_time():
    """Synchronize time with NTP server."""
    print("Synchronizing time with NTP server...")
    try:
        # Try to sync with NTP server
        ntptime.settime()
        current_time = time.localtime()
        print(
            f"Time synchronized: {current_time[0]}-{current_time[1]:02d}-{current_time[2]:02d} "
            f"{current_time[3]:02d}:{current_time[4]:02d}:{current_time[5]:02d}"
        )
        return True
    except Exception as e:
        print(f"NTP sync failed: {e}")
        # Fallback: Set a reasonable time manually (2024-01-01 00:00:00)
        try:
            rtc = machine.RTC()
            rtc.datetime(
                (2024, 1, 1, 0, 0, 0, 0, 0)
            )  # (year, month, day, weekday, hour, minute, second, microsecond)
            print("Time set manually to 2024-01-01 00:00:00")
            return True
        except Exception as e2:
            print(f"Manual time set failed: {e2}")
            return False


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
    """Wrap socket with SSL for AWS IoT Core - MicroPython ussl approach."""
    keyfile = ssl_params.get("keyfile", None)
    certfile = ssl_params.get("certfile", None)
    cafile = ssl_params.get("cafile", None)
    hostname = ssl_params.get("server_hostname", None)

    # For MicroPython/AWS IoT Core, read certificate files as binary data
    try:
        # Read the certificate files as binary data
        with open(keyfile, "rb") as f:
            key_data = f.read()
        with open(certfile, "rb") as f:
            cert_data = f.read()
        with open(cafile, "rb") as f:
            ca_data = f.read()

        print(
            f"Loaded certificates: key={len(key_data)} bytes, cert={len(cert_data)} bytes, ca={len(ca_data)} bytes"
        )

        # MicroPython SSL parameters for AWS IoT Core (ussl approach)
        try:
            # Try MicroPython's ussl first (more compatible with embedded systems)
            import ussl

            ssl_context = {
                "key": key_data,
                "cert": cert_data,
                "cadata": ca_data,
                "server_side": False,
            }
            wrapped_sock = ussl.wrap_socket(sock, **ssl_context)
            print("SSL socket wrapped successfully with MicroPython ussl")
            return wrapped_sock

        except (ImportError, AttributeError, TypeError) as e:
            print(f"ussl approach failed ({e}), trying standard ssl...")
            # Fallback to standard ssl approach
            import ssl

            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.verify_mode = ssl.CERT_REQUIRED
            ctx.check_hostname = True
            ctx.load_cert_chain(certfile, keyfile)
            ctx.load_verify_locations(cafile=cafile)
            wrapped_sock = ctx.wrap_socket(sock, server_hostname=hostname)
            print("SSL socket wrapped successfully with standard ssl")
            return wrapped_sock

    except Exception as e:
        raise Exception(f"SSL wrapping failed: {e}")


# =============================================================================
# MQTT MODULE (umqtt.py implementation) - FIXED VERSION
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

    def _encode_str(self, s):
        return struct.pack("!H", len(s)) + s.encode()

    def _encode_length(self, x):
        # MQTT uses variable length encoding
        encoded = b""
        while True:
            byte = x % 128
            x //= 128
            if x > 0:
                byte |= 0x80
            encoded += bytes([byte])
            if x == 0:
                break
        return encoded

    def _send_str(self, s):
        self.sock.write(struct.pack("!H", len(s)))
        self.sock.write(s)

    def _recv_len(self):
        """Fixed version with proper error handling."""
        n = 0
        sh = 0
        while 1:
            try:
                data = self.sock.read(1)
                if not data or len(data) == 0:
                    raise MQTTException("Connection closed while reading length")
                b = data[0]
                n |= (b & 0x7F) << sh
                if not b & 0x80:
                    return n
                sh += 7
            except (IndexError, OSError) as e:
                raise MQTTException(f"Error reading length: {e}")

    def _safe_read(self, num_bytes):
        """Safely read the specified number of bytes with timeout handling."""
        try:
            data = self.sock.read(num_bytes)
            if not data:
                raise MQTTException(
                    f"Connection closed while reading {num_bytes} bytes"
                )
            if len(data) != num_bytes:
                # Try to read remaining bytes for partial reads
                remaining = num_bytes - len(data)
                print(
                    f"Partial read: got {len(data)}/{num_bytes} bytes, reading {remaining} more..."
                )
                additional_data = self.sock.read(remaining)
                if additional_data:
                    data += additional_data
                if len(data) != num_bytes:
                    raise MQTTException(
                        f"Expected {num_bytes} bytes, got {len(data)} bytes. Data: {data.hex() if data else 'None'}"
                    )
            return data
        except OSError as e:
            raise MQTTException(f"Socket read error: {e}")
        except Exception as e:
            raise MQTTException(f"Unexpected read error: {e}")

    def set_callback(self, f):
        self.cb = f

    def set_last_will(self, topic, msg, retain=False, qos=0):
        assert 0 <= qos <= 2
        assert topic
        self.lw_topic = topic
        self.lw_msg = msg
        self.lw_qos = qos
        self.lw_retain = retain

    def connect(self, clean_session=True, timeout=10.0):
        """Connect to MQTT broker with proper socket creation and SSL wrapping."""
        # Step 1: Resolve server address
        print(f"Resolving address for {self.server}:{self.port}")
        try:
            addr = socket.getaddrinfo(self.server, self.port)[0][-1]
            print(f"Resolved address: {addr}")
        except Exception as e:
            raise MQTTException(f"Failed to resolve address: {e}")

        # Step 2: Close existing socket if any
        if self.sock is not None:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

        # Step 3: Create socket and set timeout
        print("Creating socket...")
        try:
            self.sock = socket.socket()
            self.sock.settimeout(timeout)
            print("Socket created successfully")
        except Exception as e:
            raise MQTTException(f"Failed to create socket: {e}")

        # Step 4: Connect socket
        print(f"Connecting socket to {addr}...")
        try:
            self.sock.connect(addr)
            print("Socket connected successfully")
        except Exception as e:
            if self.sock:
                self.sock.close()
                self.sock = None
            raise MQTTException(f"Failed to connect socket: {e}")

        # Step 5: Wrap with SSL
        print("Wrapping socket with SSL...")
        print(
            f"SSL parameters: keyfile={self.ssl_params.get('keyfile')}, certfile={self.ssl_params.get('certfile')}, cafile={self.ssl_params.get('cafile')}"
        )
        try:
            self.sock = wrap_socket(self.sock, self.ssl_params)
            print("SSL wrapping successful - TLS handshake completed")
            # Verify SSL connection details if possible
            try:
                if hasattr(self.sock, "cipher"):
                    print(f"SSL cipher: {self.sock.cipher()}")
            except:
                pass
            # Small delay to ensure SSL connection is fully established
            time.sleep(2)
        except Exception as e:
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
                self.sock = None
            raise MQTTException(f"Failed to wrap socket with SSL: {e}")

        # Step 6: Send MQTT CONNECT packet
        print("Sending MQTT CONNECT packet...")
        try:
            # Build MQTT CONNECT packet for AWS IoT Core
            # Variable header - Protocol Name and Level (MQTT v3.1.1)
            protocol_name = b"MQTT"
            vh = (
                struct.pack("!H", len(protocol_name)) + protocol_name + b"\x04"
            )  # Protocol level 4 (v3.1.1)

            # Connect flags
            flags = 0x02 if clean_session else 0x00  # Clean session flag

            # Add username/password flags if provided
            if self.user is not None:
                flags |= 0x80  # Username flag
                if self.pswd is not None:
                    flags |= 0x40  # Password flag

            # Add last will flags if provided
            if self.lw_topic:
                flags |= 0x04  # Will flag
                flags |= (self.lw_qos & 0x03) << 3  # Will QoS
                if self.lw_retain:
                    flags |= 0x20  # Will retain

            vh += bytes([flags])  # Connect Flags
            vh += struct.pack("!H", self.keepalive or 60)  # Keepalive

            # Payload - Client ID (required)
            payload = self._encode_str(self.client_id)

            # Add last will to payload if present
            if self.lw_topic:
                payload += self._encode_str(self.lw_topic)
                payload += self._encode_str(self.lw_msg or "")

            # Add username/password to payload if present
            if self.user is not None:
                payload += self._encode_str(self.user)
                if self.pswd is not None:
                    payload += self._encode_str(self.pswd)

            # Fixed header
            remaining_length = len(vh) + len(payload)
            fixed_header = bytes([0x10]) + self._encode_length(remaining_length)

            # Full message
            msg = fixed_header + vh + payload
            print(f"Sending MQTT CONNECT message ({len(msg)} bytes): {msg.hex()}")
            self.sock.write(msg)

            # Read CONNACK response with improved error handling
            print("Waiting for CONNACK...")
            try:
                # Read first byte to check message type
                first_byte = self._safe_read(1)
                print(f"First byte of response: 0x{first_byte[0]:02x}")

                if first_byte[0] != 0x20:  # CONNACK message type
                    # Try to read more bytes to see what we got
                    try:
                        extra_bytes = self.sock.read(
                            10
                        )  # Read up to 10 more bytes for debugging
                        full_response = first_byte + (extra_bytes or b"")
                        print(
                            f"Unexpected response (first 11 bytes): {full_response.hex()}"
                        )
                    except:
                        pass
                    raise MQTTException(
                        f"Expected CONNACK (0x20), got: 0x{first_byte[0]:02x}"
                    )

                # Read remaining length byte
                remaining_len_byte = self._safe_read(1)
                remaining_len = remaining_len_byte[0]
                print(f"CONNACK remaining length: {remaining_len}")

                if remaining_len != 2:
                    raise MQTTException(
                        f"Expected CONNACK remaining length 2, got: {remaining_len}"
                    )

                # Read the variable header (2 bytes)
                resp_payload = self._safe_read(2)

                full_connack = first_byte + remaining_len_byte + resp_payload
                print(f"Full CONNACK received: {full_connack.hex()}")

                # Check CONNACK return code
                session_present = resp_payload[0] & 0x01
                return_code = resp_payload[1]

                print(
                    f"Session present flag: {session_present}, Return code: {return_code}"
                )

                if return_code != 0:
                    error_codes = {
                        0x01: "Connection Refused, unacceptable protocol version",
                        0x02: "Connection Refused, identifier rejected",
                        0x03: "Connection Refused, Server unavailable",
                        0x04: "Connection Refused, bad user name or password",
                        0x05: "Connection Refused, not authorized",
                    }
                    error_msg = error_codes.get(
                        return_code, f"Unknown error code: {return_code}"
                    )
                    raise MQTTException(
                        f"Connection refused: {error_msg} (code: {return_code})"
                    )

                print(
                    f"MQTT connection established successfully! Session present: {bool(session_present)}"
                )
                return session_present

            except MQTTException:
                raise  # Re-raise MQTT exceptions as-is
            except Exception as e:
                raise MQTTException(f"Error reading CONNACK: {e}")

        except Exception as e:
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
                self.sock = None
            raise MQTTException(
                f"Failed to send CONNECT packet or receive CONNACK: {e}"
            )

    def disconnect(self):
        if self.sock:
            try:
                self.sock.write(b"\xe0\0")
                self.sock.close()
            except:
                pass
            self.sock = None

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
        try:
            res = self.sock.read(1)
            if res is None or res == b"" or len(res) == 0:
                return None
            if res == b"\xd0":  # PINGRESP
                sz_data = self.sock.read(1)
                if not sz_data or len(sz_data) == 0:
                    return None
                sz = sz_data[0]
                assert sz == 0
                return None
            op = res[0]
            if op & 0xF0 != 0x30:
                return op
            sz = self._recv_len()
            topic_len_data = self.sock.read(2)
            if not topic_len_data or len(topic_len_data) != 2:
                return None
            topic_len = (topic_len_data[0] << 8) | topic_len_data[1]
            topic = self.sock.read(topic_len)
            sz -= topic_len + 2
            if op & 6:
                pid_data = self.sock.read(2)
                if not pid_data or len(pid_data) != 2:
                    return None
                pid = pid_data[0] << 8 | pid_data[1]
                sz -= 2
            msg = self.sock.read(sz)
            self.cb(topic, msg)
            if op & 6 == 2:
                pkt = bytearray(b"\x40\x02\0\0")
                struct.pack_into("!H", pkt, 2, pid)
                self.sock.write(pkt)
            elif op & 6 == 4:
                assert 0
        except Exception as e:
            print(f"Error in wait_msg: {e}")
            return None

    def check_msg(self):
        try:
            r, _, _ = select.select([self.sock], [], [], 0.05)
            if len(r):
                return self.wait_msg()
        except:
            return None


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
        self.machine_id = self.config.get("machine_id", self.thing_name)

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
        # wlan = network.WLAN(network.STA_IF)
        # wlan.active(True)
        # if not wlan.isconnected():
        #     print(f'Connecting to Wi-Fi network "{ssid}"...')
        #     wlan.connect(ssid, key)
        #     timeout = 30
        #     start_time = time.time()
        #     while not wlan.isconnected() and (time.time() - start_time) < timeout:
        #         time.sleep_ms(500)
        #     if not wlan.isconnected():
        #         print("Failed to connect to Wi-Fi network.")
        #         return False
        # print("Wi-Fi Connected. IP:", wlan.ifconfig()[0])

        # # 2. Synchronize time (important for SSL certificate validation)
        # if not sync_time():
        #     print(
        #         "Warning: Time synchronization failed. SSL certificates may not work properly."
        #     )

        # 1. Wi-Fi connect
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        if not wlan.isconnected():
            print(f'Connecting to Wi-Fi network "{ssid}"...')
            wlan.connect(ssid, key)
            timeout = 30
            start_time = time.time()
            while not wlan.isconnected() and (time.time() - start_time) < timeout:
                print(".", end="")
                time.sleep(1)
            print()
            if not wlan.isconnected():
                print("Failed to connect to Wi-Fi network.")
                return False
        print("Wi-Fi Connected. IP:", wlan.ifconfig()[0])

        # 2. Synchronize time with retry (important for SSL)
        for attempt in range(3):
            if sync_time():
                break
            print(f"Retrying time sync... Attempt {attempt + 1}/3")
            time.sleep(2)
        else:
            print(
                "Warning: Time synchronization failed. SSL certificates may not work properly."
            )

        # 3. Prepare DER files
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

            # AWS IoT Core client ID must match the policy authorization exactly
            # Use the exact MQTT_CLIENT_ID that matches your AWS IoT policy
            client_id = f"machine228Prod-1234232"
            print(f"Using client ID: {client_id} (must match AWS IoT policy exactly)")

            self.client = MQTTClient(
                client_id=client_id,
                server=AWS_IOT_ENDPOINT,
                port=port,
                ssl=True,
                ssl_params=ssl_params,
                keepalive=60,  # AWS IoT Core recommended keepalive
            )

            self.client.connect(
                clean_session=True, timeout=15.0
            )  # AWS IoT Core prefers clean session
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
                    machine_id=228,
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
