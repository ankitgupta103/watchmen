from logger import logger

try:
    import requests
    USE_REQUESTS = True
except ImportError:
    USE_REQUESTS = False
from machine import RTC, UART, Pin
import uasyncio as asyncio
import utime
import sensor
import image
import ml
import os                   # file system access
import time
import binascii
import machine
from machine import LED
import sys
import random
import ubinascii
import network
import json
import gc                   # garbage collection for memory management

import enc
from sx1262 import SX1262
from _sx126x import ERR_NONE, ERR_RX_TIMEOUT, ERR_CRC_MISMATCH, SX126X_SYNC_WORD_PRIVATE
import gps_driver
from cellular_driver import Cellular
import detect

# -----------------------------------▼▼▼▼▼-----------------------------------
# TESTING VARIABLES
DYNAMIC_SPATH = False
ENCRYPTION_ENABLED = True
# -----------------------------------▲▲▲▲▲-----------------------------------




# -----------------------------------▼▼▼▼▼-----------------------------------
# FIXED VARIABLES
led = LED("LED_BLUE")

MIN_SLEEP = 0.05  # Reduced for high-speed communication (SF5, BW500kHz)
ACK_SLEEP = 0.15  # Reduced for faster ACK checking at high data rates
CHUNK_SLEEP = 0.05  # Reduced for faster chunk transmission at high data rates

DISCOVERY_COUNT = 100
HB_WAIT = 600
HB_WAIT_2 = 1200
SPATH_WAIT = 30
SPATH_WAIT_2 = 1200
SCAN_WAIT = 30
SCAN_WAIT_2 = 1200
VALIDATE_WAIT_SEC = 1200
PHOTO_TAKING_DELAY = 600

PHOTO_SENDING_EMPTY_DELAY = 4
PHOTO_SENDING_TRY_INTERVAL = 20  # Delay between uploads when queue has multiple images
PHOTO_SENDING_FAILED_PAUSE = 20 # TODO earlier it was 120 second

EVENT_SENDING_EMPTY_DELAY = 4
EVENT_SENDING_INTERVAL = 10  # Delay between uploads when queue has multiple events
EVENT_SENDING_FAILED_PAUSE = 10

GPS_WAIT_SEC = 5

# Memory Management Constants
MAX_MSGS_SENT = 500          # Maximum messages in sent buffer
MAX_MSGS_RECD = 500          # Maximum messages in received buffer
MAX_MSGS_UNACKED = 100       # Maximum unacknowledged messages
MAX_CHUNK_MAP_SIZE = 50      # Maximum chunk entries (chunk_id to chunks)
MAX_IMAGES_SAVED_AT_CC = 200 # Maximum image filenames to track at CC
MAX_IMAGES_TO_SEND = 50      # Maximum images in send queue
MAX_OLD_MSG_AGE_SEC = 3600   # Age threshold (seconds) for cleaning old messages
MEM_CLEANUP_INTERVAL_SEC = 300  # Run memory cleanup every 5 minutes
GC_COLLECT_INTERVAL_SEC = 60    # Run garbage collection every minute

MIDLEN = 7
FLAKINESS = 0
PACKET_PAYLOAD_LIMIT = 195 # bytes

AIR_SPEED = 19200

# LoRa Configuration Constants - Highest Data Rate (SF5, BW500kHz, CR5) for fast robust communication
LORA_FREQ = 868.0
LORA_SF = 5  # Spreading Factor 5 (highest data rate ~38 kbps)
LORA_BW = 500.0  # Bandwidth 500 kHz (highest bandwidth for maximum speed)
LORA_CR = 5  # Coding Rate 4/5 (good balance of speed and error correction)
LORA_PREAMBLE = 8  # Preamble length (as used in high-speed examples)
LORA_POWER = 14  # TX power in dBm
LORA_RX_TIMEOUT_MS = 200  # Receive timeout for async loop (optimized for high-speed communication)


# WiFi Configuration
WIFI_SSID = "Lifestyle 6th floor-2.4G"
WIFI_PASSWORD = "9821992096"
WIFI_ENABLED = True

cellular_system = None
wifi_nic = None
# -----------------------------------▲▲▲▲▲-----------------------------------




# -----------------------------------▼▼▼▼▼-----------------------------------
# STATE VARIABLES
# -------- Start FPS clock -----------
#clock = time.clock()            # measure frame/sec
person_image_count = 0                 # Counter to keep tranck of saved images
total_image_count = 0
center_captured_image_count = 0        # Counter for images captured on center device
gps_str = ""
gps_last_time = -1

consecutive_hb_failures = 0
lora_init_count = 0
lora_init_in_progress = False

image_in_progress = False
busy_devices = [] # device those are busy in sending/receiving images

# SD card write lock
lock = asyncio.Lock()

my_addr = None
shortest_path_to_cc = []
seen_neighbours = []
# -----------------------------------▲▲▲▲▲-----------------------------------


# -----------------------------------▼▼▼▼▼-----------------------------------
# --------- DEBUGGING ONLY ---- REMOVE BEFORE FINAL -------------------------

COMMAN_CENTER_ADDRS = [219]
IMAGE_CAPTURING_ADDRS = [221] # [] empty means capture at all device, else on list of devices
import fakelayout
flayout = fakelayout.Layout()

rtc = machine.RTC()
rtc.datetime((2025, 1, 1, 0, 0, 0, 0, 0))

# --------- DEBUGGING ONLY ---- REMOVE BEFORE FINAL -------------------------
# -----------------------------------▲▲▲▲▲-----------------------------------


uid = binascii.hexlify(machine.unique_id())      # Returns 8 byte unique ID for board
# COMMAND CENTERS, OTHER NODES
if uid == b'e076465dd7194025':
    my_addr = 225
elif uid == b'e076465dd7193a09':
    my_addr = 219
elif uid ==  b'e076465dd7090d1c':
    my_addr = 221
    if not DYNAMIC_SPATH:
        shortest_path_to_cc = [225, 219]
elif uid == b'e076465dd7091027':
    my_addr = 222
elif uid == b'e076465dd7091843':
    my_addr = 223
    if not DYNAMIC_SPATH:
        shortest_path_to_cc = [219]
else:
    logger.error("error in main.py: Unknown device ID for " + omv.board_id())
    sys.exit()

clock_start = utime.ticks_ms() # get millisecond counter

def get_free_memory():
    """Get available free memory in bytes"""
    try:
        # MicroPython's gc module provides mem_free()
        gc.collect()
        return gc.mem_free()
    except AttributeError:
        # If gc.mem_free() doesn't exist, try machine.mem_free()
        try:
            return machine.mem_free() if hasattr(machine, 'mem_free') else -1
        except:
            return -1
    except Exception:
        return -1

def running_as_cc():
    # Input: None; Output: bool indicating if this device is the command center
    return my_addr in COMMAN_CENTER_ADDRS

def get_fs_root_for_storage():
    # Input: None; Output: str path for filesystem root
    has_sdcard = True
    try:
        os.listdir('/sdcard')
        logger.debug("[FS] SD card available")
    except OSError:
        logger.error("[FS] SD card not found!")
        has_sdcard = False

    if has_sdcard:
        return "/sdcard"
    else:
        return "/flash"

FS_ROOT = get_fs_root_for_storage()
logger.info(f"[FS] Using FS_ROOT : {FS_ROOT}")
MY_IMAGE_DIR = f"{FS_ROOT}/myimages"
MY_EVENT_DIR = f"{FS_ROOT}/myevents"
NET_IMAGE_DIR = f"{FS_ROOT}/netimages"

def create_dir_if_not_exists(dir_path):
    try:
        parts = [p for p in dir_path.split('/') if p]
        if len(parts) < 2:
            logger.warning(f"[FS] Invalid directory path (no parent): {dir_path}")
            return
        parent = '/' + '/'.join(parts[:-1])
        dir_name = parts[-1]
        if dir_name not in os.listdir(parent):
            os.mkdir(dir_path)
            logger.info(f"[FS] Created {dir_path}")
        else:
            try:
                os.listdir(dir_path)  # for valid diretory
                logger.info(f"[FS] {dir_path} directory already exists")
            except OSError:
                logger.error(
                    f"dir:{dir_path} exists but not a directory, so deleting and recreating"
                )
                try:
                    os.remove(dir_path)
                    os.mkdir(dir_path)
                    print(f"info - Removed file {dir_path} and created directory")
                except OSError as e:
                    print(
                        f"WARNING - Failed to remove file {dir_path} and create directory: {e}"
                    )

    except OSError as e:
        logger.error(f"[FS] Failed to create/access {dir_path}: {e}")

create_dir_if_not_exists(NET_IMAGE_DIR)
create_dir_if_not_exists(MY_IMAGE_DIR)
create_dir_if_not_exists(MY_EVENT_DIR)

encnode = enc.EncNode(my_addr)
logger.info(f"[INIT] ===> MyAddr = {my_addr}, uid={uid.decode()} <===\n")

def time_msec():
    # Input: None; Output: int milliseconds since clock_start
    delta = utime.ticks_diff(utime.ticks_ms(), clock_start) # compute time difference
    return delta

def get_epoch_ms(): # get epoch milliseconds, eg. 1381791310000
    return utime.time_ns() // 1_000_000

def time_sec():
    # Input: None; Output: int seconds since clock_start
    return int(utime.ticks_diff(utime.ticks_ms(), clock_start) / 1000) # compute time difference


# TypeSourceDestRRRandom
def encode_node_id(node_id):
    # Input: node_id: int; Output: single-byte representation
    if not isinstance(node_id, int):
        logger.error(f"[LORA] node id must be int, got {type(node_id)}")
        raise TypeError(f"node id must be int, got {type(node_id)}")
    if not 0 <= node_id <= 255:
        logger.error(f"[LORA] node id {node_id} out of range (0-255)")
        raise ValueError(f"node id {node_id} out of range (0-255)")
    return bytes((node_id,))

def encode_dest(dest):
    # Input: dest: int; Output: single-byte representation or broadcast marker
    if dest in (0, 65535):
        return b'*'
    return encode_node_id(dest)

def get_rand():
    # Input: None; Output: str random 3-letter uppercase identifier
    rstr = ""
    for i in range(3):
        rstr += chr(65+random.randint(0,25))
    return rstr

def get_msg_uid(msg_typ, creator, dest):
    # Input: msg_typ: str, creator: int, dest: int; Output: bytes message identifier
    rrr = get_rand()
    msg_uid = (
        msg_typ.encode()
        + encode_node_id(creator)
        + encode_node_id(my_addr)
        + encode_dest(dest)
        + rrr.encode()
    )
    return msg_uid

def parse_header(data):
    # Input: data: bytes; Output: tuple(msg_uid, msg_typ, creator, sender, receiver, msg) or None
    msg_uid = b""
    if data == None:
        logger.warning(f"[LORA] Weird that data is none")
        return None
    # Minimum message is MIDLEN (7 bytes) + separator (1 byte) = 8 bytes
    if len(data) < MIDLEN + 1:
        return None
    try:
        msg_uid = data[:MIDLEN]
    except Exception as e:
        logger.error(f"[LORA] error parsing {data[:MIDLEN]} : {e}")
        return
    msg_typ = chr(msg_uid[0])
    creator = int(msg_uid[1])
    sender = int(msg_uid[2])
    if msg_uid[3] == 42 or msg_uid == b"*":
        receiver = -1
    else:
        receiver=int(msg_uid[3])
    if chr(data[MIDLEN]) != ';':
        return None
    msg = data[MIDLEN+1:]
    return (msg_uid, msg_typ, creator, sender, receiver, msg)

def ellepsis(msg):
    # Input: msg: str; Output: str truncated with ellipsis if necessary
    if len(msg) > 200:
        return msg[:100] + "......." + msg[-100:]
    return msg

def ack_needed(msg_typ): # msg_type P is devided in (B,I,E)
    # Input: msg_typ: str; Output: bool indicating if acknowledgement required
    if msg_typ in ["A", "I", "S", "W", "N"]:
        return False
    if msg_typ in ["H", "B", "E", "V", "C", "T"]:
        return True
    return False

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.HD)
sensor.skip_frames(time=2000)

sent_count = 0
recv_msg_count = {}

URL_OLD = "https://n8n.vyomos.org/webhook/watchmen-detect/"
URL = "https://hqapi.vyomos.org/watchmen-detect/"


# -----------------------------------▼▼▼▼▼-----------------------------------
# TRANSFER MODE Lock
TRANSMODE_LOCK_TIME = 180
def get_transmode_lock(device_id, img_id): # check and just lock for image
    global image_in_progress, paired_device, data_id
    if image_in_progress == True: # TRANS MODE already in use
        return False
    image_in_progress = True
    paired_device = device_id
    data_id = img_id
    logger.info(f"[IMG] ●●●●●●●●●●❯❯ TRANS MODE started, device:{device_id}, img_id:{img_id} ❮❮●●●●●●●●●●")
    return True

async def keep_transmode_lock(device_id, img_id):
    # Input: None; Output: None (sets image_in_progress flag with auto release after timeout)
    global image_in_progress, paired_device, data_id
    await asyncio.sleep(TRANSMODE_LOCK_TIME) # At this point this process might complete, also other might start
    if image_in_progress and paired_device == device_id and data_id == img_id: # TODO, test this
        logger.warning(f"[IMG] ●●●●●●●●●●❯❯ TRANS MODE ended, device:{device_id}, img_id:{img_id}, by TIMEOUT ❮❮●●●●●●●●●●")
        image_in_progress = False
        paired_device = None
        data_id = None
    else:
        logger.debug(f"[IMG] ○○○○○○○○○○❯❯ TRANS MODE already ended, device:{device_id}, img_id:{img_id} ❮❮○○○○○○○○○○") # todo, will move it to debug later

def check_transmode_lock(device_id, img_id): # check if transfer lock is active or not
    global image_in_progress, paired_device, data_id
    if image_in_progress and paired_device == device_id and data_id == img_id:
        return True
    else:
        return False

def delete_transmode_lock(device_id, img_id):
    # Input: None; Output: None (clears image_in_progress flag)
    global image_in_progress, paired_device, data_id
    if image_in_progress and paired_device == device_id and data_id == img_id:  # TODO, these has to handled using someuniqueness
        logger.info(f"[IMG] ●●●●●●●●●●❯❯ TRANS MODE ended for device:{device_id}, img_id:{img_id}, by logic ❮❮●●●●●●●●●●")
        image_in_progress = False
        paired_device = None
        data_id = None
    else:
        logger.debug(f"[IMG] ○○○○○○○○○○❯❯ TRANS MODE already ended, for device {device_id} and img_id {img_id} ❮❮○○○○○○○○○○") # will move it to debug later
# -----------------------------------▲▲▲▲▲-----------------------------------



# -----------------------------------▼▼▼▼▼-----------------------------------
# STORE for BUSY DEVICES
BUSY_WAIT_TIME = 20
WAIT_MESSAGE = f"{20}"
def is_device_free(device_id):
    global busy_devices
    # return not device_id in busy_devices
    if device_id in busy_devices:
        return False
    return True

def is_device_busy(device_id):
    global busy_devices
    # return device_id in busy_devices
    if device_id in busy_devices:
        return True
    return False

async def device_busy_life(device_id): # device_busy_cycle
    # Input: device_id: int; Output: None (sets image_in_progress flag with auto release after timeout)
    global busy_devices
    busy_devices.append(device_id)
    logger.info(f"Device marked busy, device:{device_id}")
    await asyncio.sleep(BUSY_WAIT_TIME) # At this point this process might complete, also other might start
    busy_devices.remove(device_id)
    logger.info(f"Device marked free, device:{device_id}")
# -----------------------------------▲▲▲▲▲-----------------------------------



# -----------------------------------▼▼▼▼▼-----------------------------------
# Network Topology Helpers
def possible_paths(sender=None): # Not in use, next_device_in_spath is new fun
    # Input: sender: int or None; Output: list of int possible next-hop addresses
    possible_paths = []
    sp0 = None
    if len(shortest_path_to_cc) > 0:
        sp0 = shortest_path_to_cc[0]
        possible_paths.append(shortest_path_to_cc[0])
    for x in seen_neighbours:
        if x != my_addr and x != sender and x != sp0:
            possible_paths.append(x)
    return possible_paths

def next_device_in_spath():
    for x in shortest_path_to_cc:
        if DYNAMIC_SPATH: # return first node of spath
            return x
        else: # we will check if this is in seen_neighbours
            return x
            # if x in seen_neighbours:
            #     return x
            # else:
            #     logger.debug(f"Next node:{x} of fixed shortest_path_to_cc is not in seen_neighbours")
            #     return None
    # empty shortest_path_to_cc []
    return None
# -----------------------------------▲▲▲▲▲-----------------------------------



# -----------------------------------▼▼▼▼▼-----------------------------------
# LoRa Setup and Transmission
# ---------------------------------------------------------------------------
loranode = None
async def init_lora():
    # Input: None; Output: None (initializes global loranode, updates lora_reinit_count)
    global loranode, lora_init_count, lora_init_in_progress
    if lora_init_in_progress:
        logger.info(f"[LORA] Initialization already in progress, skipping duplicate call")
        return
    lora_init_in_progress = True
    try:
        lora_init_count += 1
        logger.info(f"[LORA] Initializing LoRa SX1262 module... my lora addr = {my_addr}")

        # Initialize SX1262 with SPI pin configuration
        loranode = SX1262(
            spi_bus=1,
            clk='P2',      # SCLK
            mosi='P0',     # MOSI
            miso='P1',     # MISO
            cs='P3',       # Chip Select
            irq='P13',     # DIO1 (IRQ)
            rst='P6',      # Reset
            gpio='P7',     # BUSY
            spi_baudrate=2000000,
            spi_polarity=0,
            spi_phase=0
        )

        # Configure LoRa with highest data rate settings (SF5, BW500kHz, CR5) for fast robust communication
        status = loranode.begin(
            freq=LORA_FREQ,
            bw=LORA_BW,
            sf=LORA_SF,
            cr=LORA_CR,
            syncWord=SX126X_SYNC_WORD_PRIVATE,
            power=LORA_POWER,
            currentLimit=60.0,
            preambleLength=LORA_PREAMBLE,
            implicit=False,
            crcOn=True,
            tcxoVoltage=1.6,
            useRegulatorLDO=False,
            blocking=True
        )

        if status != ERR_NONE:
            logger.error(f"[LORA] Failed to initialize SX1262, status: {status}")
            loranode = None
        else:
            logger.info(f"[LORA] SX1262 initialized successfully with SF{LORA_SF}, BW{LORA_BW}kHz, CR{LORA_CR} (highest data rate)")
    except Exception as e:
        logger.error(f"[LORA] Exception during LoRa initialization: {e}")
        loranode = None
    finally:
        lora_init_in_progress = False

def is_lora_ready():
    # Input: None; Output: bool indicating if LoRa is ready to send
    # Returns True if connected, False if not (and starts initialization if needed)
    global lora_init_in_progress, loranode
    if loranode is None:
        if not lora_init_in_progress:
            logger.error(f"[LORA] Not connected to network, init started in background.., msg marked as failed")
            asyncio.create_task(init_lora())
        else:
            logger.debug(f"[LORA] Not connected to network, init already in progress, msg marked as failed")
        return False
    return True
# -----------------------------------▲▲▲▲▲-----------------------------------



msgs_sent = []
msgs_unacked = []
msgs_recd = []

# Memory Management Functions
def cleanup_old_messages():
    """Remove old messages from buffers based on age and size limits"""
    global msgs_sent, msgs_recd, msgs_unacked
    current_time = time_msec()
    age_threshold_ms = MAX_OLD_MSG_AGE_SEC * 1000

    # Clean msgs_sent - remove messages older than threshold
    msgs_sent = [(msg_uid, msg, t) for msg_uid, msg, t in msgs_sent
                 if (current_time - t) < age_threshold_ms]
    # Also limit by size
    if len(msgs_sent) > MAX_MSGS_SENT:
        msgs_sent = msgs_sent[-MAX_MSGS_SENT:]
        logger.info(f"[MEM] Trimmed msgs_sent to {MAX_MSGS_SENT} entries")

    # Clean msgs_recd - remove messages older than threshold
    msgs_recd = [(msg_uid, msg, t) for msg_uid, msg, t in msgs_recd
                 if (current_time - t) < age_threshold_ms]
    # Also limit by size
    if len(msgs_recd) > MAX_MSGS_RECD:
        msgs_recd = msgs_recd[-MAX_MSGS_RECD:]
        logger.info(f"[MEM] Trimmed msgs_recd to {MAX_MSGS_RECD} entries")

    # Clean msgs_unacked - remove very old unacked messages (they likely failed)
    old_unacked = []
    new_unacked = []
    for msg_uid, msg, t in msgs_unacked:
        age = current_time - t
        if age > age_threshold_ms * 2:  # Double threshold for unacked (more lenient)
            old_unacked.append(msg_uid)
        else:
            new_unacked.append((msg_uid, msg, t))
    msgs_unacked = new_unacked

    if len(old_unacked) > 0:
        logger.info(f"[MEM] Removed {len(old_unacked)} old unacked messages")

    # Also limit by size
    if len(msgs_unacked) > MAX_MSGS_UNACKED:
        # Remove oldest ones
        msgs_unacked.sort(key=lambda x: x[2])  # Sort by timestamp
        msgs_unacked = msgs_unacked[-MAX_MSGS_UNACKED:]
        logger.info(f"[MEM] Trimmed msgs_unacked to {MAX_MSGS_UNACKED} entries")

def cleanup_chunk_map():
    """Clean up old/incomplete chunk entries"""
    global chunk_map
    if len(chunk_map) > MAX_CHUNK_MAP_SIZE:
        # Remove oldest entries (FIFO)
        # Note: Python dicts maintain insertion order (Python 3.7+)
        entries_to_remove = len(chunk_map) - MAX_CHUNK_MAP_SIZE
        keys_to_remove = list(chunk_map.keys())[:entries_to_remove]
        for key in keys_to_remove:
            chunk_map.pop(key)
        logger.info(f"[MEM] Cleaned {entries_to_remove} old chunk_map entries")


async def periodic_memory_cleanup():
    """Periodically clean up memory buffers and run garbage collection"""
    while True:
        try:
            await asyncio.sleep(MEM_CLEANUP_INTERVAL_SEC)
            free_before = get_free_memory()

            logger.info(f"[MEM] Starting memory cleanup (free: {free_before/1024:.1f}KB)")

            # Clean up message buffers
            cleanup_old_messages()

            # Clean up chunk map
            cleanup_chunk_map()

            # Run garbage collection
            gc.collect()

            free_after = get_free_memory()
            freed = free_after - free_before if free_before > 0 and free_after > 0 else 0
            logger.info(f"[MEM] Cleanup complete (free: {free_after/1024:.1f}KB, freed: {freed/1024:.1f}KB)")
            logger.info(f"[MEM] Buffers - sent:{len(msgs_sent)}, recd:{len(msgs_recd)}, unacked:{len(msgs_unacked)}, chunks:{len(chunk_map)}")

        except Exception as e:
            logger.error(f"[MEM] error in memory cleanup: {e}")

async def periodic_gc():
    """Run garbage collection more frequently for aggressive cleanup"""
    while True:
        try:
            await asyncio.sleep(GC_COLLECT_INTERVAL_SEC)
            gc.collect()
        except Exception as e:
            logger.error(f"[MEM] error in periodic GC: {e}")

# MSG TYPE = H(eartbeat), A(ck), B(egin), E(nd), C(hunk), S(hortest path)

def radio_send(dest, data, msg_uid):
    # Input: dest: int, data: bytes; Output: None (sends bytes via LoRa, logs send)
    global sent_count
    sent_count = sent_count + 1
    lendata = len(data)
    if len(data) > 254:
        logger.error(f"[LORA] msg too large : {len(data)}")
        return
    #data = lendata.to_bytes(1) + data
    data = data.replace(b"\n", b"{}[]")
    # SX1262 send() doesn't take dest parameter - addressing is in the data payload
    try:
        len_sent, status = loranode.send(data)
        if status != ERR_NONE:
            logger.error(f"[LORA] Send failed with status {status}, MSG_UID = {msg_uid}, dest={dest}")
        # Map 0-210 bytes to 1-10 asterisks, anything above 210 = 10 asterisks
        data_masked_log = min(10, max(1, (len(data) + 20) // 21))
        logger.info(f"[⮕ SENT to {dest}] [{'*' * data_masked_log}] {len(data)} bytes, MSG_UID = {msg_uid}")
    except Exception as e:
        logger.error(f"[LORA] Exception in radio_send: {e}, MSG_UID = {msg_uid}")

def pop_and_get(msg_uid):
    # Input: msg_uid: bytes; Output: tuple(msg_uid, msgbytes, timestamp) removed from msgs_unacked or None
    for i in range(len(msgs_unacked)):
        m, d, t = msgs_unacked[i]
        if m == msg_uid:
            return msgs_unacked.pop(i)
    return None

async def send_single_packet(msg_typ, creator, msgbytes, dest, retry_count = 3):
    # Input: msg_typ: str, creator: int, msgbytes: bytes, dest: int; Output: tuple(success: bool, missing_chunks: list)
    msg_uid = get_msg_uid(msg_typ, creator, dest) # TODO, msg_uid used anywhere except logging
    databytes = msg_uid + b";" + msgbytes
    ackneeded = ack_needed(msg_typ)
    timesent = time_msec()
    if ackneeded:
        msgs_unacked.append((msg_uid, msgbytes, timesent))
    else:
        msgs_sent.append((msg_uid, msgbytes, timesent))
    if not ackneeded:
        radio_send(dest, databytes, msg_uid)
        await asyncio.sleep(MIN_SLEEP)
        return (True, [])
        ack_msg_recheck_count = 8 # Increased from 5 for better ACK detection at high speed
        for retry_i in range(retry_count):
            radio_send(dest, databytes, msg_uid)
            await asyncio.sleep(ACK_SLEEP)
            first_log_flag = True
            for i in range(ack_msg_recheck_count): # ack_msg recheck
                at, missing_chunks = ack_time(msg_uid)
                if at > 0:
                    logger.info(f"[ACK] Msg {msg_uid} : was acked in {at - timesent} msecs")
                    msgs_sent.append(pop_and_get(msg_uid))
                    return (True, missing_chunks)
                else:
                    if first_log_flag:
                        logger.info(f"[ACK] Still waiting for ack, MSG_UID =  {msg_uid} # {i}")
                        first_log_flag = False
                    else:
                        logger.debug(f"[ACK] Still waiting for ack, MSG_UID = {msg_uid} # {i}")
                    # Reduced sleep for faster ACK checking at high data rates
                    await asyncio.sleep(
                        ACK_SLEEP * min(i + 1, 2) / 2  # Faster checking: progressive but capped at 2x
                    )
            logger.warning(f"[ACK] Failed to get ack, MSG_UID = {msg_uid}, retry # {retry_i+1}/{retry_count}")
    logger.error(f"[LORA] Failed to send message, MSG_UID = {msg_uid}")
    return (False, [])

def make_chunks(msg):
    # Input: msg: bytes; Output: list of bytes chunks up to 200 bytes each
    chunks = []
    while len(msg) > 200:
        chunks.append(msg[0:200])
        msg = msg[200:]
    if len(msg) > 0:
        chunks.append(msg)
    return chunks

def encrypt_if_needed(msg_typ, msg):
    # Input: msg_typ: str message type, msg: bytes; Output: bytes (possibly encrypted message)
    if not ENCRYPTION_ENABLED:
        return msg
    if msg_typ in ["H", "T"]:
        # Must be less than 117 bytes
        if len(msg) > 117:
            logger.error(f"Message {msg} is lnger than 117 bytes, cant encrypt via RSA")
            return msg
        msgbytes = enc.encrypt_rsa(msg, encnode.get_pub_key())
        logger.info(f"{msg_typ} : Len msg = {len(msg)}, len msgbytes = {len(msgbytes)}")
        return msgbytes
    if msg_typ == "P":
        msgbytes = enc.encrypt_hybrid(msg, encnode.get_pub_key())
        logger.debug(f"{msg_typ} : Len msg = {len(msg)}, len msgbytes = {len(msgbytes)}")
        return msgbytes
    return msg

# === Send Function ===

async def send_msg_internal(msg_typ, creator, msgbytes, dest): # all messages except image
    if not is_lora_ready():
        return False
    # Input: msg_typ: str, creator: int, msgbytes: bytes, dest: int; Output: bool success indicator
    if len(msgbytes) < PACKET_PAYLOAD_LIMIT:
        logger.info(f"[⋙ sending....] dest={dest}, msg_typ:{msg_typ}, len:{len(msgbytes)} bytes, single packet")
        succ, _ = await send_single_packet(msg_typ, creator, msgbytes, dest)
        return succ
    else:
        logger.warning(f"msgbtyes size exceeds the packet payload limit, {len(msgbytes)} bytes > {PACKET_PAYLOAD_LIMIT} bytes")
        return False

async def send_msg_big(msg_typ, creator, msgbytes, dest, epoch_ms): # image sending
    if not is_lora_ready():
        return False
    if msg_typ == "P":
        img_id = get_rand()
        if get_transmode_lock(dest, img_id):
            asyncio.create_task(keep_transmode_lock(dest, img_id))
            # sending start
            chunks = make_chunks(msgbytes)
            logger.info(f"[⋙ sending....] dest={dest}, msg_typ:{msg_typ}, len:{len(msgbytes)} bytes, img_id:{img_id}, image_payload in {len(chunks)} chunks")
            big_succ, _ = await send_single_packet("B", creator, f"{img_id}:{epoch_ms}:{len(chunks)}", dest)
            if not big_succ:
                logger.info(f"[CHUNK] Failed sending chunk begin")
                delete_transmode_lock(dest, img_id)
                return False

            for i in range(len(chunks)):
                if i % 10 == 0:
                    logger.info(f"[CHUNK] Sending chunk {i}")
                await asyncio.sleep(CHUNK_SLEEP)
                chunkbytes = img_id.encode() + i.to_bytes(2) + chunks[i]
                _ = await send_single_packet("I", creator, chunkbytes, dest)
            for retry_i in range(20):
                if retry_i == 0:
                    await asyncio.sleep(0.1)  # Faster first check
                else:
                    await asyncio.sleep(CHUNK_SLEEP)
                succ, missing_chunks = await send_single_packet("E", creator, f"{img_id}:{epoch_ms}", dest, retry_count = 10)
                if not succ:
                    logger.error(f"[CHUNK] Failed sending chunk end")
                    break

                # Treat various ACK forms as success:
                # - [-1]   : explicit "all done" from receiver
                # - []/None: truncated or minimal ACK with no missing list (we assume success)
                if (
                    missing_chunks is None
                    or len(missing_chunks) == 0
                    or (len(missing_chunks) == 1 and missing_chunks[0] == -1)
                ):
                    logger.info(f"[CHUNK] Successfully sent all chunks (missing_chunks={missing_chunks})")
                    delete_transmode_lock(dest, img_id)
                    return True

                logger.info(
                    f"[CHUNK] Receiver still missing {len(missing_chunks)} chunks after retry {retry_i}: {missing_chunks}"
                )
                if not check_transmode_lock(dest, img_id): # check old logs is still in progress or not
                    logger.error(f"TRANS MODE ended, marking data send as failed, timeout error")
                    return False
                for mis_chunk in missing_chunks:
                    await asyncio.sleep(CHUNK_SLEEP)
                    chunkbytes = img_id.encode() + mis_chunk.to_bytes(2) + chunks[mis_chunk]
                    _ = await send_single_packet("I", creator, chunkbytes, dest)
            delete_transmode_lock(dest, img_id)
            return False
        else:
            logger.warning(f"TRANS MODE already in use, could not get lock...")
            return False
    else:
        logger.warning(f"Invalid message type: {msg_typ}")
        return False


async def send_msg(msg_typ, creator, msgbytes, dest):
    return await send_msg_internal(msg_typ, creator, msgbytes, dest)

def ack_time(msg_uid):
    # Input: msg_uid: bytes; Output: tuple(timestamp:int, missingids:list or None)
    for (recd_msg_uid, msgbytes, t) in msgs_recd:
        if chr(recd_msg_uid[0]) == "A":
            # Match ACK: the payload should start with the MID we're waiting for
            # Handle cases where payload might be exactly MIDLEN bytes or longer
            # Also handle cases where last byte might be missing (truncation issue)
            if len(msgbytes) >= MIDLEN - 1:  # Allow 1 byte shorter due to truncation
                # Try exact match first
                if len(msgbytes) >= MIDLEN and msg_uid == msgbytes[:MIDLEN]:
                    missingids = []
                    # For End (E) chunk messages, check for missing chunk IDs
                    if len(msgbytes) > MIDLEN and msgbytes[MIDLEN:MIDLEN+1] == b':':
                        # Format: MID:missing_ids or MID:-1
                        missing_str = msgbytes[MIDLEN+1:].decode()
                        if missing_str != "-1":
                            logger.info(f"[ACK] Checking for missing IDs in {missing_str}")
                            try:
                                missingids = [int(i) for i in missing_str.split(',') if i]
                            except ValueError:
                                logger.warning(f"[ACK] Failed to parse missing IDs: {missing_str}")
                                missingids = []
                    logger.debug(f"[ACK] Matched ACK for {msg_uid}, missing chunks: {missingids}")
                    return (t, missingids)
                # Try match with missing last byte (workaround for truncation issue)
                elif len(msgbytes) == MIDLEN - 1 and msg_uid[:MIDLEN-1] == msgbytes:
                    logger.debug(f"[ACK] Matched ACK for {msg_uid} with truncated payload (missing last byte)")
                    return (t, [])
            else:
                logger.debug(f"[ACK] ACK payload too short: {len(msgbytes)} bytes, expected at least {MIDLEN-1}")
    return (-1, None)


chunk_map = {} # chunk ID to (expected_chunks, [(iter, chunk_data)])

# ---------------------------------------------------------------------------
# Chunk Assembly Helpers
# ---------------------------------------------------------------------------

def begin_chunk(msg):
    # Input: msg: str formatted as "<type>:<chunk_id>:<num_chunks>"; Output: None (initializes chunk tracking)
    parts = msg.split(":")
    if len(parts) != 3:
        logger.error(f"[CHUNK] begin message unparsable {msg}")
        return
    img_id = parts[0]
    epoch_ms = int(parts[1])
    numchunks = int(parts[2])
    # Only initialize if not already present (handle duplicate B packets)
    if img_id not in chunk_map:
        chunk_map[img_id] = ("B", numchunks, [])
    return (img_id, epoch_ms, numchunks)


def get_missing_chunks(img_id):
    # Input: img_id: str chunk identifier; Output: list of int missing chunk indices
    if img_id not in chunk_map:
        #logger.info(f"Should never happen, have no entry in chunk_map for {img_id}")
        return []
    msg_typ, expected_chunks, list_chunks = chunk_map[img_id]
    missing_chunks = []
    for i in range(expected_chunks):
        if not get_data_for_iter(list_chunks, i):
            missing_chunks.append(i)
    return missing_chunks

def add_chunk(msgbytes):
    # Input: msgbytes: bytes containing chunk id + index + payload; Output: None (stores chunk data)
    if len(msgbytes) < 5:
        logger.error(f"[CHUNK] not enough bytes {len(msgbytes)} : {msgbytes}")
        return
    img_id = msgbytes[0:3].decode()
    citer = int.from_bytes(msgbytes[3:5])
    #logger.info(f"Got chunk id {citer}")
    cdata = msgbytes[5:]
    if img_id not in chunk_map:
        logger.error(f"[CHUNK] no entry yet for {img_id}")
        return
    chunk_map[img_id][2].append((citer, cdata))
    _, expected_chunks, _ = chunk_map[img_id]
    missing = get_missing_chunks(img_id)
    received = expected_chunks - len(missing)
    #logger.info(f" ===== Got {received} / {expected_chunks} chunks ====")

def get_data_for_iter(list_chunks, chunkiter):
    # Input: list_chunks: list of tuples(iter:int, data:bytes), chunkiter: int; Output: bytes or None for specific chunk
    for citer, chunk_data in list_chunks:
        if citer == chunkiter:
            return chunk_data
    return None

def recompile_msg(img_id):
    # Input: img_id: str chunk identifier; Output: bytes reconstructed message or None if incomplete
    if len(get_missing_chunks(img_id)) > 0:
        return None
    if img_id not in chunk_map:
        #logger.info(f"Should never happen, have no entry in chunk_map for {img_id}")
        return []
    msg_typ, expected_chunks, list_chunks = chunk_map[img_id]
    recompiled = b""
    for i in range(expected_chunks):
        recompiled += get_data_for_iter(list_chunks, i)
    # Ignoring message type for now
    return recompiled

def clear_chunkid(img_id):
    # Input: img_id: str chunk identifier; Output: None (removes chunk tracking entry)
    if img_id in chunk_map:
        entry = chunk_map.pop(img_id)
        # Explicitly delete chunk data to free memory
        if len(entry) > 2 and isinstance(entry[2], list):
            for _, chunk_data in entry[2]:
                del chunk_data
        del entry
        gc.collect()  # Help GC reclaim memory immediately
    else:
        logger.warning(f"[CHUNK] couldn't find {img_id} in {chunk_map}")

# Note only sends as many as wouldnt go beyond frame size
# Assumption is that subsequent end chunks would get the rest
def end_chunk(msg_uid, msg):
    # is_all_chunk_arrived, missing_chunk_str, img_id, recompiled_msgbytes, epoch_ms
    parts = msg.split(":")
    if len(parts) != 2:
        logger.error(f"[CHUNK] end message unparsable {msg}")
        return
    img_id = parts[0]
    epoch_ms = int(parts[1])

    creator = int(msg_uid[1])
    missing = get_missing_chunks(img_id)
    if len(missing) > 0:
        logger.info(f"[CHUNK] I am missing {len(missing)} chunks : {missing}")
        missing_str = str(missing[0])
        for i in range(1, len(missing)):
            if len(missing_str) + len(str(missing[i])) + 1 + MIDLEN + MIDLEN < PACKET_PAYLOAD_LIMIT:
                missing_str += "," + str(missing[i])
        return (False, missing_str, img_id, None, epoch_ms)
    else:
        if img_id not in chunk_map:
            logger.warning(f"[CHUNK] Ignoring end chunk, we dont have an entry for this img_id.., it might got processed already.")
            return (True, None, img_id, None, epoch_ms)
        recompiled_msgbytes = recompile_msg(img_id)
        return (True, None, img_id, recompiled_msgbytes, epoch_ms)

# ---------------------------------------------------------------------------
# Command Center Integration
# ---------------------------------------------------------------------------

async def init_sim():
    # Input: None; Output: bool indicating cellular initialization success (updates cellular_system)
    """Initialize the cellular connection"""
    global cellular_system
    logger.info("\n[CELL] === Initializing Cellular System ===")
    cellular_system = Cellular()
    if not cellular_system.initialize():
        logger.info("[CELL] Cellular initialization failed!")
        return False
    logger.info("[CELL] Cellular system ready")
    return True

async def sim_upload_hb(heartbeat_data): # TODO will be replaced by sim_upload_payload later
    # Input: heartbeat_data: dict payload; Output: bool indicating upload success
    """Send heartbeat data via cellular (for command center)"""
    global cellular_system

    if not cellular_system or not running_as_cc():
        return False

    try:
        result = cellular_system.upload_data(heartbeat_data, URL)
        if result and result.get('status_code') == 200:
            node_id = heartbeat_data["machine_id"]
            logger.info(f"[HB] Heartbeat from node {node_id} sent to cloud successfully")
            return True
        else:
            logger.error("[HB] failed to send heartbeat to cloud via cellular")
            if result:
                logger.info(f"[HB] HTTP Status: {result.get('status_code', 'Unknown')}")
            return False

    except Exception as e:
        logger.error(f"[HB] error sending cellular heartbeat: {e}")
        return False

async def upload_payload_to_server(payload, msg_typ, creator): # FINAL
    # Input: heartbeat_data: dict payload; Output: bool indicating upload success
    """Unified heartbeat upload: tries cellular first, falls back to WiFi"""
    if not running_as_cc():
        return False

    if cellular_system:
        result = await sim_upload_payload(payload, msg_typ, creator)
        if result:
            return True
        logger.warning(f"msg_typ:{msg_typ} from node {creator} cellular upload failed, trying WiFi fallback...")
    else:
        logger.warning(f"msg_typ:{msg_typ} from node {creator} cellular system not initialized, trying WiFi fallback...")

    if wifi_nic and wifi_nic.isconnected():
        result = await wifi_upload_payload(payload, msg_typ, creator)
        if result:
            return True
        logger.warning(f"msg_typ:{msg_typ} from node {creator} wifi upload failed, skipping upload...")
    else:
        logger.error(f"msg_typ:{msg_typ} from node {creator} wifi not connected, upload failed (cellular and WiFi both unavailable)")

    return False

async def sim_upload_payload(payload, msg_typ, creator): # FINAL
    # Input: payload_dict: dict payload; Output: bool indicating upload success
    """Send payload data via cellular (for command center)"""
    global cellular_system
    if not cellular_system or not running_as_cc():
        return False

    try:
        result = cellular_system.upload_data(payload, URL)
        if result and result.get('status_code') == 200:
            logger.info(f"msg_typ:{msg_typ} from node {creator} sent to cloud successfully")
            return True
        else:
            logger.error(f"msg_typ:{msg_typ} from node {creator} failed to send to cloud via cellular")
            if result:
                logger.info(f"HTTP Status: {result.get('status_code', 'Unknown')}")
            return False

    except Exception as e:
        logger.error(f"msg_typ:{msg_typ} from node {creator} error sending to cloud via cellular: {e}")
        return False

async def wifi_upload_payload(payload, msg_typ, creator): # FINAL
    # Input: payload: dict payload; msg_typ: str, creator: int; Output: bool upload success
    """Send payload via WiFi"""
    global wifi_nic
    if not wifi_nic or not wifi_nic.isconnected():
        logger.warning(f"msg_typ:{msg_typ} from node {creator} WiFi not connected")
        return False

    try:
        if USE_REQUESTS:
            try:
                headers = {"Content-Type": "application/json"}
                json_payload = json.dumps(payload)
                response = requests.post(URL, data=json_payload, headers=headers)
                if response.status_code == 200:
                    logger.info(f"msg_typ:{msg_typ} from node {creator} uploaded via WiFi successfully")
                    return True
                else:
                    # logger.error(f"msg_typ:{msg_typ} from node {creator} upload failed: status {response.status_code}, response {str(response)}")
                    # Get response body for detailed error information
                    try:
                        response_text = response.text
                    except:
                        response_text = "Unable to read response body"
                    try:
                        response_json = response.json()
                        error_details = f"JSON: {json.dumps(response_json)}"
                    except:
                        error_details = f"Text: {response_text[:500]}"  # Limit to first 500 chars
                    logger.error(f"msg_typ:{msg_typ} from node {creator} upload failed: status {response.status_code}, {error_details}")
                    return False
            except Exception as e:
                logger.error(f"msg_typ:{msg_typ} from node {creator} error in wifi_upload_payload: {e}")
                return False
        else:
            # Fallback to socket-based HTTP (not implemented for brevity)
            logger.warning(f"msg_typ:{msg_typ} from node {creator} requests library not available, WiFi upload skipped")
            return False

    except Exception as e:
        logger.error(f"msg_typ:{msg_typ} from node {creator} error in wifi_upload_payload: {e}")
        return False

# ---------------------------------------------------------------------------
# Message Handlers
# ---------------------------------------------------------------------------

hb_map = {}

async def hb_process(msg_uid, msgbytes, sender):
    # Input: msg_uid: bytes, msgbytes: bytes, sender: int; Output: None (routes or logs heartbeat data)
    creator = int(msg_uid[1])
    if running_as_cc():
        if creator not in hb_map:
            hb_map[creator] = 0
        hb_map[creator] += 1
        logger.info(f"[HB] HB Counts = {hb_map}")

        # Send raw heartbeat data (encrypted or not) to cloud
        # Convert bytes to base64 for JSON transmission, same as image data
        if isinstance(msgbytes, bytes):
            hb_data = ubinascii.b2a_base64(msgbytes)
        else:
            hb_data = msgbytes

        epoch_ms = get_epoch_ms()
        heartbeat_payload =  {
            "machine_id": creator,
            "message_type": "heartbeat",
            "heartbeat_data": hb_data,
            "epoch_ms": epoch_ms # TODO later with actual id
        }

        logger.info(f"[HB] Sending raw heartbeat data of length {len(msgbytes)} bytes")
        asyncio.create_task(upload_payload_to_server(heartbeat_payload, "heartbeat", creator))
        if ENCRYPTION_ENABLED:
            logger.debug(f"[HB] HB send msg = {enc.decrypt_rsa(msgbytes, encnode.get_prv_key(creator))}")
        else:
            logger.debug(f"[HB] HB send msg = {msgbytes.decode()}")
        return
    else:
        next_dst = next_device_in_spath()
        if next_dst:
            sent_succ = False
            logger.info(f"[HB] Propogating H to {next_dst}")
            sent_succ = await send_msg("H", creator, msgbytes, next_dst)
            if not sent_succ:
                logger.error(f"[HB] forwarding HB to {next_dst} failed")
        else:
            logger.error(f"[HB] can't forward HB because I dont have next device in spath yet")

images_saved_at_cc = []

async def event_text_process(creator, msgbytes):
    if running_as_cc():
        if isinstance(msgbytes, bytes):
            event_data = ubinascii.b2a_base64(msgbytes)
        else:
            event_data = msgbytes

        epoch_ms = get_epoch_ms()
        event_payload =  {
            "machine_id": creator,
            "message_type": "event_text",
            "event_data": event_data,
            "epoch_ms": epoch_ms # TODO not actual
        }
        logger.info(f"[TXT] Sending event text data of length {len(msgbytes)} bytes")
        asyncio.create_task(upload_payload_to_server(event_payload, "event_text", creator))
        return
    else:
        next_dst = next_device_in_spath()
        if next_dst:
            sent_succ = False
            logger.info(f"[TXT] Propogating event text to {next_dst}")
            sent_succ = await send_msg("T", creator, msgbytes, next_dst)
            if not sent_succ:
                logger.error(f"[TXT] forwarding event text to {next_dst} failed")
        else:
            logger.error(f"[TXT] can't forward event text because I dont have next device in spath yet")

# ---------------------------------------------------------------------------
# Sensor Capture and Image Transmission
# ---------------------------------------------------------------------------

imgpaths_to_send = [] # {creator, epoch_ms, enc_filepath}
events_to_send = [] # {creator, epoch_ms}
detector = detect.Detector()

# ============================================================================
# PIR SENSOR DETECTION: INTERRUPT-DRIVEN
# ============================================================================
# This implementation uses hardware interrupts - more efficient and responsive
# The task blocks waiting for PIR interrupt, only wakes when motion detected

# PIR Sensor Interrupt-driven Setup
pir_trigger_event = asyncio.Event()
pir_last_trigger_time = 0
PIR_DEBOUNCE_MS = 2000  # 2 seconds debounce to prevent multiple triggers from single motion

def pir_interrupt_handler(pin):
    """IRQ handler for PIR sensor - triggers on RISING edge (HIGH signal)"""
    global pir_last_trigger_time, pir_trigger_event
    current_time = utime.ticks_ms()
    # Debounce: ignore triggers within PIR_DEBOUNCE_MS of last trigger
    if utime.ticks_diff(current_time, pir_last_trigger_time) > PIR_DEBOUNCE_MS:
        pir_last_trigger_time = current_time
        # Set event to wake up person_detection_loop
        pir_trigger_event.set()
        # logger.info(f"[PIR] Motion detected (interrupt)")

async def person_detection_loop():
    # Input: None; Output: None (runs on PIR interrupt, updates counters and queue)
    global person_image_count, total_image_count, center_captured_image_count
    global pir_trigger_event, image_in_progress

    # Setup PIR sensor pin for interrupt
    # Get PIR pin from detect module
    from detect import PIR_PIN
    # Configure IRQ on RISING edge (when PIR goes HIGH)
    PIR_PIN.irq(trigger=Pin.IRQ_RISING, handler=pir_interrupt_handler)
    logger.info(f"[PIR] Interrupt-driven detection initialized on pin {PIR_PIN}")

    last_capture_time = None
    next_capture_wait = None # max value is 16
    MAX_CAPTURE_WAIT = 10
    FRESH_MOTION_LAP = 16
    while True:
        # Wait for PIR interrupt event (blocks until PIR detects motion)
        # Task is suspended here - uses minimal CPU until interrupt fires
        await pir_trigger_event.wait()
        # Clear the event for next trigger
        pir_trigger_event.clear()
        await asyncio.sleep(0.5) # DEFAULT wait after every motion

        # Exponential backoff sleep logic to prevent rapid-fire triggers
        curr_time = utime.time()  # Get current time in seconds
        if last_capture_time is None:
            last_capture_time = curr_time
            next_capture_wait = 2
            logger.info(f"[PIR] First motion detected - next_capture_wait={next_capture_wait}")
        else:
            # Calculate time difference since last trigger
            time_diff = curr_time - last_capture_time
            if time_diff<next_capture_wait:
                logger.info(f"[PIR] skipping detection - time diff:{time_diff} is too small, should be min:{next_capture_wait}s")
                continue
            else:
                if time_diff > FRESH_MOTION_LAP: # fresh movement detected
                    last_capture_time = curr_time
                    next_capture_wait = 2
                    logger.info(f"[PIR] Fresh motion detected - next_capture_wait={next_capture_wait}")
                else:
                    last_capture_time = curr_time
                    next_capture_wait = min(next_capture_wait * 2, MAX_CAPTURE_WAIT)
                    logger.info(f"[PIR] consecutive motion detected - next_capture_wait={next_capture_wait}")

        # Check if image processing is in progress
        # if image_in_progress:
        #     logger.info(f"[PIR] Skipping detection - image already in progress")
        #     continue

        # Motion detected - capture image
        img = None
        try:
            led.on()
            event_epoch_ms = get_epoch_ms() # epoch milisecond for event
            logger.info(f"[PIR] 🅾🅾🅾🅾🅾🅾❯❯ Motion detected - capturing image... ❮❮🅾🅾🅾🅾🅾🅾")
            img = sensor.snapshot()
            person_image_count += 1
            total_image_count += 1
            # Track center's own captured images separately
            if running_as_cc():
                center_captured_image_count += 1
            # imgbytes = img.bytearray() # this was bigger # TODO
            # logger.info(f"[OLD] Captured image, size: {len(imgbytes)} bytes")

            try:
                raw_path = f"{MY_IMAGE_DIR}/{my_addr}_{event_epoch_ms}_raw.jpg"
                logger.debug(f"Saving raw image to {raw_path} : imbytesize = {len(img.bytearray())}")
                async with lock:
                    img.save(raw_path)
                    os.sync()  # Force filesystem sync to SD card
                    utime.sleep_ms(500)
                logger.info(f"Saved raw image: {raw_path}: raw size = {len(img.bytearray())} bytes")
            except Exception as e:
                logger.warning(f"[PIR] Failed to save raw image: {e}")
                continue

            # read raw file
            try:
                img = image.Image(raw_path)
                imgbytes = img.bytearray() # updated
                logger.info(f"[PIR] Captured image, size: {len(imgbytes)} bytes")
            except Exception as e:
                logger.error(f"[PIR] Failed read image file: {e}")
                continue

            # Encrypt image immediately
            try:
                enc_msgbytes = encrypt_if_needed("P", imgbytes)
                enc_filepath = f"{MY_IMAGE_DIR}/{my_addr}_{event_epoch_ms}.enc"
                logger.debug(f"[PIR] Saving encrypted image to {enc_filepath} : encrypted size = {len(enc_msgbytes)} bytes...")
                # Save encrypted bytes to binary file
                async with lock:
                    with open(enc_filepath, "wb") as f:
                        f.write(enc_msgbytes)
                    os.sync()  # Force filesystem sync to SD card
                    utime.sleep_ms(500)
                logger.info(f"[PIR] Saved encrypted image: {enc_filepath}: encrypted size = {len(enc_msgbytes)} bytes")
            except Exception as e:
                logger.error(f"[PIR] Failed to save encrypted image: {e}")
                continue
            led.off()
            imgpaths_to_send.append({"creator": my_addr, "epoch_ms": event_epoch_ms, "enc_filepath": enc_filepath})

            # Limit queue size to prevent memory overflow
            if len(imgpaths_to_send) >= MAX_IMAGES_TO_SEND:
                # Remove oldest entry
                oldest = imgpaths_to_send.pop(0)
                logger.info(f"[PIR] Queue full, removing oldest image: {oldest['enc_filepath']}")

            # Save JSON file for the event
            event_filepath = f"{MY_EVENT_DIR}/{event_epoch_ms}.json"
            try:
                event_data = {"epoch_ms": event_epoch_ms}
                with open(event_filepath, "w") as f:
                    f.write(json.dumps(event_data))
                os.sync()  # Force filesystem sync to SD card
                utime.sleep_ms(500)
                logger.info(f"[PIR] Saved event file: {event_filepath}")
            except Exception as e:
                logger.error(f"[PIR] Failed to save event file {event_filepath}: {e}")
            events_to_send.append({"creator": my_addr, "epoch_ms": event_epoch_ms})

            # logger.info(f"Saved image: {raw_path}")
            # logger.info(f"Person detected Image count: {person_image_count}")
            # if running_as_cc():
            #     logger.info(f"Center captured images: {center_captured_image_count}")
        except Exception as e:
            logger.error(f"[PIR] unexpected error in image taking and saving: {e}")
        finally:
            # Explicitly clean up image object
            if img is not None:
                del img
                gc.collect()  # Help GC reclaim memory immediately


async def send_img_to_nxt_dst(creator, epoch_ms, enc_msgbytes):
    # Input: enc_msgbytes: bytes already encrypted image;
    # Output: bool indicating if image was forwarded successfully to next_node of spath
    logger.info(f"[IMG] Sending image of creator={creator}, size={len(enc_msgbytes)} bytes, to the network")
    try:
        next_dst = next_device_in_spath()
        if next_dst:
            if is_device_busy(next_dst):
                logger.warning(f"[IMG] Device {next_dst} is busy, skipping send")
                return False
            sent_succ = await send_msg_big("P", creator, enc_msgbytes, next_dst, epoch_ms)
            if sent_succ:
                return True
            else:
                logger.error(f"[IMG] forwarding image to {next_dst} failed")
                return False
        else:
            logger.error(f"[IMG] can't forward image because I dont have next device in spath yet")
            return False
    except Exception as e:
        logger.error(f"[IMG] unexpected error sending image to next device: {e}")
        return False

async def image_sending_loop():
    # Input: None; Output: None (periodically sends queued images across mesh)
    global imgpaths_to_send
    while True:
        await asyncio.sleep(PHOTO_SENDING_EMPTY_DELAY)
        if len(imgpaths_to_send) == 0:
            logger.debug("[IMG] No image event to send, skipping sending...")
            continue
        next_dst = next_device_in_spath()
        if not running_as_cc() and not next_dst:
            logger.warning("[IMG] No shortest path yet so cant send")
            continue

        if is_device_busy(next_dst):
            logger.debug(f"[IMG] Device {next_dst} is busy, skipping sending...")
            continue

        # Process all queued images one by one until queue is empty
        # This ensures all captured images get uploaded promptly
        # queue_size = len(imgpaths_to_send)
        # if queue_size > 0:
        #     logger.info(f"[IMG] Starting upload loop, {queue_size} images in queue")

        while len(imgpaths_to_send) > 0:
            queue_size = len(imgpaths_to_send)
            # logger.info(f"[IMG] Images to send = {queue_size}")
            img_entry = imgpaths_to_send.pop(0)
            enc_filepath = img_entry["enc_filepath"]
            creator = img_entry["creator"]
            epoch_ms = img_entry["epoch_ms"]

            logger.debug(f"[IMG] Processing: {enc_filepath}")
            enc_msgbytes = None
            try:
                # Read encrypted bytes directly from file
                try:
                    logger.debug(f"[IMG] Reading encrypted image of creator: {creator}, file: {enc_filepath}")
                    with open(enc_filepath, "rb") as f:
                        enc_msgbytes = f.read()
                    logger.debug(f"[IMG] Read encrypted image of creator: {creator}, file: {len(enc_msgbytes)} bytes")
                except Exception as e:
                    logger.error(f"[IMG] Failed to read encrypted image from file, image re-queued {enc_filepath}, e: {e}")
                    imgpaths_to_send.append(img_entry) # pushed to back of queue
                    break

                transmission_start = time_msec()
                if running_as_cc():
                    # Upload encrypted image directly (already encrypted)
                    logger.info(f"[IMG] ⋙⋙⋙ Uploading encrypted image (size: {len(enc_msgbytes)} bytes), file:{creator}_{epoch_ms}")
                    imgbytes = ubinascii.b2a_base64(enc_msgbytes)
                    img_payload =  {
                        "machine_id": creator,
                        "message_type": "event",
                        "image": imgbytes, # enc_msgbytes
                        "epoch_ms": epoch_ms,
                    }
                    sent_succ = await upload_payload_to_server(img_payload, "event", creator)
                    if not sent_succ:
                        imgpaths_to_send.append(img_entry) # pushed to back of queue
                        logger.warning(f"[IMG] upload_payload to server failed, image of creator={creator}, re-queued: {enc_filepath}")
                        break
                else:
                    logger.info(f"[IMG] ⋙⋙⋙ sending encrypted image to {next_dst}, file:{enc_filepath}")
                    sent_succ = await send_img_to_nxt_dst(creator, epoch_ms, enc_msgbytes)
                    if not sent_succ:
                        imgpaths_to_send.append(img_entry) # pushed to back of queue
                        logger.error(f"[IMG] sending image failed, re-queued: {enc_filepath}")
                        break

                transmission_end = time_msec()
                transmission_time = transmission_end - transmission_start
                logger.info(f"[IMG] ✔✔✔ Image transmission completed in {transmission_time} ms ({transmission_time/1000:.4f} seconds), file:{creator}_{epoch_ms}")
                # logger.info(f"[IMG] Remaining in queue: {len(imgpaths_to_send)}")

                # Wait a short interval before processing next image in queue
                # This prevents overwhelming the network/upload service
                if len(imgpaths_to_send) > 0:
                    await asyncio.sleep(PHOTO_SENDING_TRY_INTERVAL)
                else:
                    logger.info(f"[IMG] Queue empty, all images uploaded")

            except Exception as e:
                logger.error(f"[IMG] unexpected error processing image event {enc_filepath}: {e}, re-queued")
                # import sys
                # sys.print_exception(e)

                # Re-queue image on error
                imgpaths_to_send.append(img_entry) # TODO check this logic later
                break
            finally:
                # Explicitly clean up encrypted bytes
                # Variables are initialized before try block, so they should always exist
                # Use try-except for safety in case of unusual scoping issues
                try:
                    if imgbytes is not None:
                        if enc_msgbytes is not None and enc_msgbytes is not imgbytes:
                            del enc_msgbytes
                        del imgbytes
                    else:
                        if enc_msgbytes is not None: # imgbytes is None
                            del enc_msgbytes
                except NameError:
                    pass
                except:
                    pass
                # Help GC reclaim memory
                gc.collect()

        # After processing all queued images (or queue is empty), wait longer before checking again
        # Only use long delay if queue is empty to avoid missing new images
        if len(imgpaths_to_send) == 0:
            # Queue is empty, sleep longer
            await asyncio.sleep(PHOTO_SENDING_EMPTY_DELAY)
        if len(imgpaths_to_send) > 0:
            # Queue still has items (from failed uploads), check again soon
            await asyncio.sleep(PHOTO_SENDING_FAILED_PAUSE)


async def event_text_sending_loop():
    # Input: None; Output: None (periodically sends queued images across mesh)
    global events_to_send
    while True:
        await asyncio.sleep(EVENT_SENDING_EMPTY_DELAY)
        if len(events_to_send) == 0:
            logger.debug("[TXT] No message events to send, skipping sending...")
            continue
        next_dst = next_device_in_spath()
        if not running_as_cc() and not next_dst:
            logger.warning("[TXT] No shortest path yet so cant send")
            continue

        no_of_events = len(events_to_send)
        for i in range(no_of_events):
            event_entry = events_to_send.pop(0)
            epoch_ms = event_entry["epoch_ms"]
            logger.info(f"[TXT] ⋙⋙⋙ Processing event: {epoch_ms} ms")
            try:
                transmission_start = time_msec()
                sent_succ = await send_event_text(epoch_ms)
                if not sent_succ:
                    events_to_send.append(event_entry) # pushed to back of queue
                    logger.warning(f"[TXT] sending failed, event re-queued: {epoch_ms}")
                    break

                transmission_end = time_msec()
                transmission_time = transmission_end - transmission_start
                logger.info(f"[TXT] ✔✔✔ Event transmission completed in {transmission_time} ms ({transmission_time/1000:.4f} seconds)")

                if len(events_to_send) > 0:
                    await asyncio.sleep(EVENT_SENDING_INTERVAL)
                else:
                    logger.info(f"[TXT] Queue empty, all events uploaded")

            except Exception as e:
                logger.error(f"[TXT] unexpected error processing message event {epoch_ms}: {e}")
                import sys
                sys.print_exception(e)
                # Re-queue event on error
                events_to_send.append(event_entry)
                break
            finally:
                pass
                # TODO cleanup

        if len(events_to_send) == 0:
            await asyncio.sleep(EVENT_SENDING_INTERVAL)
        if len(events_to_send) == 0:
            await asyncio.sleep(EVENT_SENDING_FAILED_PAUSE)

# If N messages seen in the last M minutes.
def scan_process(msg_uid, msg):
    # Input: msg_uid: bytes, msg: bytes containing node address; Output: None (updates seen neighbours)
    nodeaddr = int.from_bytes(msg)
    if nodeaddr not in seen_neighbours:
        logger.info(f"adding nodeaddr {nodeaddr} to seen_neighbours")
        seen_neighbours.append(nodeaddr)

async def sync_and_transfer_spath(msg_uid, msg):
    # Input: msg_uid: bytes, msg: str shortest-path data; Output: None (updates shortest_path_to_cc and propagates)
    global shortest_path_to_cc
    if running_as_cc():
        logger.debug(f"Ignoring shortest path since I am cc")
        return
    if len(msg) == 0:
        logger.error(f"empty spath_received message received")
        return
    spath_received = [int(x) for x in msg.split(",")]
    if my_addr in spath_received:
        logger.debug(f"[cyclic, ignoring {my_addr} already in {spath_received}")
        return

    if len(shortest_path_to_cc) == 0:
        if len(seen_neighbours)>0:
            logger.debug(f"spath_recived for first time, saving and forwarding:{spath_received}")
        else:
            logger.debug(f"spath_recived for first time, saving:{spath_received}, but no 'seen_neighbour'")
        if DYNAMIC_SPATH:
            shortest_path_to_cc = spath_received
        for n in seen_neighbours:
            new_spath = [my_addr] + shortest_path_to_cc
            new_spath_msg = ",".join([str(x) for x in new_spath])
            logger.debug(f"propogating new_spath:{new_spath_msg}, to dst:{n}")
            asyncio.create_task(send_msg("S", int(msg_uid[1]), new_spath_msg.encode(), n))

    elif len(shortest_path_to_cc) > len(spath_received):
        if len(seen_neighbours)>0:
            logger.debug(f"smaller spath received, so updating and forwarding:{spath_received}")
        else:
            logger.debug(f"smaller spath received, so saving:{spath_received}, but no 'seen_neighbour'")
        if DYNAMIC_SPATH:
            shortest_path_to_cc = spath_received
        for n in seen_neighbours:
            new_spath = [my_addr] + shortest_path_to_cc
            new_spath_msg = ",".join([str(x) for x in new_spath])
            logger.debug(f"propogating new_spath:{new_spath_msg}, to dst:{n}")
            asyncio.create_task(send_msg("S", int(msg_uid[1]), new_spath_msg.encode(), n))
    elif len(shortest_path_to_cc) == len(spath_received):
        if len(seen_neighbours)>0:
            logger.debug(f"equal spath received, so updating and forwarding: {spath_received}")
        else:
            logger.debug(f"equal spath received, so updating: {spath_received}, but no 'seen_neighbour'")
        if DYNAMIC_SPATH:
            shortest_path_to_cc = spath_received
        for n in seen_neighbours:
            new_spath = [my_addr] + shortest_path_to_cc
            new_spath_msg = ",".join([str(x) for x in new_spath])
            logger.debug(f"propogating new_spath:{new_spath_msg}, to dst:{n}")
            asyncio.create_task(send_msg("S", int(msg_uid[1]), new_spath_msg.encode(), n))
    else:
        logger.info(f"larger spath received, so ignoring it: {spath_received}")

def process_message(data, rssi=None):
    # Input: data: bytes raw LoRa payload; rssi: int or None RSSI value in dBm; Output: bool indicating if message was processed

    parsed = parse_header(data)
    if not parsed:
        logger.error(f"[LORA] failure parsing incoming data : {data}")
        return False
    if random.randint(1,100) <= FLAKINESS:
        logger.warning(f"[LORA] flakiness dropping {data}")
        return True

    msg_uid, msg_typ, creator, sender, receiver, msg = parsed

    if DYNAMIC_SPATH:
        if not flayout.is_neighbour(sender, my_addr):
            logger.warning(f"[LORA/FAKE LAYOUT] receiving something which is beyond my range so dropping this packet {sender} : {parsed}")
            return True

    recv_log = ""
    if receiver == -1:
        recv_log = "⬇ BCAST"
    else:
        recv_log = "⬇ RECV"

    data_masked_log = min(10, max(1, (len(data) + 20) // 21))
    if rssi is not None:
        logger.info(f"[{recv_log} from {sender}, rssi: {rssi}] [{'*' * data_masked_log}] {len(data)} bytes, MSG_UID = {msg_uid}")
    else:
        logger.info(f"[{recv_log} from {sender}] [{'*' * data_masked_log}] {len(data)} bytes, MSG_UID = {msg_uid}")

    # logger.info(f"[PARSED HEADER] msg_uid:{msg_uid}, msg_typ:{msg_typ}, creator:{creator}, sender:{sender}, receiver:{receiver}, len-msg:{len(msg)}")
    if sender not in recv_msg_count:
        recv_msg_count[sender] = 0
    recv_msg_count[sender] += 1
    if receiver != -1 and my_addr != receiver:
        logger.warning(f"[LORA] skipping message as it is for dst:{receiver}, not for me (my_addr:{my_addr}), msg_uid:{msg_uid}")
        return
    msgs_recd.append((msg_uid, msg, time_msec()))
    ackmessage = msg_uid
    if msg_typ == "N": # N type msg from neighbours
        scan_process(msg_uid, msg)
    elif msg_typ == "V":
        asyncio.create_task(send_msg("A", my_addr, ackmessage, sender))
    elif msg_typ == "S":
        asyncio.create_task(sync_and_transfer_spath(msg_uid, msg.decode()))
    elif msg_typ == "T":
        asyncio.create_task(event_text_process(creator, msg))
        asyncio.create_task(send_msg("A", my_addr, ackmessage, sender))
    elif msg_typ == "H":
        # Validate HB message payload length for encrypted messages
        if ENCRYPTION_ENABLED:
            # RSA encrypted payload should be exactly 128 bytes
            if len(msg) != 128:
                logger.warning(
                    f"[HB] Invalid payload length: {len(msg)} bytes, expected 128 bytes for encrypted message. "
                    f"MID: {msg_uid}, may be corrupted or incomplete."
                )
                # Still try to process, but log the issue
        asyncio.create_task(hb_process(msg_uid, msg, sender))
        asyncio.create_task(send_msg("A", my_addr, ackmessage, sender))
    elif msg_typ == "W": # wait message
        asyncio.create_task(device_busy_life(sender))
    elif msg_typ == "B": # TODO need to ignore duplicate images, and send some response in A itself
        try:
            img_id, epoch_ms, numchunks = begin_chunk(msg.decode())
            # Check if this is a duplicate B packet for the same transfer
            if check_transmode_lock(sender, img_id):
                # Same sender and img_id - send ACK anyway (duplicate begin packet)
                logger.debug(f"[CHUNK] Duplicate B packet for same transfer, sending ACK")
                asyncio.create_task(send_msg("A", my_addr, ackmessage, sender))
            elif get_transmode_lock(sender, img_id):
                asyncio.create_task(keep_transmode_lock(sender, img_id))
                asyncio.create_task(send_msg("A", my_addr, ackmessage, sender))
            else:
                logger.warning(f"[CHUNK] TRANS MODE already in use for different transfer, sending W...")
                asyncio.create_task(send_msg("W", my_addr, WAIT_MESSAGE, sender))
                return False
        except Exception as e:
            logger.error(f"[CHUNK] decoding unicode {e} : {msg}")
            return False
    elif msg_typ == "I":
        add_chunk(msg)  # optional to check check_transmode_lock
    elif msg_typ == "E": #
        alldone, missing_str, img_id, recompiled_msgbytes, epoch_ms = end_chunk(msg_uid, msg.decode()) # TODO later, check how can we validate file
        if alldone:
            delete_transmode_lock(sender, img_id)
            # also when it fails
            ackmessage += b":-1"
            # asyncio.create_task(send_msg("A", creator, ackmessage, sender))
            async def send_ack_multiple(): # send ACK 2 times
                msg_count = 2
                for i in range(msg_count):
                    await send_msg("A", creator, ackmessage, sender)
                    if i < msg_count-1:
                        await asyncio.sleep(1)
            asyncio.create_task(send_ack_multiple())
            if recompiled_msgbytes:
                try:
                    enc_filepath = f"{MY_IMAGE_DIR}/{creator}_{epoch_ms}.enc"
                    logger.debug(f"[PIR] Saving encrypted image to {enc_filepath} : encrypted size = {len(recompiled_msgbytes)} bytes...")
                    with open(enc_filepath, "wb") as f:
                        f.write(recompiled_msgbytes)
                    os.sync()  # Force filesystem sync to SD card
                    utime.sleep_ms(500)
                    imgpaths_to_send.append({"creator": creator, "epoch_ms": epoch_ms, "enc_filepath": enc_filepath})
                    logger.info(f"[CHUNK] image saved to {enc_filepath}, adding to send queue")
                except Exception as e:
                    logger.error(f"[CHUNK] error saving image to {enc_filepath}: {e}")
                # asyncio.create_task(img_process(img_id, recompiled_msgbytes, creator, sender))
            else:
                logger.warning(f"[CHUNK] img not recompiled, so not sending")
        else:
            ackmessage += b":" + missing_str.encode()
            asyncio.create_task(send_msg("A", my_addr, ackmessage, sender))
    elif msg_typ == "A":
        # ACK messages are already added to msgs_recd at line 1267
        # They are matched by ack_time() function which searches msgs_recd
        # No additional processing needed for ACK messages
        logger.debug(f"[ACK] Received ACK message: {msg_uid}, payload: {msg}")
    else:
        logger.info(f"[LORA] Unseen messages type {msg_typ} in {msg}")
    return True

# ---------------------------------------------------------------------------
# LoRa Receive Loop
# ---------------------------------------------------------------------------

async def radio_read():
    logger.info(f"===> Radio Read, LoRa receive loop started... <===\n")
    # Input: None; Output: None (continuously receives LoRa packets and dispatches processing)
    loop_count = 0
    while True:
        # Safety check: wait for loranode to be initialized
        if loranode is None:
            logger.debug(f"[LORA] Waiting for LoRa initialization...")
            await asyncio.sleep(1)
            continue

        try:
            # Use blocking mode with timeout for async compatibility
            # Optimized timeout (200ms) for high-speed communication (SF5, BW500kHz)
            # Note: recv() internally uses blocking sleeps (sleep_ms), which blocks the async event loop
            # but the timeout ensures it returns after LORA_RX_TIMEOUT_MS
            loop_count += 1
            if loop_count == 1:
                logger.info(f"[LORA] Starting receive loop, loranode={loranode is not None}")
            elif loop_count % 100 == 0:  # Log every 100 iterations (~20 seconds with 200ms timeout)
                logger.info(f"[LORA] Receive loop running (iteration {loop_count})...")
            
            # This call will block for up to LORA_RX_TIMEOUT_MS (200ms)
            # During this time, the async event loop is blocked, but it will return after timeout
            # Note: recv() uses blocking sleep_ms() internally, which blocks the async event loop
            # This is acceptable as the timeout ensures it returns after LORA_RX_TIMEOUT_MS
            msg, status = loranode.recv(len=0, timeout_en=True, timeout_ms=LORA_RX_TIMEOUT_MS)

            if status == ERR_NONE:
                # Valid packet received
                if len(msg) > 0:
                    message = msg.replace(b"{}[]", b"\n")
                    rssi = loranode.getRSSI()  # Get RSSI after successful receive
                    process_message(message, rssi)
                else:
                    logger.debug(f"[LORA] Empty packet received")
            elif status == ERR_RX_TIMEOUT:
                # No packet received (expected, continue loop)
                pass
            elif status == ERR_CRC_MISMATCH:
                # Corrupted packet - log but try to process anyway for robustness
                logger.warning(f"[LORA] CRC error but attempting to process packet (len={len(msg)})")
                if len(msg) > 0:
                    message = msg.replace(b"{}[]", b"\n")
                    rssi = loranode.getRSSI()
                    # Try to process even with CRC error - some protocols can handle it
                    process_message(message, rssi)
            else:
                # Other error - log and continue
                logger.warning(f"[LORA] Receive error status: {status}")
        except Exception as e:
            logger.error(f"[LORA] Exception in radio_read: {e}")
            await asyncio.sleep(0.1)  # Brief pause on error

        # Small async sleep to yield to event loop (recv() uses blocking sleeps internally)
        # This prevents blocking the entire async event loop
        await asyncio.sleep(0.01)  # 10ms yield for async compatibility

# ---------------------------------------------------------------------------
# GPS Persistence Helpers
# ---------------------------------------------------------------------------

def get_gps_file_staleness():
    # Input: None; Output: int timestamp from GPS file or -1 if unavailable
    try:
        with open("gps_coordinate.txt", "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("Updated:"):
                    timestamp = int(line.split(":")[1].strip())
                    return timestamp
        return -1
    except:
        return -1

def read_gps_from_file():
    # Input: None; Output: str "lat,lon" or empty string if not available
    try:
        with open("gps_coordinate.txt", "r") as f:
            coords = f.readline().strip()
            if coords and ',' in coords:
                return coords
        return ""
    except:
        return ""


# ---------------------------------------------------------------------------
# Network Maintenance and Heartbeats
# ---------------------------------------------------------------------------

async def send_heartbeat():
    # Input: None; Output: bool indicating whether heartbeat was successfully sent to a neighbour
    gps_coords = read_gps_from_file()
    gps_staleness = get_gps_file_staleness()

    # my_addr : uptime (seconds) : photos taken : events seen : gpslat,gpslong : gps_staleness(seconds) : neighbours([221,222]) : shortest_path([221,9])
    hbmsgstr = f"{my_addr}:{time_sec()}:{total_image_count}:{person_image_count}:{gps_coords}:{gps_staleness}:{seen_neighbours}:{shortest_path_to_cc}"
    hbmsg = hbmsgstr.encode()
    msgbytes = encrypt_if_needed("H", hbmsg)
    sent_succ = False
    if running_as_cc():

        # Convert bytes to base64 for JSON transmission, same as hb_process()
        if isinstance(msgbytes, bytes):
            hb_data = ubinascii.b2a_base64(msgbytes)
        else:
            hb_data = msgbytes
        epoch_ms = get_epoch_ms()
        heartbeat_payload =  {
                "machine_id": my_addr,
                "message_type": "heartbeat",
                "heartbeat_data": hb_data,
                "epoch_ms": epoch_ms # TODO not actual
            }
        logger.info(f"[HB] sending raw HB to cloud, len={len(msgbytes)}, msg:{hbmsgstr}")
        sent_succ = await upload_payload_to_server(heartbeat_payload, "heartbeat", my_addr)
        return sent_succ
    else:
        next_dst = next_device_in_spath()
        if next_dst:
            sent_succ = await send_msg("H", my_addr, msgbytes, next_dst)
            if sent_succ:
                logger.info(f"[HB] Heartbeat sent successfully to {next_dst}")
                return True
        else:
            logger.error(f"[HB] can't send HB because I dont have next device in spath yet")
            return False
    return False


async def send_event_text(epoch_ms):
    # Input: None; Output: bool indicating whether heartbeat was successfully sent to a neighbour
    gps_coords = read_gps_from_file()
    gps_staleness = get_gps_file_staleness()

    event_msgstr = f"{my_addr}:{epoch_ms}:{gps_coords}:{gps_staleness}"
    # event_msgstr = f"{my_addr}:{epoch_ms}"
    event_msg = event_msgstr.encode()
    msgbytes = encrypt_if_needed("T", event_msg)
    sent_succ = False
    if running_as_cc():
        # Convert bytes to base64
        if isinstance(msgbytes, bytes):
            event_data = ubinascii.b2a_base64(msgbytes)
        else:
            event_data = msgbytes
        event_payload =  {
            "machine_id": my_addr,
            "message_type": "event_text",
            "event_data": event_data,
            "epoch_ms": epoch_ms
        }

        logger.info(f"[TXT] sending raw event text to cloud, len={len(msgbytes)}, msg:{event_msgstr}")
        sent_succ = await upload_payload_to_server(event_payload, "event_text", my_addr)
        return sent_succ
    else:
        next_dst = next_device_in_spath()
        if next_dst:
            sent_succ = await send_msg("T", my_addr, msgbytes, next_dst)
            if sent_succ:
                logger.info(f"[TXT] Event text sent successfully to {next_dst}")
                return True
        else:
            logger.error(f"[TXT] can't send event text because I dont have next device in spath yet")
            return False
    return False

async def keep_sending_heartbeat():
    # Input: None; Output: None (loops to periodically send heartbeats and handle retries)
    global consecutive_hb_failures
    i = 1
    print_pause = True
    print_resume = False
    while True:
        await asyncio.sleep(3)
        global image_in_progress
        if image_in_progress:
            if print_pause:
                logger.info(f"[HB] PAUSED")
            print_pause = False
            print_resume = True
            await asyncio.sleep(200)
            continue
        else:
            if print_resume:
                logger.info(f"[HB] RESUMED")
            print_resume = False
            print_pause = True

        # logger.info(f"In send HB loop, Shortest path = {shortest_path_to_cc}")
        sent_succ = await asyncio.create_task(send_heartbeat())
        if not sent_succ:
            consecutive_hb_failures += 1
            logger.warning(f"consecutive heartbeat failures = {consecutive_hb_failures}")
            if consecutive_hb_failures > 1:
                logger.error(f"Too many consecutive heartbeat failures, reinitializing LoRa...")
                try:
                    await init_lora()
                    consecutive_hb_failures = 0
                except Exception as e:
                    logger.error(f"reinitializing LoRa: {e}")
        else:
            logger.info(f"[HB] HB SUCCESS, shortest path = {shortest_path_to_cc}")
        i += 1
        if i < DISCOVERY_COUNT:
            await asyncio.sleep(HB_WAIT + random.randint(3,10))
        else:
            await asyncio.sleep(HB_WAIT_2 + random.randint(1, 120))

async def neighbour_scan():
    # Input: None; Output: None (broadcasts discovery messages periodically)
    global seen_neighbours
    i = 1
    while True:
        global image_in_progress
        if image_in_progress:
            logger.debug(f"skipping neighbour scan because image in progress")
            await asyncio.sleep(SCAN_WAIT)
            continue
        scanmsg = encode_node_id(my_addr)
        # 65535 is for Broadcast
        sent_succ = await send_msg("N", my_addr, scanmsg, 65535)
        if i < DISCOVERY_COUNT:
            await asyncio.sleep(SCAN_WAIT)
        else:
            await asyncio.sleep(SCAN_WAIT_2 + random.randint(1,120))
        logger.info(f"seen neighbours = {seen_neighbours}, Shortest path = {shortest_path_to_cc}, Sent messages = {sent_count}, Received messages = {recv_msg_count}")
        i = i + 1

async def validate_and_remove_neighbours():
    # Input: None; Output: None (verifies neighbours via ping and prunes unreachable ones)
    global shortest_path_to_cc
    logger.info(f"===> Validate/Remove, Neighbour validation loop started... <===\n")
    while True:
        global image_in_progress
        if image_in_progress:
            logger.debug(f"skipping neighbour validation because image in progress")
            await asyncio.sleep(200)
            continue

        logger.debug(f"starting neighbours validation: {seen_neighbours}")
        to_be_removed = []
        for n in seen_neighbours:

            # ---- waiting, just to not abort partial validation ----
            global image_in_progress
            waiting_retry = 5
            while image_in_progress:
                waiting_retry -= 1
                if waiting_retry <= 0:
                    logger.warning(f"image in progress, aborting neighbours validation loop")
                    break
                await asyncio.sleep(10)
            # ---- * -----

            msgbytes = b"Nothing"
            success = await send_msg("V", my_addr, msgbytes, n)
            if success:
                logger.debug(f"neighbour {n} is still within reach")
            else:
                to_be_removed.append(n)
                if DYNAMIC_SPATH and len(shortest_path_to_cc) and n == shortest_path_to_cc[0]: # first node not reachable
                    logger.warning(f"clearing shortest path to CC (unreachable neighbour {n})")
                    shortest_path_to_cc = []
        if len(to_be_removed):
            logger.warning(f"removing {len(to_be_removed)} unreachable neighbours: {to_be_removed}")
            for x in to_be_removed:
                seen_neighbours.remove(x)
        await asyncio.sleep(VALIDATE_WAIT_SEC)

async def initiate_spath_pings():
    # Input: None; Output: None (periodically shares shortest-path information with neighbours)
    i = 1
    while True:
        global image_in_progress
        if image_in_progress:
            logger.info(f"[NET] Skipping spath send because image in progress")
            await asyncio.sleep(200)
            continue
        sp = f"{my_addr}"
        for n in seen_neighbours:
            logger.info(f"[NET] Sending shortest path to {n}")
            await send_msg("S", my_addr, sp.encode(), n)
        i += 1
        if i < DISCOVERY_COUNT:
            await asyncio.sleep(SPATH_WAIT)
        else:
            await asyncio.sleep(SPATH_WAIT_2 + random.randint(1,120))

# ---------------------------------------------------------------------------
# Monitoring and Logging
# ---------------------------------------------------------------------------

async def print_summary_and_flush_logs():
    # Input: None; Output: None (periodically logs status metrics and flushes logs)
    while True:
        await asyncio.sleep(30)
        global image_in_progress
        if image_in_progress:
            logger.debug(f"TRANS MODE ongoing...")
            await asyncio.sleep(200)
            continue
        free_mem = get_free_memory()
        mem_str = f", Free: {free_mem/1024:.1f}KB" if free_mem > 0 else ""
        log_str = f"sent: {len(msgs_sent)} Recd: {len(msgs_recd)} Unacked: {len(msgs_unacked)}{mem_str}"
        if running_as_cc():
            logger.info(f"{log_str}, Chunks: {len(chunk_map)}, Images at CC (received): {len(images_saved_at_cc)}, Center captured: {center_captured_image_count}, Queued: {len(imgpaths_to_send)}")
        else:
            logger.info(f"{log_str}, Chunks: {len(chunk_map)}, Queued images: {len(imgpaths_to_send)}")
        #logger.info(msgs_sent)
        #logger.info(msgs_recd)
        #logger.info(msgs_unacked)

# ---------------------------------------------------------------------------
# GPS Acquisition Loop
# ---------------------------------------------------------------------------

async def keep_updating_gps():
    # Input: None; Output: None (continuously reads GPS hardware and updates global state)
    global gps_str, gps_last_time
    logger.info("[GPS] Initializing GPS...")

    # Wait for LoRa to settle
    await asyncio.sleep(3)

    try:
        uart = gps_driver.SC16IS750(spi_bus=1, cs_pin="P3")
        uart.init_gps()
        gps = gps_driver.GPS(uart)
        logger.info("[GPS] GPS hardware initialized successfully - starting continuous read loop")
    except Exception as e:
        logger.info(f"[GPS] GPS initialization failed: {e}")
        return

    read_count = 0
    last_successful_read = 0

    # Continuous reading loop
    while True:
        try:
            read_count += 1

            # Skip GPS if heavy operations are running
            if image_in_progress:
                await asyncio.sleep(GPS_WAIT_SEC * 2)
                continue

            # Clear any stale data in buffer first
            stale_data = uart.read_data()

            # Process fresh GPS data
            gps.update()

            if gps.has_fix():
                lat, lon = gps.get_coordinates()
                if lat is not None and lon is not None:
                    gps_str = f"{lat:.6f},{lon:.6f}"
                    logger.info(f"[GPS] {gps_str}")
                    gps_last_time = time_msec()
                    last_successful_read = read_count
                else:
                    if read_count % 10 == 1:
                        logger.info("[GPS] GPS has fix but no coordinates")
            else:
                if read_count % 20 == 1:
                    logger.info("[GPS] GPS has no fix")
                    # Show raw data for debugging
                    raw_debug = uart.read_data()
                    if raw_debug:
                        sample = raw_debug[:60].replace('\r', '\\r').replace('\n', '\\n')
                        logger.info(f"[GPS] GPS raw: {sample}")

            # Clear buffer periodically to prevent overflow
            if read_count % 30 == 0:
                while uart.read_data():  # Clear all buffered data
                    pass
                gps.buffer = ""  # Clear internal parser buffer
                logger.info("[GPS] GPS buffer cleared")

            # Reinitialize if too many failures
            if last_successful_read > 0 and (read_count - last_successful_read) > 100:
                logger.info("[GPS] GPS not working, reinitializing...")
                try:
                    uart.init_gps()
                    gps = gps_driver.GPS(uart)
                    await asyncio.sleep(2)
                    last_successful_read = read_count
                except Exception as e:
                    logger.error(f"[GPS] error in GPS reinit: {e}")
                    await asyncio.sleep(10)

        except Exception as e:
            logger.error(f"[GPS] error in GPS read: {e}")
            await asyncio.sleep(2)

        # Shorter sleep to prevent buffer overflow
        await asyncio.sleep(max(1, GPS_WAIT_SEC))  # At least 1 second

# ---------------------------------------------------------------------------
# WiFi Connection
# ---------------------------------------------------------------------------

async def init_wifi():
    # Input: None; Output: bool indicating if WiFi connection was successful
    global wifi_nic
    if not WIFI_ENABLED:
        logger.info("[WIFI] WiFi is disabled (WIFI_ENABLED = False)")
        return False

    try:
        logger.info(f"[WIFI] Initializing WiFi connection to SSID: {WIFI_SSID}")
        # Create WLAN interface in station mode
        wifi_nic = network.WLAN(network.WLAN.IF_STA)

        # Activate the interface
        wifi_nic.active(True)

        # Connect to WiFi access point
        logger.info(f"[WIFI] Connecting to WiFi network: {WIFI_SSID}")
        wifi_nic.connect(WIFI_SSID, WIFI_PASSWORD)

        # Wait for connection with timeout
        max_wait = 20  # Maximum wait time in seconds
        wait_count = 0
        while wait_count < max_wait:
            if wifi_nic.isconnected():
                # Connection successful
                ifconfig = wifi_nic.ifconfig()
                logger.info(f"[WIFI] WiFi connected successfully!, IP add: {ifconfig[0]}, Subnet mask: {ifconfig[1]}, Gateway: {ifconfig[2]}, DNS: {ifconfig[3]}")
                # logger.info(f"[WIFI] IP address: {ifconfig[0]}")
                # logger.info(f"[WIFI] Subnet mask: {ifconfig[1]}")
                # logger.info(f"[WIFI] Gateway: {ifconfig[2]}")
                # logger.info(f"[WIFI] DNS server: {ifconfig[3]}")
                return True

            # Check for connection errors (if status() is available)
            try:
                status = wifi_nic.status()
                # Try to detect common error statuses if constants exist
                if hasattr(network.WLAN, 'STAT_WRONG_PASSWORD') and status == network.WLAN.STAT_WRONG_PASSWORD:
                    logger.info(f"[WIFI] Connection failed: Wrong password")
                    wifi_nic.active(False)
                    return False
                elif hasattr(network.WLAN, 'STAT_NO_AP_FOUND') and status == network.WLAN.STAT_NO_AP_FOUND:
                    logger.info(f"[WIFI] Connection failed: Access point not found")
                    wifi_nic.active(False)
                    return False
                elif hasattr(network.WLAN, 'STAT_CONNECT_FAIL') and status == network.WLAN.STAT_CONNECT_FAIL:
                    logger.info(f"[WIFI] Connection failed: Connection failed")
                    wifi_nic.active(False)
                    return False
                logger.info(f"[WIFI] Connecting... (status: {status}, wait: {wait_count}s)")
            except Exception as e:
                # Status checking not available, just log wait time
                logger.warning(f"[WIFI] error in Connecting... (wait: {wait_count}s) : {e}")

            await asyncio.sleep(1)
            wait_count += 1

        # Timeout
        logger.error(f"[WIFI] Wifi connection timeout after {max_wait} seconds")
        wifi_nic.active(False)
        return False

    except Exception as e:
        logger.error(f"[WIFI] error in initialization: {e}")
        if wifi_nic:
            try:
                wifi_nic.active(False)
            except:
                pass
        return False


# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------
async def main():
    # Input: None; Output: None (entry point scheduling initialization and background tasks)
    global image_in_progress
    image_in_progress = False

    await init_lora()
    asyncio.create_task(radio_read())
    asyncio.create_task(print_summary_and_flush_logs())
    asyncio.create_task(validate_and_remove_neighbours())
    # Start memory management tasks
    asyncio.create_task(periodic_memory_cleanup())
    asyncio.create_task(periodic_gc())
    logger.info(f"[MEM] Memory management tasks started (free: {get_free_memory()/1024:.1f}KB)\n")
    if running_as_cc():
        logger.info(f"[INIT] ===> Starting command center node <===")
        # Initialize WiFi if enabled
        if WIFI_ENABLED:
            await init_wifi()

        # await init_sim()
        asyncio.create_task(neighbour_scan())
        await asyncio.sleep(2)
        asyncio.create_task(initiate_spath_pings()) # TODO enable for dynamic path
        await asyncio.sleep(1)
        asyncio.create_task(keep_sending_heartbeat())
        if len(IMAGE_CAPTURING_ADDRS)==0 or my_addr in IMAGE_CAPTURING_ADDRS:
            asyncio.create_task(person_detection_loop())
        else:
            logger.warning(f"[INIT] ===> Command center node {my_addr} is not enabled to capture images")
        asyncio.create_task(event_text_sending_loop())
        asyncio.create_task(image_sending_loop())
    else:
        logger.info(f"[INIT] ===> Starting unit node <===")
        asyncio.create_task(neighbour_scan())
        await asyncio.sleep(1)
        asyncio.create_task(keep_sending_heartbeat())
        await asyncio.sleep(2)
        asyncio.create_task(person_detection_loop())
        #asyncio.create_task(keep_updating_gps())
        # if len(IMAGE_CAPTURING_ADDRS)==0 or my_addr in IMAGE_CAPTURING_ADDRS:
        #     asyncio.create_task(person_detection_loop())
        # else:
        #     logger.warning(f"[INIT] ===> Unit node {my_addr} is not enabled to capture images")
        asyncio.create_task(event_text_sending_loop())
        asyncio.create_task(image_sending_loop())
    for i in range(24*7):
        await asyncio.sleep(3600)
        logger.info(f"Finished HOUR {i}")

try:
    asyncio.run(main())
except KeyboardInterrupt:
    logger.info("stopped by user via keyboard interrupt")
except Exception as e:
    logger.error(f"error in main.py: {e}")
finally:
    try:
        if 'logger' in globals():
            logger.close()
            logger.info("logger closed successfully")
    except Exception as e:
        logger.error(f"error in main.py: {e}")
