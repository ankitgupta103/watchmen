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
import sys
import random
import ubinascii
import network
import json
import gc                   # garbage collection for memory management

import enc
import sx1262
import gps_driver
from cellular_driver import Cellular
import detect

MIN_SLEEP = 0.1
ACK_SLEEP = 0.2
CHUNK_SLEEP = 0.3

DISCOVERY_COUNT = 100
HB_WAIT = 600
HB_WAIT_2 = 1200
SPATH_WAIT = 30
SPATH_WAIT_2 = 1200
SCAN_WAIT = 30
SCAN_WAIT_2 = 1200
VALIDATE_WAIT_SEC = 1200
PHOTO_TAKING_DELAY = 120
PHOTO_SENDING_DELAY = 250  # Delay after successful upload (when queue is empty)
PHOTO_SENDING_INTERVAL = 5  # Delay between uploads when queue has multiple images
GPS_WAIT_SEC = 5

# Memory Management Constants
MAX_MSGS_SENT = 500          # Maximum messages in sent buffer
MAX_MSGS_RECD = 500          # Maximum messages in received buffer
MAX_MSGS_UNACKED = 100       # Maximum unacknowledged messages
MAX_CHUNK_MAP_SIZE = 50      # Maximum chunk entries (chunk_id to chunks)
MAX_IMAGES_SAVED_AT_CC = 200 # Maximum image filenames to track at CC
MAX_IMAGES_TO_SEND = 50      # Maximum images in send queue
MAX_LOG_BUFFER_SIZE = 100    # Maximum log entries before flushing
MAX_OLD_MSG_AGE_SEC = 3600   # Age threshold (seconds) for cleaning old messages
MEM_CLEANUP_INTERVAL_SEC = 300  # Run memory cleanup every 5 minutes
GC_COLLECT_INTERVAL_SEC = 60    # Run garbage collection every minute

MIDLEN = 7
FLAKINESS = 0
FRAME_SIZE = 195

AIR_SPEED = 19200

ENCRYPTION_ENABLED = True

# WiFi Configuration
WIFI_SSID = "Airtel_anki_3363_2.4G"
WIFI_PASSWORD = "air34854"
WIFI_ENABLED = True

cellular_system = None
wifi_nic = None

# -------- Start FPS clock -----------
#clock = time.clock()            # measure frame/sec
person_image_count = 0                 # Counter to keep tranck of saved images
total_image_count = 0
center_captured_image_count = 0        # Counter for images captured on center device
gps_str = ""
gps_last_time = -1

consecutive_hb_failures = 0
lora_init_count = 0

image_in_progress = False

COMMAN_CENTER_ADDRS = [219, 223]
my_addr = None
shortest_path_to_cc = []
seen_neighbours = []

uid = binascii.hexlify(machine.unique_id())      # Returns 8 byte unique ID for board
# COMMAND CENTERS
if uid == b'e076465dd7194025':
    my_addr = 219
elif uid == b'e076465dd7090d1c':
    my_addr = 223

# OTHER NODES
elif uid == b'e076465dd7091027':
    my_addr = 221
    shortest_path_to_cc = [223]
elif uid == b'e076465dd7193a09':
    my_addr = 222
    shortest_path_to_cc = [223]
elif uid == b'e076465dd7091843':
    my_addr = 225
    shortest_path_to_cc = [223]

else:
    print("Error: Unknown device ID for " + omv.board_id())
    sys.exit()
clock_start = utime.ticks_ms() # get millisecond counter

rtc = RTC()
def get_human_ts():
    # Input: None; Output: str formatted as HH:MM:SS
    _,_,_,_,h,m,s,_ = rtc.datetime()
    return f"{h:02d}:{m:02d}:{s:02d}"

log_entries_buffer = []

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

def log(msg):
    # Input: msg: str; Output: None (side effects: buffer append and console log)
    t = get_human_ts()
    # log_entry = f"{my_addr}@{t} : {msg}"
    log_entry = f"{t} : {msg}"
    log_entries_buffer.append(log_entry)
    # Limit log buffer size to prevent memory overflow
    if len(log_entries_buffer) > MAX_LOG_BUFFER_SIZE:
        log_to_file()
    print(log_entry)



def running_as_cc():
    # Input: None; Output: bool indicating if this device is the command center
    return my_addr in COMMAN_CENTER_ADDRS

def get_fs_root_for_storage():
    # Input: None; Output: str path for filesystem root
    has_sdcard = True
    try:
        os.listdir('/sdcard')
        log("[FS] SD card available")
    except OSError:
        log("[FS] ERROR: SD card not found!")
        has_sdcard = False

    if has_sdcard:
        return "/sdcard"
    else:
        return "/flash"

FS_ROOT = get_fs_root_for_storage()
log(f"[FS] Using FS_ROOT : {FS_ROOT}")
MY_IMAGE_DIR = f"{FS_ROOT}/myimages"
NET_IMAGE_DIR = f"{FS_ROOT}/netimages"

def create_dir_if_not_exists(dir_path):
    try:
        parts = [p for p in dir_path.split('/') if p]
        if len(parts) < 2:
            log(f"[FS] WARNING: Invalid directory path (no parent): {dir_path}")
            return
        parent = '/' + '/'.join(parts[:-1])
        dir_name = parts[-1]
        if dir_name not in os.listdir(parent):
            os.mkdir(dir_path)
            log(f"[FS] Created {dir_path}")
        else:
            log(f"[FS] {dir_path} already exists")
    except OSError as e:
        log(f"[FS] ERROR: Failed to create/access {dir_path}: {e}")

create_dir_if_not_exists(NET_IMAGE_DIR)
create_dir_if_not_exists(MY_IMAGE_DIR)

LOG_FILE_PATH = f"{FS_ROOT}/mainlog.txt"

log(f"[INIT] MyAddr = {my_addr}")
encnode = enc.EncNode(my_addr)
log(f"[INIT] Logs will be written at {LOG_FILE_PATH}")


log("[INIT] Running on device : " + uid.decode())

def log_to_file():
    # Input: None; Output: None (writes buffered log entries to log file)
    with open(LOG_FILE_PATH, "a") as log_file:
        global log_entries_buffer
        tmp = log_entries_buffer
        log_entries_buffer = []
        # log(f"Writing {len(tmp)} lines to logfile")
        for x in tmp:
            log_file.write(x + "\n")
        log_file.flush()

def time_msec():
    # Input: None; Output: int milliseconds since clock_start
    delta = utime.ticks_diff(utime.ticks_ms(), clock_start) # compute time difference
    return delta

def time_sec():
    # Input: None; Output: int seconds since clock_start
    return int(utime.ticks_diff(utime.ticks_ms(), clock_start) / 1000) # compute time difference

def get_rand():
    # Input: None; Output: str random 3-letter uppercase identifier
    rstr = ""
    for i in range(3):
        rstr += chr(65+random.randint(0,25))
    return rstr

# TypeSourceDestRRRandom
def encode_node_id(node_id):
    # Input: node_id: int; Output: single-byte representation
    if not isinstance(node_id, int):
        raise TypeError(f"Node id must be int, got {type(node_id)}")
    if not 0 <= node_id <= 255:
        raise ValueError(f"Node id {node_id} out of range (0-255)")
    return bytes((node_id,))

def encode_dest(dest):
    # Input: dest: int; Output: single-byte representation or broadcast marker
    if dest in (0, 65535):
        return b'*'
    return encode_node_id(dest)

def get_msg_id(msgtype, creator, dest):
    # Input: msgtype: str, creator: int, dest: int; Output: bytes message identifier
    rrr = get_rand()
    mid = (
        msgtype.encode()
        + encode_node_id(creator)
        + encode_node_id(my_addr)
        + encode_dest(dest)
        + rrr.encode()
    )
    return mid

def parse_header(data):
    # Input: data: bytes; Output: tuple(mid, mst, creator, sender, receiver, msg) or None
    mid = b""
    if data == None:
        log(f"[LORA] Weird that data is none")
        return None
    if len(data) < 9:
        return None
    try:
        mid = data[:MIDLEN]
    except Exception as e:
        log(f"[LORA] ERROR: PARSING {data[:MIDLEN]}  :  Error : {e}")
        return
    mst = chr(mid[0])
    creator = int(mid[1])
    sender = int(mid[2])
    if mid[3] == 42 or mid == b"*":
        receiver = -1
    else:
        receiver=int(mid[3])
    if chr(data[MIDLEN]) != ';':
        return None
    msg = data[MIDLEN+1:]
    return (mid, mst, creator, sender, receiver, msg)

def ellepsis(msg):
    # Input: msg: str; Output: str truncated with ellipsis if necessary
    if len(msg) > 200:
        return msg[:100] + "......." + msg[-100:]
    return msg

def ack_needed(msgtype):
    # Input: msgtype: str; Output: bool indicating if acknowledgement required
    if msgtype == "A":
        return False
    if msgtype in ["H", "B", "E", "V"]:
        return True
    return False

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.HD)
sensor.skip_frames(time=2000)

sent_count = 0
recv_msg_count = {}

URL = "https://n8n.vyomos.org/webhook/watchmen-detect/"

# ---------------------------------------------------------------------------
# Image Lock Coordination
# ---------------------------------------------------------------------------

async def acquire_image_lock():
    # Input: None; Output: None (sets image_in_progress flag with auto release after timeout)
    global image_in_progress
    log(f"[IMG] Acquiring Image Lock")
    image_in_progress = True
    await asyncio.sleep(120)
    if image_in_progress:
        log(f"[IMG] Releasing image lock after 120 seconds, current lock state = {image_in_progress}")
    image_in_progress = False

def release_image_lock():
    # Input: None; Output: None (clears image_in_progress flag)
    log(f"[IMG] Releasing Image Lock")
    global image_in_progress
    image_in_progress = False

# ---------------------------------------------------------------------------
# Network Topology Helpers
# ---------------------------------------------------------------------------

def possible_paths(sender=None):
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

loranode = None

# ---------------------------------------------------------------------------
# LoRa Setup and Transmission
# ---------------------------------------------------------------------------

async def init_lora():
    # Input: None; Output: None (initializes global loranode, updates lora_reinit_count)
    global loranode, lora_init_count
    lora_init_count += 1
    log(f"[LORA] Initializing LoRa SX126X module... my lora addr = {my_addr}")
    loranode = sx1262.sx126x(
        uart_num=1,        # UART port number - adjust as needed
        freq=868,          # Frequency in MHz
        addr=my_addr,      # Node address
        power=22,          # Transmission power in dBm
        rssi=False,         # Enable RSSI reporting
        air_speed=AIR_SPEED,# Air data rate
        m0_pin='P6',       # M0 control pin - adjust to your wiring
        m1_pin='P7'        # M1 control pin - adjust to your wiring
    )

    # log(f"LoRa module (Total Initializations: {lora_init_count})")
    # log(f"Node address: {loranode.addr}")
    # log(f"Frequency: {loranode.start_freq + loranode.offset_freq}.125MHz")
    # log(f"===> LoRa module initialized successfully! <===\n")

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
    msgs_sent = [(mid, msg, t) for mid, msg, t in msgs_sent
                 if (current_time - t) < age_threshold_ms]
    # Also limit by size
    if len(msgs_sent) > MAX_MSGS_SENT:
        msgs_sent = msgs_sent[-MAX_MSGS_SENT:]
        log(f"[MEM] Trimmed msgs_sent to {MAX_MSGS_SENT} entries")

    # Clean msgs_recd - remove messages older than threshold
    msgs_recd = [(mid, msg, t) for mid, msg, t in msgs_recd
                 if (current_time - t) < age_threshold_ms]
    # Also limit by size
    if len(msgs_recd) > MAX_MSGS_RECD:
        msgs_recd = msgs_recd[-MAX_MSGS_RECD:]
        log(f"[MEM] Trimmed msgs_recd to {MAX_MSGS_RECD} entries")

    # Clean msgs_unacked - remove very old unacked messages (they likely failed)
    old_unacked = []
    new_unacked = []
    for mid, msg, t in msgs_unacked:
        age = current_time - t
        if age > age_threshold_ms * 2:  # Double threshold for unacked (more lenient)
            old_unacked.append(mid)
        else:
            new_unacked.append((mid, msg, t))
    msgs_unacked = new_unacked

    if len(old_unacked) > 0:
        log(f"[MEM] Removed {len(old_unacked)} old unacked messages")

    # Also limit by size
    if len(msgs_unacked) > MAX_MSGS_UNACKED:
        # Remove oldest ones
        msgs_unacked.sort(key=lambda x: x[2])  # Sort by timestamp
        msgs_unacked = msgs_unacked[-MAX_MSGS_UNACKED:]
        log(f"[MEM] Trimmed msgs_unacked to {MAX_MSGS_UNACKED} entries")

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
        log(f"[MEM] Cleaned {entries_to_remove} old chunk_map entries")

def cleanup_cc_images_list():
    """Clean up the images_saved_at_cc list if too large"""
    global images_saved_at_cc
    if len(images_saved_at_cc) > MAX_IMAGES_SAVED_AT_CC:
        # Keep only the most recent entries
        images_saved_at_cc = images_saved_at_cc[-MAX_IMAGES_SAVED_AT_CC:]
        log(f"[MEM] Trimmed images_saved_at_cc to {MAX_IMAGES_SAVED_AT_CC} entries")

async def periodic_memory_cleanup():
    """Periodically clean up memory buffers and run garbage collection"""
    while True:
        try:
            await asyncio.sleep(MEM_CLEANUP_INTERVAL_SEC)
            free_before = get_free_memory()

            log(f"[MEM] Starting memory cleanup (free: {free_before/1024:.1f}KB)")

            # Clean up message buffers
            cleanup_old_messages()

            # Clean up chunk map
            cleanup_chunk_map()

            # Clean up CC images list
            if running_as_cc():
                cleanup_cc_images_list()

            # Run garbage collection
            gc.collect()

            free_after = get_free_memory()
            freed = free_after - free_before if free_before > 0 and free_after > 0 else 0
            log(f"[MEM] Cleanup complete (free: {free_after/1024:.1f}KB, freed: {freed/1024:.1f}KB)")
            log(f"[MEM] Buffers - sent:{len(msgs_sent)}, recd:{len(msgs_recd)}, unacked:{len(msgs_unacked)}, chunks:{len(chunk_map)}")

        except Exception as e:
            log(f"[MEM] Error in memory cleanup: {e}")

async def periodic_gc():
    """Run garbage collection more frequently for aggressive cleanup"""
    while True:
        try:
            await asyncio.sleep(GC_COLLECT_INTERVAL_SEC)
            gc.collect()
        except Exception as e:
            log(f"[MEM] Error in periodic GC: {e}")

# MSG TYPE = H(eartbeat), A(ck), B(egin), E(nd), C(hunk), S(hortest path)

def radio_send(dest, data):
    # Input: dest: int, data: bytes; Output: None (sends bytes via LoRa, logs send)
    global sent_count
    sent_count = sent_count + 1
    lendata = len(data)
    if len(data) > 254:
        log(f"[LORA] ERROR: msg too large : {len(data)}")
    #data = lendata.to_bytes(1) + data
    data = data.replace(b"\n", b"{}[]")
    loranode.send(dest, data)
    log(f"[SENT {len(data)} bytes to {dest}] {data} at {time_msec()}")

def pop_and_get(mid):
    # Input: mid: bytes; Output: tuple(mid, msgbytes, timestamp) removed from msgs_unacked or None
    for i in range(len(msgs_unacked)):
        m, d, t = msgs_unacked[i]
        if m == mid:
            return msgs_unacked.pop(i)
    return None

async def send_single_msg(msgtype, creator, msgbytes, dest):
    # Input: msgtype: str, creator: int, msgbytes: bytes, dest: int; Output: tuple(success: bool, missing_chunks: list)
    mid = get_msg_id(msgtype, creator, dest)
    databytes = mid + b";" + msgbytes
    ackneeded = ack_needed(msgtype)
    unackedid = 0
    timesent = time_msec()
    if ackneeded:
        unackedid = len(msgs_unacked)
        msgs_unacked.append((mid, msgbytes, timesent))
    else:
        msgs_sent.append((mid, msgbytes, timesent))
    if not ackneeded:
        radio_send(dest, databytes)
        await asyncio.sleep(MIN_SLEEP)
        return (True, [])
    for retry_i in range(3):
        radio_send(dest, databytes)
        await asyncio.sleep(ACK_SLEEP)
        for i in range(8):
            at, missing_chunks = ack_time(mid)
            if at > 0:
                log(f"[ACK] Msg {mid} : was acked in {at - timesent} msecs")
                msgs_sent.append(pop_and_get(mid))
                return (True, missing_chunks)
            else:
                log(f"[ACK] Still waiting for ack for {mid} # {i}")
                await asyncio.sleep(ACK_SLEEP * (i+1)) # progressively more sleep
        log(f"[ACK] Failed to get ack for message {mid} for retry # {retry_i}")
    log(f"[LORA] Failed to send message {mid}")
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

def encrypt_if_needed(mst, msg):
    # Input: mst: str message type, msg: bytes; Output: bytes (possibly encrypted message)
    if not ENCRYPTION_ENABLED:
        return msg
    if mst in ["H"]:
        # Must be less than 117 bytes
        if len(msg) > 117:
            log(f"Message {msg} is lnger than 117 bytes, cant encrypt via RSA")
            return msg
        msgbytes = enc.encrypt_rsa(msg, encnode.get_pub_key())
        log(f"{mst} : Len msg = {len(msg)}, len msgbytes = {len(msgbytes)}")
        return msgbytes
    if mst == "P":
        msgbytes = enc.encrypt_hybrid(msg, encnode.get_pub_key())
        log(f"{mst} : Len msg = {len(msg)}, len msgbytes = {len(msgbytes)}")
        return msgbytes
    return msg

# === Send Function ===
async def send_msg_internal(msgtype, creator, msgbytes, dest):
    # Input: msgtype: str, creator: int, msgbytes: bytes, dest: int; Output: bool success indicator
    if msgtype == "P":
        log(f"[LORA] Sending photo of length {len(msgbytes)}")
    if len(msgbytes) < FRAME_SIZE:
        succ, _ = await send_single_msg(msgtype, creator, msgbytes, dest)
        return succ
    imid = get_rand()
    chunks = make_chunks(msgbytes)
    log(f"[CHUNK] Chunking {len(msgbytes)} long message with id {imid} into {len(chunks)} chunks")
    succ, _ = await send_single_msg("B", creator, f"{msgtype}:{imid}:{len(chunks)}", dest)
    if not succ:
        log(f"[CHUNK] Failed sending chunk begin")
        return False
    for i in range(len(chunks)):
        asyncio.create_task(acquire_image_lock())
        if i % 10 == 0:
            log(f"[CHUNK] Sending chunk {i}")
        await asyncio.sleep(CHUNK_SLEEP)
        chunkbytes = imid.encode() + i.to_bytes(2) + chunks[i]
        _ = await send_single_msg("I", creator, chunkbytes, dest)
    for retry_i in range(50):
        await asyncio.sleep(CHUNK_SLEEP)
        succ, missing_chunks = await send_single_msg("E", creator, imid, dest)
        if not succ:
            log(f"[CHUNK] Failed sending chunk end")
            break
        if len(missing_chunks) == 1 and missing_chunks[0] == -1:
            log(f"[CHUNK] Successfully sent all chunks")
            return True
        log(f"[CHUNK] Receiver still missing {len(missing_chunks)} chunks after retry {retry_i}: {missing_chunks}")
        for mc in missing_chunks:
            await asyncio.sleep(CHUNK_SLEEP)
            chunkbytes = imid.encode() + mc.to_bytes(2) + chunks[mc]
            asyncio.create_task(acquire_image_lock())
            _ = await send_single_msg("I", creator, chunkbytes, dest)
    return False

async def send_msg(msgtype, creator, msgbytes, dest):
    # Input: msgtype: str, creator: int, msgbytes: bytes, dest: int; Output: bool success indicator
    retval = await send_msg_internal(msgtype, creator, msgbytes, dest)
    return retval

def ack_time(smid):
    # Input: smid: bytes; Output: tuple(timestamp:int, missingids:list or None)
    for (rmid, msgbytes, t) in msgs_recd:
        if chr(rmid[0]) == "A":
            if smid == msgbytes[:MIDLEN]:
                missingids = []
                if chr(msgbytes[0]) == 'E' and len(msgbytes) > (MIDLEN+1):
                    log(f"[ACK] Checking for missing IDs in {msgbytes[MIDLEN+1:]}")
                    missingstr = msgbytes[MIDLEN+1:].decode()
                    missingids = [int(i) for i in missingstr.split(',')]
                return (t, missingids)
    return (-1, None)

async def log_status():
    # Input: None; Output: None (logs transmission statistics)
    await asyncio.sleep(1)
    log("[STATUS] $$$$ %%%%% ###### Printing status ###### $$$$$$ %%%%%%%%")
    log(f"[STATUS] So far sent {len(msgs_sent)} messages and received {len(msgs_recd)} messages")
    ackts = []
    msgs_not_acked = []
    for mid, msg, t in msgs_sent:
        if mid[0] == b"A":
            continue
        #log("Getting ackt for " + s + "which was sent at " + str(t))
        ackt, _ = ack_time(mid)
        if ackt > 0:
            time_to_ack = ackt - t
            ackts.append(time_to_ack)
        else:
            msgs_not_acked.append(mid)
    if ackts:
        ackts.sort()
        mid = ackts[len(ackts)//2]
        p90 = ackts[int(len(ackts) * 0.9)]
        log(f"[ACK Times] 50% = {mid:.2f}s, 90% = {p90:.2f}s")
        log(f"[STATUS] So far {len(msgs_not_acked)} messsages havent been acked")
        log(f"[STATUS] {msgs_not_acked}")

chunk_map = {} # chunk ID to (expected_chunks, [(iter, chunk_data)])

# ---------------------------------------------------------------------------
# Chunk Assembly Helpers
# ---------------------------------------------------------------------------

def begin_chunk(msg):
    # Input: msg: str formatted as "<type>:<chunk_id>:<num_chunks>"; Output: None (initializes chunk tracking)
    parts = msg.split(":")
    if len(parts) != 3:
        log(f"[CHUNK] ERROR: begin message unparsable {msg}")
        return
    mst = parts[0]
    cid = parts[1]
    numchunks = int(parts[2])
    chunk_map[cid] = (mst, numchunks, [])

def get_missing_chunks(cid):
    # Input: cid: str chunk identifier; Output: list of int missing chunk indices
    if cid not in chunk_map:
        #log(f"Should never happen, have no entry in chunk_map for {cid}")
        return []
    mst, expected_chunks, list_chunks = chunk_map[cid]
    missing_chunks = []
    for i in range(expected_chunks):
        if not get_data_for_iter(list_chunks, i):
            missing_chunks.append(i)
    return missing_chunks

def add_chunk(msgbytes):
    # Input: msgbytes: bytes containing chunk id + index + payload; Output: None (stores chunk data)
    if len(msgbytes) < 5:
        log(f"[CHUNK] ERROR: Not enough bytes {len(msgbytes)} : {msgbytes}")
        return
    asyncio.create_task(acquire_image_lock())
    cid = msgbytes[0:3].decode()
    citer = int.from_bytes(msgbytes[3:5])
    #log(f"Got chunk id {citer}")
    cdata = msgbytes[5:]
    if cid not in chunk_map:
        log(f"[CHUNK] ERROR: no entry yet for {cid}")
        return
    chunk_map[cid][2].append((citer, cdata))
    _, expected_chunks, _ = chunk_map[cid]
    missing = get_missing_chunks(cid)
    received = expected_chunks - len(missing)
    #log(f" ===== Got {received} / {expected_chunks} chunks ====")

def get_data_for_iter(list_chunks, chunkiter):
    # Input: list_chunks: list of tuples(iter:int, data:bytes), chunkiter: int; Output: bytes or None for specific chunk
    for citer, chunk_data in list_chunks:
        if citer == chunkiter:
            return chunk_data
    return None

def recompile_msg(cid):
    # Input: cid: str chunk identifier; Output: bytes reconstructed message or None if incomplete
    if len(get_missing_chunks(cid)) > 0:
        return None
    if cid not in chunk_map:
        #log(f"Should never happen, have no entry in chunk_map for {cid}")
        return []
    mst, expected_chunks, list_chunks = chunk_map[cid]
    recompiled = b""
    for i in range(expected_chunks):
        recompiled += get_data_for_iter(list_chunks, i)
    # Ignoring message type for now
    return recompiled

def clear_chunkid(cid):
    # Input: cid: str chunk identifier; Output: None (removes chunk tracking entry)
    if cid in chunk_map:
        entry = chunk_map.pop(cid)
        # Explicitly delete chunk data to free memory
        if len(entry) > 2 and isinstance(entry[2], list):
            for _, chunk_data in entry[2]:
                del chunk_data
        del entry
        gc.collect()  # Help GC reclaim memory immediately
    else:
        log(f"[CHUNK] Couldnt find {cid} in {chunk_map}")

# Note only sends as many as wouldnt go beyond frame size
# Assumption is that subsequent end chunks would get the rest
def end_chunk(mid, msg):
    # Input: mid: bytes message id, msg: str chunk identifier; Output: tuple(status:bool, missing:str|None, cid:str|None, data:bytes|None, creator:int|None)
    cid = msg
    creator = int(mid[1])
    missing = get_missing_chunks(cid)
    log(f"[CHUNK] I am missing {len(missing)} chunks : {missing}")
    if len(missing) > 0:
        missing_str = str(missing[0])
        for i in range(1, len(missing)):
            if len(missing_str) + len(str(missing[i])) + 1 + MIDLEN + MIDLEN < FRAME_SIZE:
                missing_str += "," + str(missing[i])
        return (False, missing_str, None, None, None)
    else:
        if cid not in chunk_map:
            log(f"[CHUNK] Ignoring this because we dont have an entry for this chunkid, likely because we have already processed this.")
            return (True, None, None, None, None)
        recompiled = recompile_msg(cid)
        return (True, None, cid, recompiled, creator)

# ---------------------------------------------------------------------------
# Command Center Integration
# ---------------------------------------------------------------------------

async def init_sim():
    # Input: None; Output: bool indicating cellular initialization success (updates cellular_system)
    """Initialize the cellular connection"""
    global cellular_system
    log("\n[CELL] === Initializing Cellular System ===")
    cellular_system = Cellular()
    if not cellular_system.initialize():
        log("[CELL] Cellular initialization failed!")
        return False
    log("[CELL] Cellular system ready")
    return True

async def sim_send_image(creator, encimb):
    # Input: creator: int node id, encimb: bytes encrypted image; Output: bool upload success
    """Send image via cellular with better error handling and retry logic"""
    global cellular_system
    if not cellular_system:
        log("[CELL] Cellular system not initialized")
        return False

    # Check connection health with retry
    max_connection_retries = 3
    for retry in range(max_connection_retries):
        if cellular_system.check_connection():
            break

        log(f"[CELL] Connection check failed, attempt {retry + 1}/{max_connection_retries}")
        if retry < max_connection_retries - 1:
            log("[CELL] Attempting reconnect...")
            if not cellular_system.reconnect():
                log(f"[CELL] Reconnection attempt {retry + 1} failed")
                await asyncio.sleep(5)  # Wait before next retry
                continue
        else:
            log("[CELL] All connection attempts failed")
            return False

    try:
        # Load and process image
        imgbytes = ubinascii.b2a_base64(encimb)
        log(f"[CELL] Sending image of size {len(imgbytes)} bytes")
        # Prepare payload with additional metadata
        payload = {
            "machine_id": creator,
            "message_type": "event",
            "image": imgbytes,
        }

        # Upload with retry logic
        max_upload_retries = 3
        for upload_retry in range(max_upload_retries):
            result = cellular_system.upload_data(payload, URL)

            if result and result.get('status_code') == 200:
                log(f"[CELL] Image uploaded successfully on attempt {upload_retry + 1}")
                log(f"[CELL] Upload time: {result.get('upload_time', 0):.2f}s")
                log(f"[CELL] Data size: {result.get('data_size', 0)/1024:.2f} KB")
                return True
            else:
                log(f"[CELL] Upload attempt {upload_retry + 1} failed")
                if result:
                    log(f"[CELL] HTTP Status: {result.get('status_code', 'Unknown')}")

                if upload_retry < max_upload_retries - 1:
                    await asyncio.sleep(2 ** upload_retry)  # Exponential backoff

        log(f"[CELL] Failed to upload image after {max_upload_retries} attempts")
        return False

    except Exception as e:
        log(f"[CELL] ERROR: in sim_send_image: {e}")
        return False

async def sim_upload_hb(heartbeat_data):
    # Input: heartbeat_data: dict payload; Output: bool indicating upload success
    """Send heartbeat data via cellular (for command center)"""
    global cellular_system

    if not cellular_system or not running_as_cc():
        return False

    try:
        result = cellular_system.upload_data(heartbeat_data, URL)
        if result and result.get('status_code') == 200:
            node_id = heartbeat_data["machine_id"]
            log(f"[HB] Heartbeat from node {node_id} sent to cloud successfully")
            return True
        else:
            log("[HB] ERROR: Failed to send heartbeat to cloud via cellular")
            if result:
                log(f"[HB] HTTP Status: {result.get('status_code', 'Unknown')}")
            return False

    except Exception as e:
        log(f"[HB] ERROR: sending cellular heartbeat: {e}")
        return False

async def upload_image(creator, encimb):
    # Input: creator: int node id, encimb: bytes encrypted image; Output: bool upload success
    """Unified image upload: tries cellular first, falls back to WiFi"""
    if cellular_system:
        result = await sim_send_image(creator, encimb)
        if result:
            return True
        log("[IMG] Cellular upload failed, trying WiFi fallback...")

    if wifi_nic and wifi_nic.isconnected():
        result = await wifi_send_image(creator, encimb)
        if result:
            return True

    log("[IMG] Image upload failed (cellular and WiFi both unavailable or failed)")
    return False

async def upload_heartbeat(heartbeat_data):
    # Input: heartbeat_data: dict payload; Output: bool indicating upload success
    """Unified heartbeat upload: tries cellular first, falls back to WiFi"""
    if not running_as_cc():
        return False

    if cellular_system:
        result = await sim_upload_hb(heartbeat_data)
        if result:
            return True
        log("[HB] ERROR: Cellular heartbeat upload failed, trying WiFi fallback...")
    else:
        log("[HB] ERROR: Cellular system not initialized, trying WiFi fallback...")

    if wifi_nic and wifi_nic.isconnected():
        result = await wifi_upload_hb(heartbeat_data)
        if result:
            return True
        log("[HB] ERROR: WiFi heartbeat upload failed, skipping heartbeat...")
    else:
        log("[HB] ERROR: WiFi not connected, heartbeat upload failed (cellular and WiFi both unavailable)")

    return False

# ---------------------------------------------------------------------------
# Message Handlers
# ---------------------------------------------------------------------------

hb_map = {}

async def hb_process(mid, msgbytes, sender):
    # Input: mid: bytes, msgbytes: bytes, sender: int; Output: None (routes or logs heartbeat data)
    destlist = possible_paths(sender)
    creator = int(mid[1])
    if running_as_cc():
        if creator not in hb_map:
            hb_map[creator] = 0
        hb_map[creator] += 1
        log(f"[HB] HB Counts = {hb_map}")
        log(f"[HB] Images saved at cc so far = {len(images_saved_at_cc)}")

        # Send raw heartbeat data (encrypted or not) to cloud
        # Convert bytes to base64 for JSON transmission, same as image data
        if isinstance(msgbytes, bytes):
            hb_data = ubinascii.b2a_base64(msgbytes)
        else:
            hb_data = msgbytes

        heartbeat_payload =  {
            "machine_id": creator,
            "message_type": "heartbeat",
            "heartbeat_data": hb_data,
        }

        log(f"[HB] Sending raw heartbeat data of length {len(msgbytes)} bytes")
        asyncio.create_task(upload_heartbeat(heartbeat_payload))

        for i in images_saved_at_cc:
            log(f"[HB] {i}")
        if ENCRYPTION_ENABLED:
            log(f"[HB] Only for debugging : HB msg = {enc.decrypt_rsa(msgbytes, encnode.get_prv_key(creator))}")
        else:
            log(f"[HB] Only for debugging : HB msg = {msgbytes.decode()}")
        # asyncio.create_task(sim_upload_hb(msgbytes))
        return
    elif len(destlist) > 0:
        sent_succ = False
        for peer_addr in destlist:
            log(f"[HB] Propogating H to {peer_addr}")
            sent_succ = await asyncio.create_task(send_msg("H", creator, msgbytes, peer_addr))
            if sent_succ:
                break
        if not sent_succ:
            log(f"[HB] ERROR: forwarding HB to possible_paths : {destlist}")
    else:
        log(f"[HB] Can't forward HB because I dont have Spath yet")

images_saved_at_cc = []

async def img_process(cid, msg, creator, sender):
    # Input: cid: str, msg: bytes (possibly encrypted image), creator: int, sender: int; Output: None (stores or forwards image)
    clear_chunkid(cid)
    if running_as_cc():
        log(f"[IMG] Received image of size {len(msg)}")
        # ----- TODO REMOVE THIS IS FOR DEBUGGING ONLY -------
        img_bytes = None
        img = None
        try:
            if ENCRYPTION_ENABLED:
                img_bytes = enc.decrypt_hybrid(msg, encnode.get_prv_key(creator))
            else:
                img_bytes = msg
            img = image.Image(320, 240, image.JPEG, buffer=img_bytes)
            log(f"[IMG] Image size: {len(img_bytes)} bytes")
            fname = f"{NET_IMAGE_DIR}/cc_{creator}_{cid}.jpg"
            log(f"[IMG] Saving to file {fname}")
            images_saved_at_cc.append(fname)
            # Limit list size
            if len(images_saved_at_cc) > MAX_IMAGES_SAVED_AT_CC:
                images_saved_at_cc.pop(0)
            img.save(fname)
            # ------------------------------------------------------
            asyncio.create_task(upload_image(creator, msg))
        finally:
            # Explicitly clean up image objects
            if img_bytes is not None:
                del img_bytes
            if img is not None:
                del img
            # Help GC reclaim memory
            gc.collect()
    else:
        destlist = possible_paths(sender)
        sent_succ = False
        for peer_addr in destlist:
            log(f"[IMG] Propogating Image to {peer_addr}")
            sent_succ = await asyncio.create_task(send_msg("P", creator, msg, peer_addr))
            if sent_succ:
                break
        if not sent_succ:
            log(f"[IMG] Failed propagating image to possible_paths : {possible_paths}")

# ---------------------------------------------------------------------------
# Sensor Capture and Image Transmission
# ---------------------------------------------------------------------------

images_to_send = []
detector = detect.Detector()

# ============================================================================
# PIR SENSOR DETECTION: INTERRUPT-DRIVEN 
# ============================================================================
# This implementation uses hardware interrupts - more efficient and responsive
# The task blocks waiting for PIR interrupt, only wakes when motion detected

# # PIR Sensor Interrupt-driven Setup
# pir_trigger_event = asyncio.Event()
# pir_last_trigger_time = 0
# PIR_DEBOUNCE_MS = 2000  # 2 seconds debounce to prevent multiple triggers from single motion

# def pir_interrupt_handler(pin):
#     """IRQ handler for PIR sensor - triggers on RISING edge (HIGH signal)"""
#     global pir_last_trigger_time, pir_trigger_event
#     current_time = utime.ticks_ms()
#     # Debounce: ignore triggers within PIR_DEBOUNCE_MS of last trigger
#     if utime.ticks_diff(current_time, pir_last_trigger_time) > PIR_DEBOUNCE_MS:
#         pir_last_trigger_time = current_time
#         # Set event to wake up person_detection_loop
#         pir_trigger_event.set()
#         # log(f"[PIR] Motion detected (interrupt)")

# async def person_detection_loop():
#     # Input: None; Output: None (runs on PIR interrupt, updates counters and queue)
#     global person_image_count, total_image_count, center_captured_image_count
#     global pir_trigger_event, image_in_progress
    
#     # Setup PIR sensor pin for interrupt
#     # Get PIR pin from detect module
#     from detect import PIR_PIN
#     # Configure IRQ on RISING edge (when PIR goes HIGH)
#     PIR_PIN.irq(trigger=Pin.IRQ_RISING, handler=pir_interrupt_handler)
#     log(f"[PIR] Interrupt-driven detection initialized on pin {PIR_PIN}")
    
#     while True:
#         # Wait for PIR interrupt event (blocks until PIR detects motion)
#         # Task is suspended here - uses minimal CPU until interrupt fires
#         await pir_trigger_event.wait()
#         # Clear the event for next trigger
#         pir_trigger_event.clear()
        
#         # Check if image processing is in progress
#         if image_in_progress:
#             log(f"[PIR] Skipping detection - image already in progress")
#             continue
        
#         # Motion detected - capture image
#         img = None
#         try:
#             log(f"[PIR] Motion detected - (interrupt) capturing image...")
#             img = sensor.snapshot()
#             person_image_count += 1
#             total_image_count += 1
#             # Track center's own captured images separately
#             if running_as_cc():
#                 center_captured_image_count += 1
#             raw_path = f"{MY_IMAGE_DIR}/raw_{get_rand()}.jpg"
#             log(f"[PIR] Saving image to {raw_path} : imbytesize = {len(img.bytearray())}...")
#             img.save(raw_path)
            
#             # Limit queue size to prevent memory overflow
#             if len(images_to_send) >= MAX_IMAGES_TO_SEND:
#                 # Remove oldest entry
#                 oldest = images_to_send.pop(0)
#                 log(f"[PIR] Queue full, removing oldest image: {oldest}")
#             images_to_send.append(raw_path)
#             # log(f"Saved image: {raw_path}")
#             # log(f"Person detected Image count: {person_image_count}")
#             # if running_as_cc():
#             #     log(f"Center captured images: {center_captured_image_count}")
#         except Exception as e:
#             log(f"[PIR] ERROR: Unexpected error in image taking and saving: {e}")
#         finally:
#             # Explicitly clean up image object
#             if img is not None:
#                 del img
#                 gc.collect()  # Help GC reclaim memory immediately


# ============================================================================
# PIR SENSOR DETECTION: POLLING-BASED 
# ============================================================================
# This is the previous implementation using software polling
# 
# ADVANTAGES of polling:
#   - Simpler code (no interrupt handlers)
#   - Good for slow-changing signals
# 
# DISADVANTAGES of polling:
#   - Wastes CPU cycles (wakes every 5 seconds even with no motion)
#   - Delayed response (up to 5 seconds delay)
#   - Higher power consumption (constant wake-ups)
#   - Can miss brief motions between polls

async def person_detection_loop():
    """Previous polling-based implementation"""
    # Input: None; Output: None (runs continuous detection, updates counters and queue)
    global person_image_count, total_image_count
    
    while True:
        # Poll every 5 seconds - wastes CPU even when no motion
        await asyncio.sleep(5)
        
        global image_in_progress
        if image_in_progress:
            log(f"Skipping DETECTION because image in progress")
            await asyncio.sleep(20)
            continue
        
        # Software polling: Read PIR pin value (inefficient)
        # This actively checks the pin every 5 seconds
        person_detected = detector.check_person()  # Calls PIR_PIN.value()
        
        # For testing without actual PIR: use if True instead
        # if True:
        if person_detected:
            img = None
            try:
                img = sensor.snapshot()
                person_image_count += 1
                total_image_count += 1
                raw_path = f"{MY_IMAGE_DIR}/raw_{get_rand()}.jpg"
                log(f"Saving image to {raw_path} : imbytesize = {len(img.bytearray())}...")
                img.save(raw_path)
                # Limit queue size to prevent memory overflow
                if len(images_to_send) >= MAX_IMAGES_TO_SEND:
                    # Remove oldest entry
                    oldest = images_to_send.pop(0)
                    log(f"Queue full, removing oldest image: {oldest}")
                images_to_send.append(raw_path)
                log(f"Saved image: {raw_path}")
            except Exception as e:
                log(f"ERROR: Unexpected error in image taking and saving: {e}")
            finally:
                # Explicitly clean up image object
                if img is not None:
                    del img
                    gc.collect()  # Help GC reclaim memory immediately
        
        await asyncio.sleep(PHOTO_TAKING_DELAY)
        log(f"Person detected Image count: {person_image_count}")

async def send_image_to_mesh(imgbytes):
    # Input: imgbytes: bytes raw image; Output: bool indicating if image was forwarded successfully
    log(f"[IMG] Sending {len(imgbytes)} bytes to the network")
    msgbytes = encrypt_if_needed("P", imgbytes)
    sent_succ = False
    destlist = possible_paths(None)
    for peer_addr in destlist:
        asyncio.create_task(acquire_image_lock())
        sent_succ = await send_msg("P", my_addr, msgbytes, peer_addr)
        release_image_lock()
        if sent_succ:
            return True
    return False

def take_image_and_send_now():
    # Input: None; Output: None (captures immediate snapshot and schedules send)
    img = sensor.snapshot()
    asyncio.create_task(send_image_to_mesh(img.to_jpeg().bytearray()))

async def image_sending_loop():
    # Input: None; Output: None (periodically sends queued images across mesh)
    global images_to_send
    while True:
        await asyncio.sleep(4)
        destlist = possible_paths(None)
        if not running_as_cc() and len(destlist) == 0:
            log("[NET] No shortest path yet so cant send")
            continue
        
        # Process all queued images one by one until queue is empty
        # This ensures all captured images get uploaded promptly
        # queue_size = len(images_to_send)
        # if queue_size > 0:
        #     log(f"[IMG] Starting upload loop, {queue_size} images in queue")
            
        while len(images_to_send) > 0:
            queue_size = len(images_to_send)
            # log(f"[IMG] Images to send = {queue_size}")
            imagefile = images_to_send.pop(0)
            log(f"[IMG] Processing: {imagefile}")
            img = None
            imgbytes = None
            encimgbytes = None
            try:
                img = image.Image(imagefile)
                imgbytes = img.bytearray()
                transmission_start = time_msec()
                if running_as_cc():
                    # Encrypt image before uploading (same format as images from other units)
                    encimgbytes = encrypt_if_needed("P", imgbytes)
                    log(f"[IMG] Uploading encrypted image (size: {len(encimgbytes)} bytes)")
                    sent_succ = await upload_image(my_addr, encimgbytes)
                else:
                    sent_succ = await send_image_to_mesh(imgbytes)
                if not sent_succ:
                    images_to_send.append(imagefile) # pushed to back of queue
                    log(f"[IMG] Upload failed, image re-queued: {imagefile}")
                    # If upload failed, wait longer before retrying
                    break

                transmission_end = time_msec()
                transmission_time = transmission_end - transmission_start
                log(f"[IMG] Image transmission completed in {transmission_time} ms ({transmission_time/1000:.4f} seconds)")
                # log(f"[IMG] Remaining in queue: {len(images_to_send)}")
                
                # Wait a short interval before processing next image in queue
                # This prevents overwhelming the network/upload service
                if len(images_to_send) > 0:
                    await asyncio.sleep(PHOTO_SENDING_INTERVAL)
                else:
                    log(f"[IMG] Queue empty, all images uploaded")
                    
            except Exception as e:
                log(f"[IMG] ERROR: Unexpected error processing image {imagefile}: {e}")
                import sys
                sys.print_exception(e)
                # Re-queue image on error
                images_to_send.append(imagefile)
                break
            finally:
                # Explicitly clean up image objects
                # Variables are initialized before try block, so they should always exist
                # Use try-except for safety in case of unusual scoping issues
                try:
                    if img is not None:
                        del img
                except NameError:
                    pass  # Variable not defined (shouldn't happen, but safe)
                except:
                    pass
                try:
                    if imgbytes is not None:
                        del imgbytes
                except NameError:
                    pass
                except:
                    pass
                try:
                    # Only delete encimgbytes if it was assigned and is different from imgbytes
                    # encimgbytes is only assigned when running_as_cc(), so check carefully
                    if encimgbytes is not None:
                        # Only delete if imgbytes is None or they're different objects
                        # This avoids deleting the same object twice
                        if imgbytes is None or encimgbytes is not imgbytes:
                            del encimgbytes
                except NameError:
                    pass  # Variable not defined (e.g., if exception occurred before assignment)
                except:
                    pass
                # Help GC reclaim memory
                gc.collect()
        
        # After processing all queued images (or queue is empty), wait longer before checking again
        # Only use long delay if queue is empty to avoid missing new images
        if len(images_to_send) == 0:
            # Queue is empty, sleep longer
            await asyncio.sleep(PHOTO_SENDING_DELAY)
        else:
            # Queue still has items (from failed uploads), check again soon
            await asyncio.sleep(PHOTO_SENDING_INTERVAL)

# If N messages seen in the last M minutes.
def scan_process(mid, msg):
    # Input: mid: bytes, msg: bytes containing node address; Output: None (updates seen neighbours)
    nodeaddr = int.from_bytes(msg)
    if nodeaddr not in seen_neighbours:
        log(f"[NET] Adding nodeaddr {nodeaddr} to seen_neighbours")
        seen_neighbours.append(nodeaddr)

async def spath_process(mid, msg):
    # Input: mid: bytes, msg: str shortest-path data; Output: None (updates shortest_path_to_cc and propagates)
    global shortest_path_to_cc
    if running_as_cc():
        # log(f"Ignoring shortest path since I am cc")
        return
    if len(msg) == 0:
        log(f"[NET] Empty spath")
        return
    spath = [int(x) for x in msg.split(",")]
    if my_addr in spath:
        log(f"[NET] Cyclic, ignoring {my_addr} already in {spath}")
        return
    if len(shortest_path_to_cc) == 0 or len(shortest_path_to_cc) > len(spath):
        log(f"[NET] Updating spath to {spath}")
        shortest_path_to_cc = spath
        for n in seen_neighbours:
            nsp = [my_addr] + spath
            nmsg = ",".join([str(x) for x in nsp])
            log(f"[NET] Propogating spath from {spath} to {nmsg}")
            asyncio.create_task(send_msg("S", int(mid[1]), nmsg.encode(), n))

def process_message(data):
    # Input: data: bytes raw LoRa payload; Output: bool indicating if message was processed
    log(f"[RECV {len(data)}] {data} at {time_msec()}")
    parsed = parse_header(data)
    if not parsed:
        log(f"[LORA] ERROR: Failure parsing incoming data : {data}")
        return False
    if random.randint(1,100) <= FLAKINESS:
        log(f"[LORA] Flakiness dropping {data}")
        return True
    mid, mst, creator, sender, receiver, msg = parsed
    if sender not in recv_msg_count:
        recv_msg_count[sender] = 0
    recv_msg_count[sender] += 1
    if receiver != -1 and my_addr != receiver:
        log(f"[LORA] Strange that {my_addr} is not as {receiver}")
        log(f"[LORA] Skipping message as it is not for me but for {receiver} : {mid}")
        return
    if receiver == -1 :
        log(f"[LORA] Processing broadcast message : {data} : {parsed}")
    msgs_recd.append((mid, msg, time_msec()))
    ackmessage = mid
    if mst == "N":
        scan_process(mid, msg)
    elif mst == "V":
        asyncio.create_task(send_msg("A", my_addr, ackmessage, sender))
    elif mst == "S":
        asyncio.create_task(spath_process(mid, msg.decode()))
    elif mst == "H":
        asyncio.create_task(hb_process(mid, msg, sender))
        asyncio.create_task(send_msg("A", my_addr, ackmessage, sender))
    elif mst == "C":
        asyncio.create_task(command_process(mid, msg))
    elif mst == "B":
        asyncio.create_task(acquire_image_lock())
        asyncio.create_task(send_msg("A", my_addr, ackmessage, sender))
        try:
            begin_chunk(msg.decode())
        except Exception as e:
            log(f"[CHUNK] ERROR: decoding unicode {e} : {msg}")
    elif mst == "I":
        add_chunk(msg)
    elif mst == "E":
        alldone, missing_str, cid, recompiled, creator = end_chunk(mid, msg.decode())
        if alldone:
            release_image_lock()
            global image_in_progress
            image_in_progress = False
            # Also when it fails
            ackmessage += b":-1"
            asyncio.create_task(send_msg("A", my_addr, ackmessage, sender))
            if recompiled:
                asyncio.create_task(img_process(cid, recompiled, creator, sender))
            else:
                log(f"[CHUNK] No recompiled, so not sending")
        else:
            ackmessage += b":" + missing_str.encode()
            asyncio.create_task(send_msg("A", my_addr, ackmessage, sender))
    else:
        log(f"[LORA] Unseen messages type {mst} in {msg}")
    return True

# ---------------------------------------------------------------------------
# LoRa Receive Loop
# ---------------------------------------------------------------------------

async def radio_read():
    # Input: None; Output: None (continuously receives LoRa packets and dispatches processing)
    while True:
        message = loranode.receive()
        if message:
            message = message.replace(b"{}[]", b"\n")
            process_message(message)
        await asyncio.sleep(0.1)

async def validate_and_remove_neighbours():
    # Input: None; Output: None (verifies neighbours via ping and prunes unreachable ones)
    global shortest_path_to_cc
    while True:
        log(f"[NET] Going to validate neighbours : {seen_neighbours}")
        to_be_removed = []
        for n in seen_neighbours:
            msgbytes = b"Nothing"
            success = await send_msg("V", my_addr, msgbytes, n)
            if success:
                log(f"[NET] Neighbour {n} is still within reach")
            else:
                log(f"[NET] Dropping neighbour : {n}")
                to_be_removed.append(n)
                if n in shortest_path_to_cc:
                    log(f"[NET] Clearing shortest path to CC (neighbour dropped)")
                    shortest_path_to_cc = []
        for x in to_be_removed:
            seen_neighbours.remove(x)
        await asyncio.sleep(VALIDATE_WAIT_SEC)

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
    destlist = possible_paths(None)
    log(f"[HB] Will send HB to {destlist}")

    gps_coords = read_gps_from_file()
    gps_staleness = get_gps_file_staleness()

    # my_addr : uptime (seconds) : photos taken : events seen : gpslat,gpslong : gps_staleness(seconds) : neighbours([221,222]) : shortest_path([221,9])
    hbmsgstr = f"{my_addr}:{time_sec()}:{total_image_count}:{person_image_count}:{gps_coords}:{gps_staleness}:{seen_neighbours}:{shortest_path_to_cc}"
    log(f"HBSTR = {hbmsgstr}")
    hbmsg = hbmsgstr.encode()
    msgbytes = encrypt_if_needed("H", hbmsg)
    sent_succ = False
    if running_as_cc():
        # Convert bytes to base64 for JSON transmission, same as hb_process()
        if isinstance(msgbytes, bytes):
            hb_data = ubinascii.b2a_base64(msgbytes)
        else:
            hb_data = msgbytes
        heartbeat_payload =  {
                "machine_id": my_addr,
                "message_type": "heartbeat",
                "heartbeat_data": hb_data,
            }
        log(f"[HB] Sending raw heartbeat data of length {len(msgbytes)} bytes")
        sent_succ = await upload_heartbeat(heartbeat_payload)
        return sent_succ
    else:
        for peer_addr in destlist:
            log(f"[HB] Sending HB to {peer_addr}")
            sent_succ = await send_msg("H", my_addr, msgbytes, peer_addr)
            if sent_succ:
                consecutive_hb_failures = 0
                log(f"[HB] Heartbeat sent successfully to {peer_addr}")
                return True
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
                log(f"[HB] PAUSED")
            print_pause = False
            print_resume = True
            await asyncio.sleep(200)
            continue
        else:
            if print_resume:
                log(f"[HB] RESUMED")
            print_resume = False
            print_pause = True

        # log(f"In send HB loop, Shortest path = {shortest_path_to_cc}")
        sent_succ = await asyncio.create_task(send_heartbeat())
        if not sent_succ:
            consecutive_hb_failures += 1
            log(f"[ERROR]: consecutive heartbeat failures = {consecutive_hb_failures}")
            if consecutive_hb_failures > 1:
                log(f"[ERROR]: Too many consecutive heartbeat failures, reinitializing LoRa...")
                try:
                    await init_lora()
                    consecutive_hb_failures = 0
                except Exception as e:
                    log(f"[LORA] ERROR: reinitializing LoRa: {e}")
        else:
            log(f"[HB] HB SUCCESS, shortest path = {shortest_path_to_cc}")
        i += 1
        if i < DISCOVERY_COUNT:
            await asyncio.sleep(HB_WAIT + random.randint(3,10))
        else:
            await asyncio.sleep(HB_WAIT_2 + random.randint(1, 120))

async def send_scan():
    # Input: None; Output: None (broadcasts discovery messages periodically)
    global seen_neighbours
    i = 1
    while True:
        global image_in_progress
        if image_in_progress:
            log(f"[NET] Skipping scan send because image in progress")
            await asyncio.sleep(SCAN_WAIT)
            continue
        scanmsg = encode_node_id(my_addr)
        # 65535 is for Broadcast
        await send_msg_internal("N", my_addr, scanmsg, 65535)
        if i < DISCOVERY_COUNT:
            await asyncio.sleep(SCAN_WAIT)
        else:
            await asyncio.sleep(SCAN_WAIT_2 + random.randint(1,120))
        log(f"[STATUS] {my_addr} : Seen neighbours = {seen_neighbours}, Shortest path = {shortest_path_to_cc}, Sent messages = {sent_count}, Received messages = {recv_msg_count}")
        i = i + 1

async def send_spath():
    # Input: None; Output: None (periodically shares shortest-path information with neighbours)
    i = 1
    while True:
        global image_in_progress
        if image_in_progress:
            log(f"[NET] Skipping spath send because image in progress")
            await asyncio.sleep(200)
            continue
        sp = f"{my_addr}"
        for n in seen_neighbours:
            log(f"[NET] Sending shortest path to {n}")
            await send_msg("S", my_addr, sp.encode(), n)
        i += 1
        if i < DISCOVERY_COUNT:
            await asyncio.sleep(SPATH_WAIT)
        else:
            await asyncio.sleep(SPATH_WAIT_2 + random.randint(1,120))

# ---------------------------------------------------------------------------
# Command Execution and Routing
# ---------------------------------------------------------------------------

def get_next_on_path(cpath):
    # Input: cpath: list of str/int path nodes; Output: int or None next hop for this device
    for i in range(len(cpath) - 1):
        n = cpath[i]
        if n == my_addr:
            return cpath[i+1]
    return None

def execute_command(command):
    # Input: command: str command identifier; Output: None (performs device-specific action)
    log(f"[CMD] Gonna execute_command {command} on {my_addr}")
    if command == "SENDHB":
        asyncio.create_task(send_heartbeat())
    elif command == "SENDIMG":
        take_image_and_send_now()
    elif command == "RESET":
        log(f"Resetting maching")
        log_to_file()
        machine.reset()

def fake_listen_http():
    # Input: None; Output: tuple(command: str, dest: int, cpath: list[int]) for simulated commands
    command = "SENDHB"
    dest = 222
    cpath = [219,222]
    return (command, dest, cpath)

async def command_process(mid, msg):
    # Input: mid: bytes, msg: bytes command payload; Output: None (executes or forwards command)
    try:
        msgstr = msg.decode()
    except Exception as e:
        log(f"[CMD] Could not decode {msg} : {e}")
    parts = msgstr.split(";")
    if len(parts) != 3:
        log(f"[CMD] ERROR: parsing msgstr")
    dest = int(parts[0])
    cpath = parts[1].split(",")
    command = parts[2]
    if dest == my_addr:
        execute_command(command)
        return
    next_dest = get_next_on_path(cpath)
    if next_dest is not None:
        log(f"[CMD] Propogating command to {next_dest}")
        await send_msg("C", my_addr, msgstr.encode(), next_dest)
    else:
        log(f"[CMD] Next dest seems None for {msg}")

# Randomly sends, with 10% probability every 20 seconds.
async def listen_commands_from_cloud():
    # Input: None; Output: None (simulates random command reception and routing)
    while True:
        await asyncio.sleep(20)
        if random.randint(1, 100) >= 10:
            continue
        command, dest, cpath = fake_listen_http()
        global image_in_progress
        if image_in_progress:
            log(f"[STATUS] Skipping print summary because image in progress")
            await asyncio.sleep(200)
            continue
        log(f"[CMD] Randomly sending a command {command} to {dest}, via {cpath}")
        if dest == my_addr:
            execute_command(command)
            continue
        next_dest = get_next_on_path(cpath)
        if next_dest is not None:
            log(f"[CMD] Propogating command to {next_dest}")
            cpathstr = ",".join(str(x) for x in cpath)
            command = f"{dest};{cpathstr};{command}"
            await send_msg("C", my_addr, command.encode(), next_dest)
        else:
            log(f"[CMD] Next dest seems to be None")

# ---------------------------------------------------------------------------
# Monitoring and Logging
# ---------------------------------------------------------------------------

async def print_summary_and_flush_logs():
    # Input: None; Output: None (periodically logs status metrics and flushes logs)
    while True:
        await asyncio.sleep(30)
        global image_in_progress
        if image_in_progress:
            log(f"[STATUS] Skipping print summary because image in progress")
            await asyncio.sleep(200)
            continue
        free_mem = get_free_memory()
        mem_str = f", Free: {free_mem/1024:.1f}KB" if free_mem > 0 else ""
        log(f"[STATUS] Sent : {len(msgs_sent)} Recd : {len(msgs_recd)} Unacked : {len(msgs_unacked)} LoRa inits: {lora_init_count}{mem_str}")
        if running_as_cc():
            log(f"[STATUS] Chunks: {len(chunk_map)}, Images at CC (received): {len(images_saved_at_cc)}, Center captured: {center_captured_image_count}, Queued: {len(images_to_send)}")
        else:
            log(f"[STATUS] Chunks: {len(chunk_map)}, Queued images: {len(images_to_send)}")
        log_to_file()
        #log(msgs_sent)
        #log(msgs_recd)
        #log(msgs_unacked)

# ---------------------------------------------------------------------------
# GPS Acquisition Loop
# ---------------------------------------------------------------------------

async def keep_updating_gps():
    # Input: None; Output: None (continuously reads GPS hardware and updates global state)
    global gps_str, gps_last_time
    log("[GPS] Initializing GPS...")

    # Wait for LoRa to settle
    await asyncio.sleep(3)

    try:
        uart = gps_driver.SC16IS750(spi_bus=1, cs_pin="P3")
        uart.init_gps()
        gps = gps_driver.GPS(uart)
        log("[GPS] GPS hardware initialized successfully - starting continuous read loop")
    except Exception as e:
        log(f"[GPS] GPS initialization failed: {e}")
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
                    log(f"[GPS] {gps_str}")
                    gps_last_time = time_msec()
                    last_successful_read = read_count
                else:
                    if read_count % 10 == 1:
                        log("[GPS] GPS has fix but no coordinates")
            else:
                if read_count % 20 == 1:
                    log("[GPS] GPS has no fix")
                    # Show raw data for debugging
                    raw_debug = uart.read_data()
                    if raw_debug:
                        sample = raw_debug[:60].replace('\r', '\\r').replace('\n', '\\n')
                        log(f"[GPS] GPS raw: {sample}")

            # Clear buffer periodically to prevent overflow
            if read_count % 30 == 0:
                while uart.read_data():  # Clear all buffered data
                    pass
                gps.buffer = ""  # Clear internal parser buffer
                log("[GPS] GPS buffer cleared")

            # Reinitialize if too many failures
            if last_successful_read > 0 and (read_count - last_successful_read) > 100:
                log("[GPS] GPS not working, reinitializing...")
                try:
                    uart.init_gps()
                    gps = gps_driver.GPS(uart)
                    await asyncio.sleep(2)
                    last_successful_read = read_count
                except Exception as e:
                    log(f"[GPS] GPS reinit failed: {e}")
                    await asyncio.sleep(10)

        except Exception as e:
            log(f"[GPS] GPS read error: {e}")
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
        log("[WIFI] WiFi is disabled (WIFI_ENABLED = False)")
        return False

    try:
        log(f"[WIFI] Initializing WiFi connection to SSID: {WIFI_SSID}")
        # Create WLAN interface in station mode
        wifi_nic = network.WLAN(network.WLAN.IF_STA)

        # Activate the interface
        wifi_nic.active(True)

        # Connect to WiFi access point
        log(f"[WIFI] Connecting to WiFi network: {WIFI_SSID}")
        wifi_nic.connect(WIFI_SSID, WIFI_PASSWORD)

        # Wait for connection with timeout
        max_wait = 20  # Maximum wait time in seconds
        wait_count = 0
        while wait_count < max_wait:
            if wifi_nic.isconnected():
                # Connection successful
                ifconfig = wifi_nic.ifconfig()
                log(f"[WIFI] WiFi connected successfully!")
                log(f"[WIFI] IP address: {ifconfig[0]}")
                log(f"[WIFI] Subnet mask: {ifconfig[1]}")
                log(f"[WIFI] Gateway: {ifconfig[2]}")
                log(f"[WIFI] DNS server: {ifconfig[3]}")
                return True

            # Check for connection errors (if status() is available)
            try:
                status = wifi_nic.status()
                # Try to detect common error statuses if constants exist
                if hasattr(network.WLAN, 'STAT_WRONG_PASSWORD') and status == network.WLAN.STAT_WRONG_PASSWORD:
                    log(f"[WIFI] Connection failed: Wrong password")
                    wifi_nic.active(False)
                    return False
                elif hasattr(network.WLAN, 'STAT_NO_AP_FOUND') and status == network.WLAN.STAT_NO_AP_FOUND:
                    log(f"[WIFI] Connection failed: Access point not found")
                    wifi_nic.active(False)
                    return False
                elif hasattr(network.WLAN, 'STAT_CONNECT_FAIL') and status == network.WLAN.STAT_CONNECT_FAIL:
                    log(f"[WIFI] Connection failed: Connection failed")
                    wifi_nic.active(False)
                    return False
                log(f"[WIFI] Connecting... (status: {status}, wait: {wait_count}s)")
            except:
                # Status checking not available, just log wait time
                log(f"[WIFI] Connecting... (wait: {wait_count}s)")

            await asyncio.sleep(1)
            wait_count += 1

        # Timeout
        log(f"[WIFI] Connection timeout after {max_wait} seconds")
        wifi_nic.active(False)
        return False

    except Exception as e:
        log(f"[WIFI] Initialization error: {e}")
        if wifi_nic:
            try:
                wifi_nic.active(False)
            except:
                pass
        return False

def get_wifi_status():
    # Input: None; Output: dict with WiFi status information
    global wifi_nic
    if not wifi_nic or not WIFI_ENABLED:
        return {"enabled": False, "connected": False}

    try:
        is_connected = wifi_nic.isconnected()
        if is_connected:
            ifconfig = wifi_nic.ifconfig()
            status = wifi_nic.status()
            rssi = None
            try:
                rssi = wifi_nic.status('rssi')
            except:
                pass
            return {
                "enabled": True,
                "connected": True,
                "ip": ifconfig[0],
                "subnet": ifconfig[1],
                "gateway": ifconfig[2],
                "dns": ifconfig[3],
                "status": status,
                "rssi": rssi
            }
        else:
            return {
                "enabled": True,
                "connected": False,
                "status": wifi_nic.status()
            }
    except Exception as e:
        log(f"[WIFI] ERROR: getting WiFi status: {e}")
        return {"enabled": True, "connected": False, "error": str(e)}

async def wifi_send_image(creator, encimb):
    # Input: creator: int node id, encimb: bytes encrypted image; Output: bool upload success
    """Send image via WiFi"""
    global wifi_nic
    if not wifi_nic or not wifi_nic.isconnected():
        log("[WIFI] WiFi not connected")
        return False

    try:
        # Try to import requests
        try:
            import requests
            use_requests = True
        except ImportError:
            use_requests = False

        # Load and process image - same format as SIM upload
        imgbytes = ubinascii.b2a_base64(encimb)
        # log(f"Sending image of size {len(imgbytes)} bytes")
        # Prepare payload with additional metadata - same format as SIM upload
        payload = {
            "machine_id": creator,
            "message_type": "event",
            "image": imgbytes,
        }

        if use_requests:
            # Convert bytes to string for requests library (standard Python json needs strings)
            # Match SIM upload format: MicroPython json.dumps converts bytes to string automatically
            # We need to manually convert to match that behavior
            payload_str = payload.copy()
            if "image" in payload_str and isinstance(payload_str["image"], bytes):
                # Decode base64 bytes to base64 string, remove all newlines to match MicroPython behavior
                # ubinascii.b2a_base64 may include newlines every 76 chars, remove them
                payload_str["image"] = payload_str["image"].decode('utf-8').replace('\n', '').replace('\r', '')
            headers = {"Content-Type": "application/json"}
            json_payload = json.dumps(payload_str)
            r = requests.post(URL, data=json_payload, headers=headers)
            if r.status_code == 200:
                log(f"[WIFI] Image uploaded via WiFi successfully")
                return True
            else:
                log(f"[WIFI] Upload failed: status {r.status_code}")
                return False
        else:
            # Fallback to socket-based HTTP (not implemented for brevity)
            log("[WIFI] requests library not available, WiFi upload skipped")
            return False

    except Exception as e:
        log(f"[WIFI] ERROR: in wifi_send_image: {e}")
        return False

async def wifi_upload_hb(heartbeat_data):
    # Input: heartbeat_data: dict payload; Output: bool indicating upload success
    """Send heartbeat data via WiFi"""
    global wifi_nic
    if not wifi_nic or not wifi_nic.isconnected():
        return False

    try:
        try:
            import requests
            use_requests = True
        except ImportError:
            use_requests = False

        if use_requests:
            # Convert bytes to strings for requests library (standard Python json needs strings)
            # Match SIM upload format: MicroPython json.dumps converts bytes to string automatically
            # We need to manually convert to match that behavior
            payload = heartbeat_data.copy()
            if "heartbeat_data" in payload and isinstance(payload["heartbeat_data"], bytes):
                # Decode base64 bytes to base64 string, remove all newlines to match MicroPython behavior
                # ubinascii.b2a_base64 may include newlines every 76 chars, remove them
                payload["heartbeat_data"] = payload["heartbeat_data"].decode('utf-8').replace('\n', '').replace('\r', '')
            headers = {"Content-Type": "application/json"}
            json_payload = json.dumps(payload)
            r = requests.post(URL, data=json_payload, headers=headers)
            if r.status_code == 200:
                node_id = payload.get("machine_id", "unknown")
                log(f"[HB] Heartbeat from node {node_id} sent via WiFi successfully")
                return True
            else:
                log(f"[HB] WiFi upload failed: status {r.status_code}")
                if hasattr(r, 'text'):
                    log(f"[HB] Response: {r.text[:200]}")
                return False
        else:
            log("[HB] requests library not available, WiFi upload skipped")
            return False

    except Exception as e:
        log(f"[HB] ERROR: in wifi_upload_hb: {e}")
        return False

# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------

async def main():
    # Input: None; Output: None (entry point scheduling initialization and background tasks)
    log(f"[INIT] Started device {my_addr}")

    await init_lora()
    asyncio.create_task(radio_read())
    asyncio.create_task(print_summary_and_flush_logs())
    asyncio.create_task(validate_and_remove_neighbours())
    # Start memory management tasks
    asyncio.create_task(periodic_memory_cleanup())
    asyncio.create_task(periodic_gc())
    log(f"[MEM] Memory management tasks started (free: {get_free_memory()/1024:.1f}KB)")
    if running_as_cc():
        log(f"[INIT] Starting command center")
        # Initialize WiFi if enabled
        if WIFI_ENABLED:
            await init_wifi()

        # await init_sim()
        asyncio.create_task(send_scan())
        await asyncio.sleep(2)
        asyncio.create_task(send_spath())
        #asyncio.create_task(listen_commands_from_cloud())
        asyncio.create_task(keep_sending_heartbeat())
        asyncio.create_task(person_detection_loop())
        asyncio.create_task(image_sending_loop())
    else:
        asyncio.create_task(send_scan())
        await asyncio.sleep(1)
        asyncio.create_task(keep_sending_heartbeat())
        await asyncio.sleep(2)
        #asyncio.create_task(keep_updating_gps())
        asyncio.create_task(person_detection_loop())
        asyncio.create_task(image_sending_loop())
    for i in range(24*7):
        await asyncio.sleep(3600)
        log(f"Finished HOUR {i}")

try:
    asyncio.run(main())
except KeyboardInterrupt:
    log("Stopped.")
