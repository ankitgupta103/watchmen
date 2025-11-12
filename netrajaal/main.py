from machine import RTC, UART
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

import enc
import sx1262
import gps_driver
from cellular_driver import Cellular
import detect

MIN_SLEEP = 0.1
ACK_SLEEP = 0.2
CHUNK_SLEEP = 0.3

DISCOVERY_COUNT = 100
HB_WAIT = 300
HB_WAIT_2 = 1200
SPATH_WAIT = 30
SPATH_WAIT_2 = 1200
SCAN_WAIT = 30
SCAN_WAIT_2 = 1200
VALIDATE_WAIT_SEC = 1200
PHOTO_TAKING_DELAY = 1
PHOTO_SENDING_DELAY = 600
GPS_WAIT_SEC = 5

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
gps_str = ""
gps_last_time = -1

consecutive_hb_failures = 0
lora_reinit_count = 0

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
    shortest_path_to_cc = [219]
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
    # Input: None; Output: str formatted as mm:ss
    _,_,_,_,h,m,s,_ = rtc.datetime()
    t=f"{m}:{s}"
    return t

log_entries_buffer = []

def log(msg):
    # Input: msg: str; Output: None (side effects: buffer append and console log)
    t = get_human_ts()
    # log_entry = f"{my_addr}@{t} : {msg}"
    log_entry = f"{t} : {msg}"
    log_entries_buffer.append(log_entry)
    print(log_entry)



def running_as_cc():
    # Input: None; Output: bool indicating if this device is the command center
    return my_addr in COMMAN_CENTER_ADDRS

def get_fs_root_for_storage():
    # Input: None; Output: str path for filesystem root
    has_sdcard = True
    try:
        os.listdir('/sdcard')
        log("SD card available")
    except OSError:
        log("ERROR: SD card not found!")
        has_sdcard = False

    if has_sdcard:
        return "/sdcard"
    else:
        return "/flash"

FS_ROOT = get_fs_root_for_storage()
log(f"Using FS_ROOT : {FS_ROOT}")
MY_IMAGE_DIR = f"{FS_ROOT}/myimages"
NET_IMAGE_DIR = f"{FS_ROOT}/netimages"

def create_dir_if_not_exists(dir_path):
    try:
        parts = [p for p in dir_path.split('/') if p]
        if len(parts) < 2:
            log(f"WARNING: Invalid directory path (no parent): {dir_path}")
            return
        parent = '/' + '/'.join(parts[:-1])
        dir_name = parts[-1]
        if dir_name not in os.listdir(parent):
            os.mkdir(dir_path)
            log(f"Created {dir_path}")
        else:
            log(f"{dir_path} already exists")
    except OSError as e:
        log(f"ERROR: Failed to create/access {dir_path}: {e}")

create_dir_if_not_exists(NET_IMAGE_DIR)
create_dir_if_not_exists(MY_IMAGE_DIR)

LOG_FILE_PATH = f"{FS_ROOT}/mainlog.txt"

log(f"MyAddr = {my_addr}")
encnode = enc.EncNode(my_addr)
log(f"Logs will be written at {LOG_FILE_PATH}")


log("Running on device : " + uid.decode())

def log_to_file():
    # Input: None; Output: None (writes buffered log entries to log file)
    with open(LOG_FILE_PATH, "a") as log_file:
        global log_entries_buffer
        tmp = log_entries_buffer
        log_entries_buffer = []
        log(f"Writing {len(tmp)} lines to logfile")
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
        log(f"Weird that data is none")
        return None
    if len(data) < 9:
        return None
    try:
        mid = data[:MIDLEN]
    except Exception as e:
        log(f"ERROR: PARSING {data[:MIDLEN]}  :  Error : {e}")
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
    log(f"Acquiring Image Lock")
    image_in_progress = True
    await asyncio.sleep(120)
    if image_in_progress:
        log(f"Releasing image lock after 120 seconds, current lock state = {image_in_progress}")
    image_in_progress = False

def release_image_lock():
    # Input: None; Output: None (clears image_in_progress flag)
    log(f"Releasing Image Lock")
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
    global loranode, lora_reinit_count
    lora_reinit_count += 1
    log(f"Initializing LoRa SX126X module... my lora addr = {my_addr}")
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

    log(f"LoRa module (Total Initializations: {lora_reinit_count})")
    log(f"Node address: {loranode.addr}")
    log(f"Frequency: {loranode.start_freq + loranode.offset_freq}.125MHz")
    log(f"===> LoRa module initialized successfully! <===\n")

msgs_sent = []
msgs_unacked = []
msgs_recd = []

# MSG TYPE = H(eartbeat), A(ck), B(egin), E(nd), C(hunk), S(hortest path)

def radio_send(dest, data):
    # Input: dest: int, data: bytes; Output: None (sends bytes via LoRa, logs send)
    global sent_count
    sent_count = sent_count + 1
    lendata = len(data)
    if len(data) > 254:
        log(f"ERROR: msg too large : {len(data)}")
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
                log(f"Msg {mid} : was acked in {at - timesent} msecs")
                msgs_sent.append(pop_and_get(mid))
                return (True, missing_chunks)
            else:
                log(f"Still waiting for ack for {mid} # {i}")
                await asyncio.sleep(ACK_SLEEP * (i+1)) # progressively more sleep
        log(f"Failed to get ack for message {mid} for retry # {retry_i}")
    log(f"Failed to send message {mid}")
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
        log(f"Sending photo of length {len(msgbytes)}")
    if len(msgbytes) < FRAME_SIZE:
        succ, _ = await send_single_msg(msgtype, creator, msgbytes, dest)
        return succ
    imid = get_rand()
    chunks = make_chunks(msgbytes)
    log(f"Chunking {len(msgbytes)} long message with id {imid} into {len(chunks)} chunks")
    succ, _ = await send_single_msg("B", creator, f"{msgtype}:{imid}:{len(chunks)}", dest)
    if not succ:
        log(f"Failed sending chunk begin")
        return False
    for i in range(len(chunks)):
        asyncio.create_task(acquire_image_lock())
        if i % 10 == 0:
            log(f"Sending chunk {i}")
        await asyncio.sleep(CHUNK_SLEEP)
        chunkbytes = imid.encode() + i.to_bytes(2) + chunks[i]
        _ = await send_single_msg("I", creator, chunkbytes, dest)
    for retry_i in range(50):
        await asyncio.sleep(CHUNK_SLEEP)
        succ, missing_chunks = await send_single_msg("E", creator, imid, dest)
        if not succ:
            log(f"Failed sending chunk end")
            break
        if len(missing_chunks) == 1 and missing_chunks[0] == -1:
            log(f"Successfully sent all chunks")
            return True
        log(f"Receiver still missing {len(missing_chunks)} chunks after retry {retry_i}: {missing_chunks}")
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
                    log(f"Checking for missing IDs in {msgbytes[MIDLEN+1:]}")
                    missingstr = msgbytes[MIDLEN+1:].decode()
                    missingids = [int(i) for i in missingstr.split(',')]
                return (t, missingids)
    return (-1, None)

async def log_status():
    # Input: None; Output: None (logs transmission statistics)
    await asyncio.sleep(1)
    log("$$$$ %%%%% ###### Printing status ###### $$$$$$ %%%%%%%%")
    log(f"So far sent {len(msgs_sent)} messages and received {len(msgs_recd)} messages")
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
        log(f"So far {len(msgs_not_acked)} messsages havent been acked")
        log(msgs_not_acked)

chunk_map = {} # chunk ID to (expected_chunks, [(iter, chunk_data)])

# ---------------------------------------------------------------------------
# Chunk Assembly Helpers
# ---------------------------------------------------------------------------

def begin_chunk(msg):
    # Input: msg: str formatted as "<type>:<chunk_id>:<num_chunks>"; Output: None (initializes chunk tracking)
    parts = msg.split(":")
    if len(parts) != 3:
        log(f"ERROR: : begin message unparsable {msg}")
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
        log(f"ERROR: : Not enough bytes {len(msgbytes)} : {msgbytes}")
        return
    asyncio.create_task(acquire_image_lock())
    cid = msgbytes[0:3].decode()
    citer = int.from_bytes(msgbytes[3:5])
    #log(f"Got chunk id {citer}")
    cdata = msgbytes[5:]
    if cid not in chunk_map:
        log(f"ERROR: : no entry yet for {cid}")
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
        chunk_map.pop(cid)
    else:
        log(f"Couldnt find {cid} in {chunk_map}")

# Note only sends as many as wouldnt go beyond frame size
# Assumption is that subsequent end chunks would get the rest
def end_chunk(mid, msg):
    # Input: mid: bytes message id, msg: str chunk identifier; Output: tuple(status:bool, missing:str|None, cid:str|None, data:bytes|None, creator:int|None)
    cid = msg
    creator = int(mid[1])
    missing = get_missing_chunks(cid)
    log(f"I am missing {len(missing)} chunks : {missing}")
    if len(missing) > 0:
        missing_str = str(missing[0])
        for i in range(1, len(missing)):
            if len(missing_str) + len(str(missing[i])) + 1 + MIDLEN + MIDLEN < FRAME_SIZE:
                missing_str += "," + str(missing[i])
        return (False, missing_str, None, None, None)
    else:
        if cid not in chunk_map:
            log(f"Ignoring this because we dont have an entry for this chunkid, likely because we have already processed this.")
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
    log("\n=== Initializing Cellular System ===")
    cellular_system = Cellular()
    if not cellular_system.initialize():
        log("Cellular initialization failed!")
        return False
    log("Cellular system ready")
    return True

async def sim_send_image(creator, encimb):
    # Input: creator: int node id, encimb: bytes encrypted image; Output: bool upload success
    """Send image via cellular with better error handling and retry logic"""
    global cellular_system
    if not cellular_system:
        log("Cellular system not initialized")
        return False

    # Check connection health with retry
    max_connection_retries = 3
    for retry in range(max_connection_retries):
        if cellular_system.check_connection():
            break

        log(f"Connection check failed, attempt {retry + 1}/{max_connection_retries}")
        if retry < max_connection_retries - 1:
            log("Attempting reconnect...")
            if not cellular_system.reconnect():
                log(f"  Reconnection attempt {retry + 1} failed")
                await asyncio.sleep(5)  # Wait before next retry
                continue
        else:
            log("All connection attempts failed")
            return False

    try:
        # Load and process image
        imgbytes = ubinascii.b2a_base64(encimb)
        log(f"Sending image of size {len(imgbytes)} bytes")
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
                log(f"Image uploaded successfully on attempt {upload_retry + 1}")
                log(f"Upload time: {result.get('upload_time', 0):.2f}s")
                log(f"Data size: {result.get('data_size', 0)/1024:.2f} KB")
                return True
            else:
                log(f"Upload attempt {upload_retry + 1} failed")
                if result:
                    log(f"HTTP Status: {result.get('status_code', 'Unknown')}")

                if upload_retry < max_upload_retries - 1:
                    await asyncio.sleep(2 ** upload_retry)  # Exponential backoff

        log(f"Failed to upload image after {max_upload_retries} attempts")
        return False

    except Exception as e:
        log(f"ERROR: in sim_send_image: {e}")
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
            log(f"Heartbeat from node {node_id} sent to cloud successfully")
            return True
        else:
            log("Failed to send heartbeat to cloud via cellular")
            if result:
                log(f"HTTP Status: {result.get('status_code', 'Unknown')}")
            return False

    except Exception as e:
        log(f"ERROR: sending cellular heartbeat: {e}")
        return False

async def upload_image(creator, encimb):
    # Input: creator: int node id, encimb: bytes encrypted image; Output: bool upload success
    """Unified image upload: tries cellular first, falls back to WiFi"""
    if cellular_system:
        result = await sim_send_image(creator, encimb)
        if result:
            return True
        log("Cellular upload failed, trying WiFi fallback...")

    if wifi_nic and wifi_nic.isconnected():
        result = await wifi_send_image(creator, encimb)
        if result:
            return True

    log("Image upload failed (cellular and WiFi both unavailable or failed)")
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
        log("Cellular heartbeat upload failed, trying WiFi fallback...")

    if wifi_nic and wifi_nic.isconnected():
        result = await wifi_upload_hb(heartbeat_data)
        if result:
            return True

    log("Heartbeat upload failed (cellular and WiFi both unavailable or failed)")
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
        log(f"HB Counts = {hb_map}")
        log(f"Images saved at cc so far = {len(images_saved_at_cc)}")

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

        log(f"Sending raw heartbeat data of length {len(msgbytes)} bytes")
        asyncio.create_task(upload_heartbeat(heartbeat_payload))

        for i in images_saved_at_cc:
            log(i)
        if ENCRYPTION_ENABLED:
            log(f"Only for debugging : HB msg = {enc.decrypt_rsa(msgbytes, encnode.get_prv_key(creator))}")
        else:
            log(f"Only for debugging : HB msg = {msgbytes.decode()}")
        # asyncio.create_task(sim_upload_hb(msgbytes))
        return
    elif len(destlist) > 0:
        sent_succ = False
        for peer_addr in destlist:
            log(f"Propogating H to {peer_addr}")
            sent_succ = await asyncio.create_task(send_msg("H", creator, msgbytes, peer_addr))
            if sent_succ:
                break
        if not sent_succ:
            log(f"ERROR: forwarding HB to possible_paths : {destlist}")
    else:
        log(f"Can't forward HB because I dont have Spath yet")

images_saved_at_cc = []

async def img_process(cid, msg, creator, sender):
    # Input: cid: str, msg: bytes (possibly encrypted image), creator: int, sender: int; Output: None (stores or forwards image)
    clear_chunkid(cid)
    if running_as_cc():
        log(f"Received image of size {len(msg)}")
        # ----- TODO REMOVE THIS IS FOR DEBUGGING ONLY -------
        if ENCRYPTION_ENABLED:
            img_bytes = enc.decrypt_hybrid(msg, encnode.get_prv_key(creator))
        else:
            img_bytes = msg
        img = image.Image(320, 240, image.JPEG, buffer=img_bytes)
        log(len(img_bytes))
        fname = f"{NET_IMAGE_DIR}/cc_{creator}_{cid}.jpg"
        log(f"Saving to file {fname}")
        images_saved_at_cc.append(fname)
        img.save(fname)
        # ------------------------------------------------------
        asyncio.create_task(upload_image(creator, msg))
    else:
        destlist = possible_paths(sender)
        sent_succ = False
        for peer_addr in destlist:
            log(f"Propogating Image to {peer_addr}")
            sent_succ = await asyncio.create_task(send_msg("P", creator, msg, peer_addr))
            if sent_succ:
                break
        if not sent_succ:
            log(f"Failed propagating image to possible_paths : {possible_paths}")

# ---------------------------------------------------------------------------
# Sensor Capture and Image Transmission
# ---------------------------------------------------------------------------

images_to_send = []
detector = detect.Detector()

async def person_detection_loop():
    # Input: None; Output: None (runs continuous detection, updates counters and queue)
    global person_image_count, total_image_count
    while True:
        await asyncio.sleep(5)
        global image_in_progress
        if image_in_progress:
            log(f"Skipping DETECTION because image in progress")
            await asyncio.sleep(20)
            continue
        total_image_count += 1
        person_detected = detector.check_person()
        if person_detected:
            try:
                img = sensor.snapshot()
                person_image_count += 1
                raw_path = f"{MY_IMAGE_DIR}/raw_{get_rand()}.jpg"
                log(f"Saving image to {raw_path} : imbytesize = {len(img.bytearray())}...")
                img.save(raw_path)
                images_to_send.append(raw_path)
                log(f"Saved image: {raw_path}")
            except Exception as e:
                log(f"ERROR: Unexpected error in image taking and saving: {e}")
        await asyncio.sleep(PHOTO_TAKING_DELAY)
        log(f"Total_image_count = {total_image_count}, Person Image count: {person_image_count}")

async def send_image_to_mesh(imgbytes):
    # Input: imgbytes: bytes raw image; Output: bool indicating if image was forwarded successfully
    log(f"Sending {len(imgbytes)} bytes to the network")
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
            log("No shortest path yet so cant send")
            continue
        if len(images_to_send) > 0:
            log(f"Images to send = {len(images_to_send)}")
            imagefile = images_to_send.pop(0)
            img = image.Image(imagefile)
            imgbytes = img.bytearray()
            transmission_start = time_msec()
            if running_as_cc():
                sent_succ = await asyncio.create_task(upload_image(my_addr, imgbytes))
            else:
                sent_succ = await asyncio.create_task(send_image_to_mesh(imgbytes))
            if not sent_succ:
                images_to_send.append(imagefile) # pushed to back of queue

            transmission_end = time_msec()
            transmission_time = transmission_end - transmission_start
            log(f"Image transmission completed in {transmission_time} ms ({transmission_time/1000:.4f} seconds)")
            await asyncio.sleep(PHOTO_SENDING_DELAY)

# If N messages seen in the last M minutes.
def scan_process(mid, msg):
    # Input: mid: bytes, msg: bytes containing node address; Output: None (updates seen neighbours)
    nodeaddr = int.from_bytes(msg)
    if nodeaddr not in seen_neighbours:
        log(f"Adding nodeaddr {nodeaddr} to seen_neighbours")
        seen_neighbours.append(nodeaddr)

async def spath_process(mid, msg):
    # Input: mid: bytes, msg: str shortest-path data; Output: None (updates shortest_path_to_cc and propagates)
    global shortest_path_to_cc
    if running_as_cc():
        # log(f"Ignoring shortest path since I am cc")
        return
    if len(msg) == 0:
        log(f"Empty spath")
        return
    spath = [int(x) for x in msg.split(",")]
    if my_addr in spath:
        log(f"Cyclic, ignoring {my_addr} already in {spath}")
        return
    if len(shortest_path_to_cc) == 0 or len(shortest_path_to_cc) > len(spath):
        log(f"Updating spath to {spath}")
        shortest_path_to_cc = spath
        for n in seen_neighbours:
            nsp = [my_addr] + spath
            nmsg = ",".join([str(x) for x in nsp])
            log(f"Propogating spath from {spath} to {nmsg}")
            asyncio.create_task(send_msg("S", int(mid[1]), nmsg.encode(), n))

def process_message(data):
    # Input: data: bytes raw LoRa payload; Output: bool indicating if message was processed
    log(f"[RECV {len(data)}] {data} at {time_msec()}")
    parsed = parse_header(data)
    if not parsed:
        log(f" ######## ***** @@@@@@@@ Failure parsing incoming data : {data}")
        return False
    if random.randint(1,100) <= FLAKINESS:
        log(f"Flakiness dropping {data}")
        return True
    mid, mst, creator, sender, receiver, msg = parsed
    if sender not in recv_msg_count:
        recv_msg_count[sender] = 0
    recv_msg_count[sender] += 1
    if receiver != -1 and my_addr != receiver:
        log(f"Strange that {my_addr} is not as {receiver}")
        log(f"Skipping message as it is not for me but for {receiver} : {mid}")
        return
    if receiver == -1 :
        log(f"processing broadcast message : {data} : {parsed}")
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
            log(f"ERROR: decoding unicode {e} : {msg}")
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
                log(f"No recompiled, so not sending")
        else:
            ackmessage += b":" + missing_str.encode()
            asyncio.create_task(send_msg("A", my_addr, ackmessage, sender))
    else:
        log(f"Unseen messages type {mst} in {msg}")
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
        log(f"Going to validate neighbours : {seen_neighbours}")
        to_be_removed = []
        for n in seen_neighbours:
            msgbytes = b"Nothing"
            success = await send_msg("V", my_addr, msgbytes, n)
            if success:
                log(f"Glad to see that neighbour {n} is still within reach")
            else:
                log(f"Ohno, will have to drop this neighbour : {n}")
                to_be_removed.append(n)
                if n in shortest_path_to_cc:
                    log(f"Even sadder that this was my shortest path to CC which I am now clearing")
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
    log(f"Will send HB to {destlist}")

    gps_coords = read_gps_from_file()
    gps_staleness = get_gps_file_staleness()

    # my_addr : uptime (seconds) : photos taken : events seen : gpslat,gpslong : gps_staleness(seconds) : neighbours([221,222]) : shortest_path([221,9])
    hbmsgstr = f"{my_addr}:{time_sec()}:{total_image_count}:{person_image_count}:{gps_coords}:{gps_staleness}:{seen_neighbours}:{shortest_path_to_cc}"
    log(f"HBSTR = {hbmsgstr}")
    hbmsg = hbmsgstr.encode()
    msgbytes = encrypt_if_needed("H", hbmsg)
    sent_succ = False
    if running_as_cc():
        heartbeat_payload =  {
                "machine_id": my_addr,
                "message_type": "heartbeat",
                "heartbeat_data": msgbytes,
            }
        log(f"Sending raw heartbeat data of length {len(heartbeat_payload)} bytes")
        sent_succ = await upload_heartbeat(heartbeat_payload)
        return sent_succ
    else:
        for peer_addr in destlist:
            log(f"Sending HB to {peer_addr}")
            sent_succ = await send_msg("H", my_addr, msgbytes, peer_addr)
            if sent_succ:
                consecutive_hb_failures = 0
                log(f"heartbeat sent successfully to {peer_addr}")
                return True
    return False

async def keep_sending_heartbeat():
    # Input: None; Output: None (loops to periodically send heartbeats and handle retries)
    global consecutive_hb_failures
    i = 1
    while True:
        await asyncio.sleep(3)
        global image_in_progress
        if image_in_progress:
            log(f"Skipping HB send because image in progress")
            await asyncio.sleep(200)
            continue
        log(f"In send HB loop, Shortest path = {shortest_path_to_cc}")
        sent_succ = await asyncio.create_task(send_heartbeat())
        if not sent_succ:
            consecutive_hb_failures += 1
            log(f"Failed to send heartbeat, consecutive failures = {consecutive_hb_failures}")
            if consecutive_hb_failures > 1:
                log(f"Too many consecutive failures, reinitializing LoRa")
                try:
                    await init_lora()
                    consecutive_hb_failures = 0
                except Exception as e:
                    log(f"ERROR: reinitializing LoRa: {e}")
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
            log(f"Skipping scan send because image in progress")
            await asyncio.sleep(SCAN_WAIT)
            continue
        scanmsg = encode_node_id(my_addr)
        # 65535 is for Broadcast
        await send_msg_internal("N", my_addr, scanmsg, 65535)
        if i < DISCOVERY_COUNT:
            await asyncio.sleep(SCAN_WAIT)
        else:
            await asyncio.sleep(SCAN_WAIT_2 + random.randint(1,120))
        log(f"{my_addr} : Seen neighbours = {seen_neighbours}, Shortest path = {shortest_path_to_cc}, Sent messages = {sent_count}, Received messages = {recv_msg_count}")
        i = i + 1

async def send_spath():
    # Input: None; Output: None (periodically shares shortest-path information with neighbours)
    i = 1
    while True:
        global image_in_progress
        if image_in_progress:
            log(f"Skipping spath send because image in progress")
            await asyncio.sleep(200)
            continue
        sp = f"{my_addr}"
        for n in seen_neighbours:
            log(f"Sending shortest path to {n}")
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
    log(f"Gonna execute_command {command} on {my_addr}")
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
        log(f"Could not decode {msg} : {e}")
    parts = msgstr.split(";")
    if len(parts) != 3:
        log(f"ERROR: parsing msgstr")
    dest = int(parts[0])
    cpath = parts[1].split(",")
    command = parts[2]
    if dest == my_addr:
        execute_command(command)
        return
    next_dest = get_next_on_path(cpath)
    if next_dest is not None:
        log(f"Propogating command to {next_dest}")
        await send_msg("C", my_addr, msgstr.encode(), next_dest)
    else:
        log(f"Next dest seems None for {msg}")

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
            log(f"Skipping print summary because image in progress")
            await asyncio.sleep(200)
            continue
        log(f"Randomly sending a command {command} to {dest}, via {cpath}")
        if dest == my_addr:
            execute_command(command)
            continue
        next_dest = get_next_on_path(cpath)
        if next_dest is not None:
            log(f"Propogating command to {next_dest}")
            cpathstr = ",".join(str(x) for x in cpath)
            command = f"{dest};{cpathstr};{command}"
            await send_msg("C", my_addr, command.encode(), next_dest)
        else:
            log(f"Next dest seems to be None")

# ---------------------------------------------------------------------------
# Monitoring and Logging
# ---------------------------------------------------------------------------

async def print_summary_and_flush_logs():
    # Input: None; Output: None (periodically logs status metrics and flushes logs)
    while True:
        await asyncio.sleep(30)
        global image_in_progress
        if image_in_progress:
            log(f"Skipping print summary because image in progress")
            await asyncio.sleep(200)
            continue
        log(f"Sent : {len(msgs_sent)} Recd : {len(msgs_recd)} Unacked : {len(msgs_unacked)} LoRa reinits: {lora_reinit_count}")
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
    log("Initializing GPS...")

    # Wait for LoRa to settle
    await asyncio.sleep(3)

    try:
        uart = gps_driver.SC16IS750(spi_bus=1, cs_pin="P3")
        uart.init_gps()
        gps = gps_driver.GPS(uart)
        log("GPS hardware initialized successfully - starting continuous read loop")
    except Exception as e:
        log(f"GPS initialization failed: {e}")
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
                    log(f"GPS: {gps_str}")
                    gps_last_time = time_msec()
                    last_successful_read = read_count
                else:
                    if read_count % 10 == 1:
                        log("GPS has fix but no coordinates")
            else:
                if read_count % 20 == 1:
                    log("GPS has no fix")
                    # Show raw data for debugging
                    raw_debug = uart.read_data()
                    if raw_debug:
                        sample = raw_debug[:60].replace('\r', '\\r').replace('\n', '\\n')
                        log(f"GPS raw: {sample}")

            # Clear buffer periodically to prevent overflow
            if read_count % 30 == 0:
                while uart.read_data():  # Clear all buffered data
                    pass
                gps.buffer = ""  # Clear internal parser buffer
                log("GPS buffer cleared")

            # Reinitialize if too many failures
            if last_successful_read > 0 and (read_count - last_successful_read) > 100:
                log("GPS not working, reinitializing...")
                try:
                    uart.init_gps()
                    gps = gps_driver.GPS(uart)
                    await asyncio.sleep(2)
                    last_successful_read = read_count
                except Exception as e:
                    log(f"GPS reinit failed: {e}")
                    await asyncio.sleep(10)

        except Exception as e:
            log(f"GPS read error: {e}")
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
        log("WiFi is disabled (WIFI_ENABLED = False)")
        return False

    try:
        log(f"Initializing WiFi connection to SSID: {WIFI_SSID}")
        # Create WLAN interface in station mode
        wifi_nic = network.WLAN(network.WLAN.IF_STA)

        # Activate the interface
        wifi_nic.active(True)

        # Connect to WiFi access point
        log(f"Connecting to WiFi network: {WIFI_SSID}")
        wifi_nic.connect(WIFI_SSID, WIFI_PASSWORD)

        # Wait for connection with timeout
        max_wait = 20  # Maximum wait time in seconds
        wait_count = 0
        while wait_count < max_wait:
            if wifi_nic.isconnected():
                # Connection successful
                ifconfig = wifi_nic.ifconfig()
                log(f"WiFi connected successfully!")
                log(f"IP address: {ifconfig[0]}")
                log(f"Subnet mask: {ifconfig[1]}")
                log(f"Gateway: {ifconfig[2]}")
                log(f"DNS server: {ifconfig[3]}")
                return True

            # Check for connection errors (if status() is available)
            try:
                status = wifi_nic.status()
                # Try to detect common error statuses if constants exist
                if hasattr(network.WLAN, 'STAT_WRONG_PASSWORD') and status == network.WLAN.STAT_WRONG_PASSWORD:
                    log(f"WiFi connection failed: Wrong password")
                    wifi_nic.active(False)
                    return False
                elif hasattr(network.WLAN, 'STAT_NO_AP_FOUND') and status == network.WLAN.STAT_NO_AP_FOUND:
                    log(f"WiFi connection failed: Access point not found")
                    wifi_nic.active(False)
                    return False
                elif hasattr(network.WLAN, 'STAT_CONNECT_FAIL') and status == network.WLAN.STAT_CONNECT_FAIL:
                    log(f"WiFi connection failed: Connection failed")
                    wifi_nic.active(False)
                    return False
                log(f"WiFi connecting... (status: {status}, wait: {wait_count}s)")
            except:
                # Status checking not available, just log wait time
                log(f"WiFi connecting... (wait: {wait_count}s)")

            await asyncio.sleep(1)
            wait_count += 1

        # Timeout
        log(f"WiFi connection timeout after {max_wait} seconds")
        wifi_nic.active(False)
        return False

    except Exception as e:
        log(f"WiFi initialization error: {e}")
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
        log(f"ERROR: getting WiFi status: {e}")
        return {"enabled": True, "connected": False, "error": str(e)}

async def wifi_send_image(creator, encimb):
    # Input: creator: int node id, encimb: bytes encrypted image; Output: bool upload success
    """Send image via WiFi"""
    global wifi_nic
    if not wifi_nic or not wifi_nic.isconnected():
        log("WiFi not connected")
        return False

    try:
        # Try to import requests
        try:
            import requests
            use_requests = True
        except ImportError:
            use_requests = False

        imgbytes = ubinascii.b2a_base64(encimb).decode('utf-8')
        payload = {
            "machine_id": creator,
            "message_type": "event",
            "image": imgbytes,
        }

        if use_requests:
            headers = {"Content-Type": "application/json"}
            json_payload = json.dumps(payload)
            r = requests.post(URL, data=json_payload, headers=headers)
            if r.status_code == 200:
                log(f"Image uploaded via WiFi successfully")
                return True
            else:
                log(f"WiFi upload failed: status {r.status_code}")
                return False
        else:
            # Fallback to socket-based HTTP (not implemented for brevity)
            log("requests library not available, WiFi upload skipped")
            return False

    except Exception as e:
        log(f"ERROR: in wifi_send_image: {e}")
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
            # Convert heartbeat_data bytes to base64 string if needed
            payload = heartbeat_data.copy()
            if "heartbeat_data" in payload:
                hb_data = payload["heartbeat_data"]
                if isinstance(hb_data, bytes):
                    # Convert bytes to base64 string
                    payload["heartbeat_data"] = ubinascii.b2a_base64(hb_data).decode('utf-8').strip()
                elif not isinstance(hb_data, str):
                    # If it's not a string, convert to string
                    payload["heartbeat_data"] = str(hb_data)

            headers = {"Content-Type": "application/json"}
            json_payload = json.dumps(payload)
            r = requests.post(URL, data=json_payload, headers=headers)
            if r.status_code == 200:
                node_id = payload.get("machine_id", "unknown")
                log(f"Heartbeat from node {node_id} sent via WiFi successfully")
                return True
            else:
                log(f"WiFi heartbeat upload failed: status {r.status_code}")
                if hasattr(r, 'text'):
                    log(f"Response: {r.text[:200]}")
                return False
        else:
            log("requests library not available, WiFi upload skipped")
            return False

    except Exception as e:
        log(f"ERROR: in wifi_upload_hb: {e}")
        return False

# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------

async def main():
    # Input: None; Output: None (entry point scheduling initialization and background tasks)
    log(f"[INFO] Started device {my_addr}")

    # Initialize WiFi if enabled
    if WIFI_ENABLED:
        await init_wifi()

    await init_lora()
    asyncio.create_task(radio_read())
    asyncio.create_task(print_summary_and_flush_logs())
    asyncio.create_task(validate_and_remove_neighbours())
    if running_as_cc():
        log(f"Starting command center")
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
