# ============================================================================
# IoT Mesh Network with Person Detection - Modular Architecture
# ============================================================================

import sys
import random
import asyncio
import time as utime
from time import gmtime, strftime

# Hardware detection and imports
run_omv = True
try:
    import omv
    print("The 'omv' library IS installed.")
except ImportError:
    print("The 'omv' library IS NOT installed.")
    run_omv = False

if run_omv:
    from machine import RTC, UART
    import uasyncio as asyncio
    import utime
    import sensor
    import ml
    import os
    import image
    import time
    import binascii
    import machine
    import enc
else:
    import serial

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    # Communication settings
    UART_BAUDRATE = 57600
    USBA_BAUDRATE = 57600
    MIN_SLEEP = 0.1
    ACK_SLEEP = 0.3

    # Protocol settings
    MIDLEN = 7
    FLAKINESS = 0
    FRAME_SIZE = 225

    # Detection settings
    CONFIDENCE_THRESHOLD = 0.5
    IMG_DIR = "/sdcard/images/"
    MODEL_PATH = "/rom/person_detect.tflite"

    # Device addresses
    DEVICE_ADDRESSES = {
        b'e076465dd7194025': 'A',
        b'e076465dd7091027': 'B',
        b'e076465dd7194211': 'Z'
    }

    # USB port for non-OMV devices
    USBA_PORT = "/dev/tty.usbserial-0001"

# ============================================================================
# HARDWARE ABSTRACTION LAYER
# ============================================================================

class HardwareManager:
    def __init__(self):
        self.my_addr = None
        self.uart = None
        self.rtc = None
        self.clock_start = None
        self.model = None
        self.image_count = 0

        self._initialize_hardware()

    def _initialize_hardware(self):
        """Initialize hardware based on platform"""
        if run_omv:
            self._init_omv_hardware()
        else:
            self._init_desktop_hardware()

    def _init_omv_hardware(self):
        """Initialize OpenMV hardware"""
        self.rtc = RTC()
        uid = binascii.hexlify(machine.unique_id())
        print(f"Running on device: {uid.decode()}")

        self.my_addr = Config.DEVICE_ADDRESSES.get(uid)
        if not self.my_addr:
            print(f"Unknown device ID for {omv.board_id()}")
            sys.exit()

        self.clock_start = utime.ticks_ms()

        # Initialize UART
        self.uart = UART(1, baudrate=Config.UART_BAUDRATE, timeout=1000)
        self.uart.init(Config.UART_BAUDRATE, bits=8, parity=None, stop=1)

        # Initialize ML model
        self.model = ml.Model(Config.MODEL_PATH)
        print(f"Model loaded: {self.model}")

        # Initialize camera
        sensor.reset()
        sensor.set_pixformat(sensor.RGB565)
        sensor.set_framesize(sensor.QVGA)
        sensor.skip_frames(time=2000)

    def _init_desktop_hardware(self):
        """Initialize desktop hardware simulation"""
        self.my_addr = 'ZZZZ'
        try:
            self.uart = serial.Serial(Config.USBA_PORT, Config.USBA_BAUDRATE, timeout=0.1)
        except serial.SerialException as e:
            print(f"[ERROR] Could not open serial port {Config.USBA_PORT}: {e}")
            sys.exit(1)

        self.clock_start = int(utime.time() * 1000)

    def get_timestamp(self):
        """Get human readable timestamp"""
        if run_omv and self.rtc:
            _, _, _, _, h, m, s, _ = self.rtc.datetime()
            return f"{m:02d}:{s:02d}"
        else:
            return strftime("%M:%S", gmtime())

    def get_time_msec(self):
        """Get time in milliseconds since start"""
        if run_omv:
            return utime.ticks_diff(utime.ticks_ms(), self.clock_start)
        else:
            return int(utime.time() * 1000) - self.clock_start

    def capture_image(self):
        """Capture image from camera"""
        if run_omv:
            return sensor.snapshot()
        return None

    def save_image(self, img, filename):
        """Save image to storage"""
        if img and run_omv:
            img2 = image.Image(320, 240, image.RGB565, buffer=img.bytearray())
            img2.save(filename)
            return True
        return False

# ============================================================================
# PERSON DETECTION COMPONENT
# ============================================================================

class PersonDetector:
    def __init__(self, hardware_manager):
        self.hw = hardware_manager
        self.detection_count = 0

    def detect_person(self, img):
        """Detect person in image"""
        if not self.hw.model or not img:
            return False, 0.0

        prediction = self.hw.model.predict([img])
        scores = zip(self.hw.model.labels, prediction[0].flatten().tolist())
        scores = sorted(scores, key=lambda x: x[1], reverse=True)

        for label, conf in scores:
            if label == "person":
                if conf >= Config.CONFIDENCE_THRESHOLD:
                    return True, conf
                return False, conf

        return False, 0.0

    async def detection_loop(self, message_handler):
        """Main person detection loop"""
        while True:
            if not run_omv:
                await asyncio.sleep(30)
                continue

            img = self.hw.capture_image()
            if not img:
                await asyncio.sleep(30)
                continue

            self.detection_count += 1
            print(f"Image {self.detection_count}: {len(img.bytearray())} bytes")

            person_detected, confidence = self.detect_person(img)

            if person_detected:
                await self._handle_detection(img, confidence, message_handler)

            await asyncio.sleep(30)

    async def _handle_detection(self, img, confidence, message_handler):
        """Handle person detection event"""
        r = NetworkUtils.get_rand()

        # Send image to control center via shortest path
        if message_handler.routing.shortest_path_to_cc:
            peer_addr = message_handler.routing.shortest_path_to_cc[0]
            await message_handler.send_message("P", self.hw.my_addr, img.bytearray(), peer_addr)

        # Save image locally
        raw_path = f"{Config.IMG_DIR}raw_{r}_{person_detected}_{confidence:.2f}.jpg"
        if self.hw.save_image(img, raw_path):
            print(f"Saved image to {raw_path}")

# ============================================================================
# MESSAGE CHUNKING COMPONENT
# ============================================================================

class MessageChunker:
    def __init__(self):
        self.chunk_map = {}  # chunk_id -> (msg_type, expected_chunks, [(iter, data)])

    def make_chunks(self, msg, chunk_size=200):
        """Split message into chunks"""
        chunks = []
        while len(msg) > chunk_size:
            chunks.append(msg[:chunk_size])
            msg = msg[chunk_size:]
        if len(msg) > 0:
            chunks.append(msg)
        return chunks

    def begin_chunk(self, msg):
        """Initialize chunking for a message"""
        parts = msg.split(":")
        if len(parts) != 3:
            print(f"ERROR: Invalid begin message {msg}")
            return

        msg_type, chunk_id, num_chunks = parts[0], parts[1], int(parts[2])
        self.chunk_map[chunk_id] = (msg_type, num_chunks, [])

    def add_chunk(self, msgbytes):
        """Add a chunk to the reconstruction"""
        if len(msgbytes) < 5:
            print(f"ERROR: Chunk too short {len(msgbytes)}")
            return

        chunk_id = msgbytes[:3].decode()
        chunk_iter = int.from_bytes(msgbytes[3:5], 'big')
        chunk_data = msgbytes[5:]

        if chunk_id not in self.chunk_map:
            print(f"ERROR: No entry for chunk_id {chunk_id}")
            return

        self.chunk_map[chunk_id][2].append((chunk_iter, chunk_data))

    def get_missing_chunks(self, chunk_id):
        """Get list of missing chunk indices"""
        if chunk_id not in self.chunk_map:
            return []

        _, expected_chunks, received_chunks = self.chunk_map[chunk_id]
        received_indices = {chunk_iter for chunk_iter, _ in received_chunks}

        return [i for i in range(expected_chunks) if i not in received_indices]

    def reconstruct_message(self, chunk_id):
        """Reconstruct complete message from chunks"""
        if self.get_missing_chunks(chunk_id):
            return None

        if chunk_id not in self.chunk_map:
            return None

        _, expected_chunks, received_chunks = self.chunk_map[chunk_id]

        # Sort chunks by iteration number
        received_chunks.sort(key=lambda x: x[0])

        reconstructed = b""
        for _, chunk_data in received_chunks:
            reconstructed += chunk_data

        return reconstructed

    def clear_chunk(self, chunk_id):
        """Clear chunk data after reconstruction"""
        self.chunk_map.pop(chunk_id, None)

# ============================================================================
# ROUTING COMPONENT
# ============================================================================

class RoutingManager:
    def __init__(self, my_addr):
        self.my_addr = my_addr
        self.shortest_path_to_cc = []
        self.seen_neighbours = []
        self.hb_map = {}

    def is_control_center(self):
        """Check if this device is the control center"""
        return self.my_addr == "Z"

    def process_scan(self, sender_addr):
        """Process neighbor discovery scan"""
        if sender_addr not in self.seen_neighbours:
            self.seen_neighbours.append(sender_addr)
            print(f"New neighbor discovered: {sender_addr}")

    def process_shortest_path(self, mid, msg, message_handler):
        """Process shortest path update"""
        if self.is_control_center():
            return

        if not msg:
            print("Empty shortest path message")
            return

        path = msg.split(",")

        if self.my_addr in path:
            print(f"Cyclic path detected, ignoring: {path}")
            return

        # Update if we have no path or found a shorter one
        if not self.shortest_path_to_cc or len(self.shortest_path_to_cc) > len(path):
            print(f"Updating shortest path to: {path}")
            self.shortest_path_to_cc = path

            # Propagate updated path to neighbors
            new_path = f"{self.my_addr},{','.join(path)}"
            for neighbor in self.seen_neighbours:
                asyncio.create_task(
                    message_handler.send_message("S", mid[1], new_path.encode(), neighbor)
                )

    def process_heartbeat(self, mid, msgbytes, message_handler):
        """Process heartbeat message"""
        creator = mid[1]

        if self.is_control_center():
            if creator not in self.hb_map:
                self.hb_map[creator] = 0
            self.hb_map[creator] += 1
            print(f"Heartbeat counts: {self.hb_map}")
        else:
            # Forward heartbeat towards control center
            if self.shortest_path_to_cc:
                peer_addr = self.shortest_path_to_cc[0]
                asyncio.create_task(
                    message_handler.send_message("H", creator, msgbytes, peer_addr)
                )
            else:
                print("Cannot forward heartbeat - no path to control center")

# ============================================================================
# COMMUNICATION COMPONENT
# ============================================================================

class NetworkUtils:
    @staticmethod
    def get_rand():
        """Generate random 3-character string"""
        return ''.join(chr(65 + random.randint(0, 25)) for _ in range(3))

    @staticmethod
    def get_msg_id(msgtype, creator, sender, dest):
        """Generate unique message ID"""
        rand_str = NetworkUtils.get_rand()
        return f"{msgtype}{creator}{sender}{dest}{rand_str}"

    @staticmethod
    # def parse_header(data):
    #     """Parse message header"""
    #     if len(data) < 9:
    #         return None

    #     try:
    #         mid = data[:Config.MIDLEN].decode()

    #         # Validate message ID format
    #         for i, char in enumerate(mid):
    #             if not ('A' <= char <= 'Z') and not (i == 3 and char == '*'):
    #                 return None

    #         if data[Config.MIDLEN] != ord(';'):
    #             return None

    #         msg = data[Config.MIDLEN + 1:-1]

    #         return {
    #             'mid': mid,
    #             'type': mid[0],
    #             'creator': mid[1],
    #             'sender': mid[2],
    #             'receiver': mid[3],
    #             'msg': msg
    #         }
    #     except (UnicodeDecodeError, IndexError):
    #         return None
    def parse_header(data):
        """OpenMV/MicroPython compatible version"""
        try:
            if not data or len(data) < 9:
                return None
            
            # Manual byte cleaning for MicroPython
            clean_str = ""
            for i in range(len(data)):
                b = data[i]
                if 32 <= b <= 126:  # Printable ASCII
                    clean_str += chr(b)
                elif b in [10, 13]:  # Newline, carriage return
                    clean_str += chr(b)
                else:
                    clean_str += ' '  # Replace bad bytes with space
            
            clean_str = clean_str.rstrip('\n\r ')
            
            if len(clean_str) < 8:
                return None
            
            mid = clean_str[:7]
            
            # Validate message ID
            for i in range(7):
                c = mid[i]
                if not (('A' <= c <= 'Z') or (i == 3 and c == '*')):
                    return None
            
            if clean_str[7] != ';':
                return None
            
            msg_part = clean_str[8:]
            msg_bytes = msg_part.encode('utf-8') if msg_part else b''
            
            return {
                'mid': mid,
                'type': mid[0],
                'creator': mid[1],
                'sender': mid[2], 
                'receiver': mid[3],
                'msg': msg_bytes
            }
            
        except Exception as e:
            print(f"[ERROR] Parse error: {e}")
            return None

    @staticmethod
    def encrypt_if_needed(msg_type, msg):
        """Apply encryption if needed (placeholder)"""
        if msg_type == "H" and len(msg) <= 117:
            # Encrypt heartbeat messages
            if run_omv:
                return enc.encrypt_rsa(msg, enc.load_rsa_pub())
        return msg

class MessageHandler:
    def __init__(self, hardware_manager):
        self.hw = hardware_manager
        self.routing = RoutingManager(hardware_manager.my_addr)
        self.chunker = MessageChunker()

        # Message tracking
        self.msgs_sent = []
        self.msgs_unacked = []
        self.msgs_received = []
        self.sent_count = 0
        self.recv_msg_count = {}

        self.print_lock = asyncio.Lock()

    def log(self, msg):
        """Log message with timestamp"""
        timestamp = self.hw.get_timestamp()
        print(f"{timestamp}: {msg}")

    def ack_needed(self, msg_type):
        """Check if message type requires acknowledgment"""
        return msg_type in ["H", "B", "E"] and msg_type != "A"

    def radio_send(self, data):
        """Send data over radio"""
        self.sent_count += 1
        self.hw.uart.write(data)
        self.log(f"[SENT] {len(data)} bytes at {self.hw.get_time_msec()}")

    async def send_single_message(self, msg_type, creator, msgbytes, dest):
        """Send a single message with retry logic"""
        mid = NetworkUtils.get_msg_id(msg_type, creator, self.hw.my_addr, dest)
        databytes = mid.encode() + b";" + msgbytes + b"\n"

        ack_required = dest != "*" and self.ack_needed(msg_type)
        time_sent = self.hw.get_time_msec()

        if ack_required:
            self.msgs_unacked.append((mid, msgbytes, time_sent))
        else:
            self.msgs_sent.append((mid, msgbytes, time_sent))

        if not ack_required:
            self.radio_send(databytes)
            return True, []

        # Retry logic for acknowledged messages
        for retry in range(5):
            self.radio_send(databytes)
            await asyncio.sleep(Config.ACK_SLEEP)

            for attempt in range(3):
                ack_time, missing_chunks = self._check_ack(mid)
                if ack_time > 0:
                    self.log(f"Message {mid} acknowledged in {ack_time - time_sent} ms")
                    self._move_to_sent(mid)
                    return True, missing_chunks

                await asyncio.sleep(Config.ACK_SLEEP * (attempt + 1))

            self.log(f"Retry {retry} failed for message {mid}")

        self.log(f"Failed to send message {mid}")
        return False, []

    async def send_message(self, msg_type, creator, msg, dest):
        """Send message (with chunking if needed)"""
        msgbytes = NetworkUtils.encrypt_if_needed(msg_type, msg)

        if len(msgbytes) < Config.FRAME_SIZE:
            success, _ = await self.send_single_message(msg_type, creator, msgbytes, dest)
            return success

        # Handle large messages with chunking
        return await self._send_chunked_message(msg_type, creator, msgbytes, dest)

    async def _send_chunked_message(self, msg_type, creator, msgbytes, dest):
        """Send large message using chunking protocol"""
        chunk_id = NetworkUtils.get_rand()
        chunks = self.chunker.make_chunks(msgbytes)

        self.log(f"Chunking {len(msgbytes)} byte message into {len(chunks)} chunks")

        # Send begin message
        begin_msg = f"{msg_type}:{chunk_id}:{len(chunks)}"
        success, _ = await self.send_single_message("B", creator, begin_msg.encode(), dest)
        if not success:
            return False

        # Send chunks
        for i, chunk in enumerate(chunks):
            chunk_bytes = chunk_id.encode() + i.to_bytes(2, 'big') + chunk
            await self.send_single_message("I", creator, chunk_bytes, dest)

        # Send end message and handle retransmissions
        for retry in range(50):
            success, missing_chunks = await self.send_single_message("E", creator, chunk_id.encode(), dest)
            if not success:
                break

            if len(missing_chunks) == 1 and missing_chunks[0] == -1:
                self.log("All chunks successfully transmitted")
                return True

            if missing_chunks:
                self.log(f"Retransmitting {len(missing_chunks)} missing chunks")
                for chunk_idx in missing_chunks:
                    if chunk_idx < len(chunks):
                        chunk_bytes = chunk_id.encode() + chunk_idx.to_bytes(2, 'big') + chunks[chunk_idx]
                        await self.send_single_message("I", creator, chunk_bytes, dest)

        return False

    def _check_ack(self, msg_id):
        """Check if message has been acknowledged"""
        for mid, msg, timestamp in self.msgs_received:
            if mid[0] == "A" and len(msg) >= Config.MIDLEN:
                acked_id = msg[:Config.MIDLEN].decode()
                if msg_id == acked_id:
                    missing_chunks = []
                    if len(msg) > Config.MIDLEN + 1:
                        try:
                            missing_str = msg[Config.MIDLEN + 1:].decode()
                            missing_chunks = [int(x) for x in missing_str.split(',') if x]
                        except (ValueError, UnicodeDecodeError):
                            missing_chunks = []
                    return timestamp, missing_chunks
        return -1, None

    def _move_to_sent(self, msg_id):
        """Move message from unacked to sent"""
        for i, (mid, msg, timestamp) in enumerate(self.msgs_unacked):
            if mid == msg_id:
                self.msgs_sent.append(self.msgs_unacked.pop(i))
                break

    async def radio_read(self):
        """Async radio receiver"""
        if run_omv:
            while True:
                if self.hw.uart.any():
                    buffer = self.hw.uart.readline()
                    if buffer:
                        self._process_message(buffer)
                await asyncio.sleep(0.01)
        else:
            buffer = b""
            while True:
                await asyncio.sleep(0.01)
                while self.hw.uart.in_waiting > 0:
                    byte = self.hw.uart.read(1)
                    buffer += byte
                    if byte == b'\n':
                        self._process_message(buffer)
                        buffer = b""

    def _process_message(self, data):
        """Process incoming message"""
        parsed = NetworkUtils.parse_header(data)
        if not parsed:
            self.log(f"Failed to parse message: {data}")
            return

        # Simulate network flakiness
        if random.randint(1, 100) <= Config.FLAKINESS:
            self.log(f"Dropping message due to flakiness: {data}")
            return

        mid = parsed['mid']
        msg_type = parsed['type']
        creator = parsed['creator']
        sender = parsed['sender']
        receiver = parsed['receiver']
        msg = parsed['msg']

        # Update receive statistics
        if sender not in self.recv_msg_count:
            self.recv_msg_count[sender] = 0
        self.recv_msg_count[sender] += 1

        # Check if message is for us
        if receiver != "*" and self.hw.my_addr != receiver:
            self.log(f"Message not for us (for {receiver}): {mid}")
            return

        self.log(f"[RECV {len(data)}] {mid} at {self.hw.get_time_msec()}")
        self.msgs_received.append((mid, msg, self.hw.get_time_msec()))

        # Process message by type
        ack_message = mid

        if msg_type == "N":  # Neighbor discovery
            self.routing.process_scan(sender)
        elif msg_type == "S":  # Shortest path
            self.routing.process_shortest_path(mid, msg.decode(), self)
        elif msg_type == "H":  # Heartbeat
            self.routing.process_heartbeat(mid, msg, self)
        elif msg_type == "B":  # Begin chunking
            self.chunker.begin_chunk(msg.decode())
        elif msg_type == "I":  # Intermediate chunk
            self.chunker.add_chunk(msg)
        elif msg_type == "E":  # End chunking
            all_received, result = self._handle_end_chunk(msg.decode())
            if all_received:
                ack_message += ":-1"
                self.log(f"Message fully received: {len(result)} bytes")
                self._process_reconstructed_message(msg_type, result)
            else:
                ack_message += f":{result}"
        elif msg_type == "P":  # Person detection data
            self._process_person_data(mid, msg)

        # Send acknowledgment if needed
        if self.ack_needed(msg_type) and receiver != "*":
            asyncio.create_task(
                self.send_message("A", self.hw.my_addr, ack_message.encode(), sender)
            )

    def _handle_end_chunk(self, chunk_id):
        """Handle end of chunked message"""
        missing = self.chunker.get_missing_chunks(chunk_id)

        if missing:
            # Return missing chunk indices (limited by frame size)
            missing_str = ",".join(str(x) for x in missing[:10])  # Limit count
            return False, missing_str
        else:
            reconstructed = self.chunker.reconstruct_message(chunk_id)
            self.chunker.clear_chunk(chunk_id)
            return True, reconstructed

    def _process_reconstructed_message(self, msg_type, data):
        """Process a reconstructed chunked message"""
        if msg_type == "P":  # Person detection image
            self._process_person_data("", data)

    def _process_person_data(self, mid, data):
        """Process person detection data"""
        if self.routing.is_control_center():
            self.log(f"Received person detection image: {len(data)} bytes")
            # TODO: Save or process the image at control center
        else:
            # Forward to control center if not there yet
            if self.routing.shortest_path_to_cc:
                peer_addr = self.routing.shortest_path_to_cc[0]
                asyncio.create_task(
                    self.send_message("P", mid[1] if mid else self.hw.my_addr, data, peer_addr)
                )

# ============================================================================
# TASK MANAGERS
# ============================================================================

class TaskManager:
    def __init__(self, hardware_manager, message_handler, person_detector):
        self.hw = hardware_manager
        self.msg_handler = message_handler
        self.detector = person_detector

    async def heartbeat_task(self):
        """Send periodic heartbeats"""
        while True:
            hb_msg = f"{self.hw.my_addr}:{self.hw.get_timestamp()}"

            if self.msg_handler.routing.shortest_path_to_cc:
                peer_addr = self.msg_handler.routing.shortest_path_to_cc[0]
                await self.msg_handler.send_message("H", self.hw.my_addr, hb_msg.encode(), peer_addr)

            await asyncio.sleep(30)

    async def scan_task(self):
        """Send periodic neighbor discovery scans"""
        scan_count = 0
        while True:
            scan_msg = self.hw.my_addr
            await self.msg_handler.send_message("N", self.hw.my_addr, scan_msg.encode(), "*")

            scan_count += 1
            if scan_count < 10:
                await asyncio.sleep(10)  # Frequent scans during startup
            else:
                await asyncio.sleep(300)  # Less frequent scans later

            # Print status
            print(f"Neighbors: {self.msg_handler.routing.seen_neighbours}")
            print(f"Shortest path: {self.msg_handler.routing.shortest_path_to_cc}")
            print(f"Messages sent: {self.msg_handler.sent_count}")
            print(f"Messages received: {self.msg_handler.recv_msg_count}")

    async def shortest_path_task(self):
        """Control center shortest path distribution"""
        while True:
            await asyncio.sleep(10)

            sp_msg = self.hw.my_addr
            for neighbor in self.msg_handler.routing.seen_neighbours:
                await self.msg_handler.send_message("S", self.hw.my_addr, sp_msg.encode(), neighbor)

            await asyncio.sleep(50)

# ============================================================================
# MAIN APPLICATION
# ============================================================================

class MeshNetworkApp:
    def __init__(self):
        self.hw = HardwareManager()
        self.msg_handler = MessageHandler(self.hw)
        self.detector = PersonDetector(self.hw)
        self.task_manager = TaskManager(self.hw, self.msg_handler, self.detector)

    async def run(self):
        """Main application entry point"""
        print(f"[INFO] Starting device {self.hw.my_addr} (OMV={run_omv})")

        # Start radio receiver
        asyncio.create_task(self.msg_handler.radio_read())

        if self.hw.my_addr in ["A", "B", "C"]:
            # Regular nodes: heartbeat, scanning, detection
            asyncio.create_task(self.task_manager.heartbeat_task())
            asyncio.create_task(self.task_manager.scan_task())
            asyncio.create_task(self.detector.detection_loop(self.msg_handler))
            await asyncio.sleep(36000)  # Run for 10 hours

        elif self.hw.my_addr == "Z":
            # Control center: shortest path distribution, scanning
            asyncio.create_task(self.task_manager.shortest_path_task())
            asyncio.create_task(self.task_manager.scan_task())
            await asyncio.sleep(3600)  # Run for 1000 hours

        else:
            print(f"Unknown device address: {self.hw.my_addr}")

# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

def main():
    app = MeshNetworkApp()
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        print("Application stopped by user")

if __name__ == "__main__":
    main()
