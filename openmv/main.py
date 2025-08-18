import omv
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
import json
import ubinascii

import enc
from sim7600x import SIM7600X
import sx1262

print_lock = asyncio.Lock()

MIN_SLEEP = 0.1
ACK_SLEEP = 0.2
CHUNK_SLEEP = 0.2
HB_WAIT_SEC = 30
SPATH_WAIT = 20
SCAN_WAIT = 10
PHOTO_TAKING_DELAY = 10
PHOTO_SENDING_DELAY = 60

MIDLEN = 7
FLAKINESS = 0
FRAME_SIZE = 195

AIR_SPEED = 62500

ENCRYPTION_ENABLED = True

# -------- Start FPS clock -----------
#clock = time.clock()            # measure frame/sec
image_count = 0                 # Counter to keep tranck of saved images

consecutive_hb_failures = 0
lora_reinit_count = 0

COMMAN_CENTER_ADDR = 9
my_addr = None
shortest_path_to_cc = []
seen_neighbours = []

rtc = RTC()
uid = binascii.hexlify(machine.unique_id())      # Returns 8 byte unique ID for board
print("Running on device : " + uid.decode())
if uid == b'e076465dd7194025':
    my_addr = 222
    #shortest_path_to_cc = [1, 9]
elif uid == b'e076465dd7091027':
    my_addr = 221
    #shortest_path_to_cc = [9]
elif uid == b'e076465dd7194211':
    my_addr = 9
elif uid == b'e076465dd7193a09':
    my_addr = 223
    shortest_path_to_cc = [9]
else:
    print("Unknown device ID for " + omv.board_id())
    sys.exit()
clock_start = utime.ticks_ms() # get millisecond counter

# ------ Configuration for tensorflow model ------
MODEL_PATH = "/rom/person_detect.tflite"
model = ml.Model(MODEL_PATH)
print(" Model loaded:", model)
CONFIDENCE_THRESHOLD = 0.75
IMG_DIR = "/sdcard/images/"

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)

sent_count = 0
recv_msg_count = {}

URL = "https://n8n.vyomos.org/webhook/watchmen-detect/"

sim = None

async def init_sim():
    global sim
    print("Initializing 4G connection...")
    sim = SIM7600X(uart_id=1, baudrate=115200)
    if not sim.init_module(apn="airtelgprs.com"):  # Use your carrier's APN
        print("4G connection failed!")
        return False
    print(" ================ >>> 4G Connected successfully!")

async def sim_send_image(creator, fname):
    global sim
    img = image.Image(fname)
    imb = img.bytearray()
    encimb = encrypt_if_needed("P", imb)
    imgbytes = ubinascii.b2a_base64(encimb)
    print(f" ================ >>> Sending file of size {len(imgbytes)}")
    payload = {
        "machine_id": creator,
        "message_type": "event",
        "image": imgbytes,
    }
    json_payload = json.dumps(payload)
    print(json_payload)
    success, response = sim.http_post(URL, json_payload)
    if success:
        print(f"HB Data uploaded to server successfully : {response}")
        return True
    else:
        print(f"Failure uploading HB {response}")
        return False

# TODO add heartbeat also to sim

loranode = None

async def init_lora():
    global loranode, lora_reinit_count
    lora_reinit_count += 1
    print(f"Initializing LoRa SX126X module... my lora addr = {my_addr}")
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

    print(f"LoRa module initialized successfully! (Total reinitializations: {lora_reinit_count})")
    print(f"Node address: {loranode.addr}")
    print(f"Frequency: {loranode.start_freq + loranode.offset_freq}.125MHz")

def running_as_cc():
    return my_addr == COMMAN_CENTER_ADDR

# ------- Person Detection + snapshot ---------
# TODO(anand): Test with IR lense for person detection in Night
def detect_person(img):
    prediction = model.predict([img])
    scores = zip(model.labels, prediction[0].flatten().tolist())
    scores = sorted(scores, key=lambda x: x[1], reverse=True)  # Highest confidence first
    p_conf = 0.0
    for label, conf in scores:
        if label == "person":
            p_conf = conf
            if conf >= CONFIDENCE_THRESHOLD:
                return (True, p_conf)
    return (False, p_conf)

images_to_send = []

# ------- Person detection loop ---------
# TODO this should save files and then put them in a queue which radio should send.
# Else we are blocking photos until radio.
# Else we are also not retrying if transmission of a photo fails.
async def person_detection_loop():
    global image_count
    while True:
        img = sensor.snapshot()
        image_count += 1
        print(f"Image count: {image_count}")
        person_detected, confidence = detect_person(img)
        print(f"Person detected = {person_detected}, confidence = {confidence}")
        #if person_detected:
        if True:
            r = get_rand()
            raw_path = f"raw_{r}_{person_detected}_{confidence:.2f}.jpg"
            print(f"Saving image to {raw_path}")
            img.save(raw_path)
            images_to_send.append(raw_path)
        await asyncio.sleep(PHOTO_TAKING_DELAY)

async def image_sending_loop():
    global images_to_send
    while True:
        await asyncio.sleep(5)
        if len(shortest_path_to_cc) == 0:
            print("No shortest path yet so cant send")
            continue
        if len(images_to_send) > 0:
            print(f"Images to send = {len(images_to_send)}")
            imagefile = images_to_send.pop(0)
            img = image.Image(imagefile)
            imgbytes = img.bytearray()
            print(f"Sending {len(imgbytes)} bytes to the network")
            msgbytes = encrypt_if_needed("P", imgbytes)

            peer_addr = shortest_path_to_cc[0]
            transmission_start = time_msec()
            await send_msg("P", my_addr, msgbytes, peer_addr)
            # If failure, retry and put it back in queue
            transmission_end = time_msec()

            transmission_time = transmission_end - transmission_start
            print(f"Image transmission completed in {transmission_time} ms ({transmission_time/1000:.4f} seconds)")
            await asyncio.sleep(PHOTO_SENDING_DELAY)
            # Draw visual annotations on the image
            # img.draw_rectangle((0, 0, img.width(), img.height()), color=(255, 0, 0), thickness=2)  # Full image border
            # img.draw_string(4, 4, f"Person: {confidence:.2f}", color=(255, 255, 255), scale=2)      # Label text
            # TODO(anand): As we are have a memory constrain on the sd card(<=2GB), Need to calculate max number of images that can be saved and how images will be deleted after transmission.
            # processed_path = f"{IMG_DIR}/processed_{image_count}.jpg"
            # img.save(processed_path)  # Save image with annotations

def get_human_ts():
    _,_,_,_,h,m,s,_ = rtc.datetime()
    t=f"{m}:{s}"
    return t

def log(msg):
    t = get_human_ts()
    print(f"{t} : {msg}")

msgs_sent = []
msgs_unacked = []
msgs_recd = []

# MSG TYPE = H(eartbeat), A(ck), B(egin), E(nd), C(hunk), S(hortest path)

def time_msec():
    delta = utime.ticks_diff(utime.ticks_ms(), clock_start) # compute time difference
    return delta

def time_sec():
    return utime.ticks_diff(utime.ticks_ms(), clock_start) # compute time difference

def get_rand():
    rstr = ""
    for i in range(3):
        rstr += chr(65+random.randint(0,25))
    return rstr

# TypeSourceDestRRRandom
def get_msg_id(msgtype, creator, dest):
    rrr = get_rand()
    if dest == 0 or dest == 65535:
        mid = msgtype.encode() + creator.to_bytes() + my_addr.to_bytes() + b'*' + rrr.encode()
    else:
        mid = msgtype.encode() + creator.to_bytes() + my_addr.to_bytes() + dest.to_bytes() + rrr.encode()
    return mid

def parse_header(data):
    mid = b""
    if data == None:
        print(f"Weird that data is none")
        return None
    if len(data) < 9:
        return None
    try:
        mid = data[:MIDLEN]
    except Exception as e:
        print(f"ERROR PARSING {data[:MIDLEN]}  :  Error : {e}")
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
    if len(msg) > 200:
        return msg[:100] + "......." + msg[-100:]
    return msg

def ack_needed(msgtype):
    if msgtype == "A":
        return False
    if msgtype in ["H", "B", "E"]:
        return True
    return False

# === Async Receiver for openmv ===
async def radio_read():
    while True:
        message = loranode.receive()
        if message:
            message = message.replace(b"{}[]", b"\n")
            process_message(message)
        await asyncio.sleep(0.1)

def radio_send(dest, data):
    global sent_count
    sent_count = sent_count + 1
    lendata = len(data)
    if len(data) > 254:
        print(f"Error msg too large : {len(data)}")
    #data = lendata.to_bytes(1) + data
    data = data.replace(b"\n", b"{}[]")
    loranode.send(dest, data)
    log(f"[SENT at {len(data)} bytes] {data} at {time_msec()}")

def pop_and_get(mid):
    for i in range(len(msgs_unacked)):
        m, d, t = msgs_unacked[i]
        if m == mid:
            return msgs_unacked.pop(i)
    return None

async def send_single_msg(msgtype, creator, msgbytes, dest):
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
        return (True, [])
    for retry_i in range(3):
        radio_send(dest, databytes)
        await asyncio.sleep(ACK_SLEEP if ackneeded else MIN_SLEEP)
        for i in range(5):
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
    chunks = []
    while len(msg) > 200:
        chunks.append(msg[0:200])
        msg = msg[200:]
    if len(msg) > 0:
        chunks.append(msg)
    return chunks

def encrypt_if_needed(mst, msg):
    if not ENCRYPTION_ENABLED:
        return msg
    if mst in ["H"]:
        # Must be less than 117 bytes
        if len(msg) > 117:
            print(f"Message {msg} is lnger than 117 bytes, cant encrypt via RSA")
            return msg
        msgbytes = enc.encrypt_rsa(msg, enc.load_rsa_pub())
        print(f"{mst} : Len msg = {len(msg)}, len msgbytes = {len(msgbytes)}")
        return msgbytes
    if mst == "P":
        msgbytes = enc.encrypt_hybrid(msg, enc.load_rsa_pub())
        print(f"{mst} : Len msg = {len(msg)}, len msgbytes = {len(msgbytes)}")
        return msgbytes
    return msg

# === Send Function ===
def send_msg_internal(msgtype, creator, msgbytes, dest):
    if msgtype == "P":
        print(f"Sending photo of length {len(msgbytes)}")
    else:
        print(f"Sending message {msgbytes}")
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
        if i % 10 == 0:
            print(f"Sending chunk {i}")
        await asyncio.sleep(CHUNK_SLEEP)
        chunkbytes = imid.encode() + i.to_bytes(2) + chunks[i]
        _ = await send_single_msg("I", creator, chunkbytes, dest)
    for retry_i in range(50):
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
            _ = await send_single_msg("I", creator, chunkbytes, dest)
    return False

async def send_msg(msgtype, creator, msgbytes, dest):
    retval = await send_msg_internal(msgtype, creator, msgbytes, dest)
    return retval

def ack_time(smid):
    print(f"Finding {smid} in {msgs_recd}")
    for (rmid, msgbytes, t) in msgs_recd:
        if chr(rmid[0]) == "A":
            print(f"Found an ack {rmid} : {msgbytes}")
            if smid == msgbytes[:MIDLEN]:
                missingids = []
                if msg[0] == 'E' and len(msg) > (MIDLEN+1):
                    print(f"Checking for missing IDs in {msgbytes[MIDLEN+1:]}")
                    missingstr = msgbytes[MIDLEN+1:]
                    missingids = [int(i) for i in missingstr.split(',')]
                return (t, missingids)
    return (-1, None)

async def log_status():
    await asyncio.sleep(1)
    async with print_lock:
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
        async with print_lock:
            log(f"[ACK Times] 50% = {mid:.2f}s, 90% = {p90:.2f}s")
            log(f"So far {len(msgs_not_acked)} messsages havent been acked")
            log(msgs_not_acked)

chunk_map = {} # chunk ID to (expected_chunks, [(iter, chunk_data)])

def begin_chunk(msg):
    parts = msg.split(":")
    if len(parts) != 3:
        log(f"ERROR : begin message unparsable {msg}")
        return
    mst = parts[0]
    cid = parts[1]
    numchunks = int(parts[2])
    chunk_map[cid] = (mst, numchunks, [])

def get_missing_chunks(cid):
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
    if len(msgbytes) < 5:
        log(f"ERROR : Not enough bytes {len(msgbytes)} : {msgbytes}")
        return
    cid = msgbytes[0:3].decode()
    citer = int.from_bytes(msgbytes[3:5])
    print(f"Got chunk id {citer}")
    cdata = msgbytes[5:]
    if cid not in chunk_map:
        log(f"ERROR : no entry yet for {cid}")
    chunk_map[cid][2].append((citer, cdata))
    _, expected_chunks, _ = chunk_map[cid]
    missing = get_missing_chunks(cid)
    received = expected_chunks - len(missing)
    print(f" ===== Got {received} / {expected_chunks} chunks ====")

def get_data_for_iter(list_chunks, chunkiter):
    for citer, chunk_data in list_chunks:
        if citer == chunkiter:
            return chunk_data
    return None

def recompile_msg(cid):
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
    if cid in chunk_map:
        chunk_map.pop(cid)
    else:
        print(f"Couldnt find {cid} in {chunk_map}")

# Note only sends as many as wouldnt go beyond frame size
# Assumption is that subsequent end chunks would get the rest
def end_chunk(mid, msg):
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
            print(f"Ignoring this because we dont have an entry for this chunkid, likely because we have already processed this.")
            return (True, None, None, None, None)
        recompiled = recompile_msg(cid)
        return (True, None, cid, recompiled, creator)

hb_map = {}

def hb_process(mid, msgbytes):
    creator = int(mid[1])
    if running_as_cc():
        if creator not in hb_map:
            hb_map[creator] = 0
        hb_map[creator] += 1
        print(f"HB Counts = {hb_map}")
        print(f"Images saved at cc so far = {len(images_saved_at_cc)}")
        for i in images_saved_at_cc:
            print(i)
        if ENCRYPTION_ENABLED:
            print(f"Only for debugging : HB msg = {enc.decrypt_rsa(msgbytes, enc.load_rsa_prv())}")
        else:
            print(f"Only for debugging : HB msg = {msgbytes.decode()}")
        return
    if len(shortest_path_to_cc) > 0:
        peer_addr = shortest_path_to_cc[0]
        print(f"Propogating H to {peer_addr}")
        asyncio.create_task(send_msg("H", creator, msgbytes, peer_addr))
    else:
        print(f"Can't forward HB because I dont have Spath yet")

images_saved_at_cc = []

def img_process(cid, msg, creator):
    clear_chunkid(cid)
    # TODO save image
    if running_as_cc():
        print(f"Received image of size {len(msg)}")
        if ENCRYPTION_ENABLED:
            img_bytes = enc.decrypt_hybrid(msg, enc.load_rsa_prv())
        else:
            img_bytes = msg
        img = image.Image(320, 240, image.JPEG, buffer=img_bytes)
        print(len(img_bytes))
        fname = f"cc_{creator}_{cid}.jpg"
        print(f"Saving to file {fname}")
        images_saved_at_cc.append(fname)
        img.save(fname)
        asyncio.create_task(sim_send_image(creator, fname))
    else:
        if len(shortest_path_to_cc) > 0:
            peer_addr = shortest_path_to_cc[0]
            print(f"Propogating Image to {peer_addr}")
            #await send_msg("P", creator, msg, peer_addr)
            asyncio.create_task(send_msg("P", creator, msg, peer_addr))
        else:
            print(f"Can't forward Photo because I dont have Spath yet")

# If N messages seen in the last M minutes.
def scan_process(mid, msg):
    nodeaddr = int.from_bytes(msg)
    if nodeaddr not in seen_neighbours:
        print(f"Adding nodeaddr {nodeaddr} to seen_neighbours")
        seen_neighbours.append(nodeaddr)

def spath_process(mid, msg):
    global shortest_path_to_cc
    if running_as_cc():
        # print(f"Ignoring shortest path since I am cc")
        return
    if len(msg) == 0:
        print(f"Empty spath")
        return
    spath = [int(x) for x in msg.split(",")]
    if my_addr in spath:
        print(f"Cyclic, ignoring {my_addr} already in {spath}")
        return
    if len(shortest_path_to_cc) == 0 or len(shortest_path_to_cc) > len(spath):
        print(f"Updating spath to {spath}")
        shortest_path_to_cc = spath
        for n in seen_neighbours:
            nsp = [my_addr] + spath
            nmsg = f"{nsp}"
            print(f"Propogating spath from {spath} to {nmsg}")
            asyncio.create_task(send_msg("S", int(mid[1]), nmsg.encode(), n))

def process_message(data):
    log(f"[RECV {len(data)}] {data} at {time_msec()}")
    parsed = parse_header(data)
    if not parsed:
        log(f"Failure parsing incoming data : {data}")
        return False
    if random.randint(1,100) <= FLAKINESS:
        log(f"Flakiness dropping {data}")
        return True
    mid, mst, creator, sender, receiver, msg = parsed
    if sender not in recv_msg_count:
        recv_msg_count[sender] = 0
    recv_msg_count[sender] += 1
    if receiver != -1 and my_addr != receiver:
        print(f"Strange that {my_addr} is not as {receiver}")
        log(f"Skipping message as it is not for me but for {receiver} : {mid}")
        return
    if receiver == -1 :
        print(f"processing broadcast message : {data} : {parsed}")
    msgs_recd.append((mid, msg, time_msec()))
    ackmessage = mid
    if mst == "N":
        scan_process(mid, msg)
    elif mst == "S":
        spath_process(mid, msg.decode())
    elif mst == "H":
        asyncio.create_task(send_msg("A", my_addr, ackmessage, sender))
        hb_process(mid, msg)
    elif mst == "B":
        asyncio.create_task(send_msg("A", my_addr, ackmessage, sender))
        try:
            begin_chunk(msg.decode())
        except Exception as e:
            print(f"Error decoding unicode {e} : {msg}")
    elif mst == "I":
        add_chunk(msg)
    elif mst == "E":
        alldone, retval, cid, recompiled, creator = end_chunk(mid, msg.decode())
        if alldone:
            # Also when it fails
            ackmessage += ":-1"
            asyncio.create_task(send_msg("A", my_addr, ackmessage.encode(), sender))
            if recompiled:
                img_process(cid, recompiled, creator)
            else:
                print(f"No recompiled, so not sending")
        else:
            ackmessage += f":{retval}"
            asyncio.create_task(send_msg("A", my_addr, ackmessage.encode(), sender))
    else:
        print(f"Unseen messages type {mst} in {msg}")
    return True

async def send_heartbeat():
    global consecutive_hb_failures
    while True:
        # TODO add last known GPS here also.
        print(f"Shortest path = {shortest_path_to_cc}")
        if len(shortest_path_to_cc) > 0:
            hbmsgstr = f"{my_addr}:{get_human_ts()}"
            hbmsg = hbmsgstr.encode()
            peer_addr = shortest_path_to_cc[0]
            msgbytes = encrypt_if_needed("H", hbmsg)
            success = await send_msg("H", my_addr, msgbytes, peer_addr)
            if success:
                consecutive_hb_failures = 0
                print(f"heartbeat sent successfully to {peer_addr}")
            else:
                consecutive_hb_failures += 1
                print(f"Failed to send heartbeat to {peer_addr}, consecutive failures = {consecutive_hb_failures}")
                if consecutive_hb_failures > 1:
                    print(f"Too many consecutive failures, reinitializing LoRa")
                    try:
                        await init_lora()
                        consecutive_hb_failures = 0
                    except Exception as e:
                        print(f"Error reinitializing LoRa: {e}")
        else:
            print("Not sending heartbeat right now because i dont know my shortest path")
        await asyncio.sleep(HB_WAIT_SEC)

async def send_scan():
    global seen_neighbours
    i = 1
    while True:
        scanmsg = my_addr.to_bytes()
        # 0 is for Broadcast
        await send_msg("N", my_addr, scanmsg, 65535)
        await asyncio.sleep(SCAN_WAIT) # reduce after setup
        print(f"{my_addr} : Seen neighbours = {seen_neighbours}, Shortest path = {shortest_path_to_cc}, Sent messages = {sent_count}, Received messages = {recv_msg_count}")
        i = i + 1

async def send_spath():
    while True:
        sp = f"{my_addr}"
        for n in seen_neighbours:
            print(f"Sending shortest path to {n}")
            await send_msg("S", my_addr, sp.encode(), n)
        await asyncio.sleep(SPATH_WAIT)

async def print_summary():
    while True:
        await asyncio.sleep(30)
        print(f"Sent : {len(msgs_sent)} Recd : {len(msgs_recd)} Unacked : {len(msgs_unacked)} LoRa reinits: {lora_reinit_count}")
        #print(msgs_sent)
        #print(msgs_recd)
        #print(msgs_unacked)

def image_test():
    r = get_rand()
    print(r)
    img = sensor.snapshot()
    print(img.size())
    print(img.to_jpeg().size())
    im2 = image.Image(320, 240, image.RGB565, data=img.bytearray())
    im3 = image.Image(320, 240, image.JPEG, buffer=img.to_jpeg().bytearray())
    img.save(f"{r}.jpg")
    im2.save(f"reconstructed_{r}.jpg")
    im3.save(f"reconstructed_jpeg_{r}.jpg")

async def main():
    log(f"[INFO] Started device {my_addr}")
    await init_lora()
    asyncio.create_task(radio_read())
    asyncio.create_task(print_summary())
    if my_addr != COMMAN_CENTER_ADDR:
        asyncio.create_task(send_heartbeat())
        # asyncio.create_task(send_scan())
        # asyncio.create_task(person_detection_loop())
        # asyncio.create_task(image_sending_loop())
    else:
        print(f"Starting command center")
        # await init_sim()
        # asyncio.create_task(send_spath())
        # asyncio.create_task(send_scan())
    for i in range(24*7):
        await asyncio.sleep(3600)
        print(f"Finished HOUR {i}")

try:
    asyncio.run(main())
except KeyboardInterrupt:
    log("Stopped.")
