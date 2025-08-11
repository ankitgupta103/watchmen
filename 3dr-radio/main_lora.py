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
    import image
    import ml
    import os                   # file system access
    import time
    import binascii
    import machine
    import enc
    import sx1262
else:
    import asyncio
    import serial
    import time as utime
    from time import gmtime, strftime
import sys
import random

# Local libraries
import radio

print_lock = asyncio.Lock()

UART_BAUDRATE = 57600
USBA_BAUDRATE = 57600
MIN_SLEEP = 0.1
ACK_SLEEP = 0.5
CHUNK_SLEEP = 0.1

HB_WAIT_SEC = 30

MIDLEN = 7
FLAKINESS = 0

FRAME_SIZE = 225

TRANSFERRING_IMAGE = False
RECEIVING_IMAGE = False
CURRENT_NETID = 0

# -------- Start FPS clock -----------
#clock = time.clock()            # measure frame/sec
image_count = 0                 # Counter to keep tranck of saved images

my_addr = None
peer_addr = None

NET_ID_MAP = {
        "A" : 1,
        "B" : 2,
        "C" : 3,
        "Z" : 9
        }

def get_net_id(node_addr=None):
    if node_addr == None:
        return NET_ID_MAP[my_addr]
    return NET_ID_MAP[node_addr]

time_of_last_radio_receive = 0

if run_omv:
    rtc = RTC()
    uid = binascii.hexlify(machine.unique_id())      # Returns 8 byte unique ID for board
    print("Running on device : " + uid.decode())
    if uid == b'e076465dd7194025':
        my_addr = 'B'
    elif uid == b'e076465dd7091027':
        my_addr = 'A'
    elif uid == b'e076465dd7194211':
        my_addr = 'Z'
    else:
        print("Unknown device ID for " + omv.board_id())
        sys.exit()
    clock_start = utime.ticks_ms() # get millisecond counter
    UART_PORT = 1
    uart = UART(UART_PORT, baudrate=UART_BAUDRATE, timeout=1000)
    uart.init(UART_BAUDRATE, bits=8, parity=None, stop=1)

    # ------ Configuration for tensorflow model ------
    MODEL_PATH = "/rom/person_detect.tflite"
    model = ml.Model(MODEL_PATH)
    print(" Model loaded:", model)

    IMG_DIR = "/sdcard/images/"
    CONFIDENCE_THRESHOLD = 0.5

    sensor.reset()
    sensor.set_pixformat(sensor.RGB565)
    sensor.set_framesize(sensor.QVGA)
    sensor.skip_frames(time=2000)
else:
    my_addr = 'ZZZZ'
    #USBA_PORT = "/dev/ttyUSB0"
    USBA_PORT = "/dev/tty.usbserial-0001"
    try:
        uart = serial.Serial(USBA_PORT, USBA_BAUDRATE, timeout=0.1)
    except serial.SerialException as e:
        print(f"[ERROR] Could not open serial port {USBA_PORT}: {e}")
        sys.exit(1)
    clock_start = int(utime.time() * 1000)

shortest_path_to_cc = []
if my_addr == "A":
    shortest_path_to_cc = ["Z"]
elif my_addr == "B":
    shortest_path_to_cc = ["A", "Z"]
else:
    shortest_path_to_cc = []
seen_neighbours = []

sent_count = 0
recv_msg_count = {}

def running_as_cc():
    return my_addr == "Z"

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


# ------- Person detection loop ---------
async def person_detection_loop():
    global image_count
    while True:
        img = sensor.snapshot()
        image_count += 1
        print(f"Image count: {image_count}")
        person_detected, confidence = detect_person(img)
        print(f"Person detected = {person_detected}, confidence = {confidence}")
        if person_detected:
            r = get_rand()
            if len(shortest_path_to_cc) > 0:
                peer_addr = shortest_path_to_cc[0]
                imgbytes = img.to_jpeg().bytearray()
                print(f"Sending {len(imgbytes)} bytes to the network")
                msgbytes = encrypt_if_needed("P", imgbytes)
                global TRANSFERRING_IMAGE
                TRANSFERRING_IMAGE = True
                await send_msg("P", my_addr, msgbytes, peer_addr)
                TRANSFERRING_IMAGE = False
            #raw_path = f"{IMG_DIR}raw_{r}_{person_detected}_{confidence:.2f}.jpg"
            #img2 = image.Image(320, 240, image.RGB565, buffer=img.bytearray())
            #print(f"Saving image to {raw_path}")
            #img2.save(raw_path)

            # Draw visual annotations on the image
            # img.draw_rectangle((0, 0, img.width(), img.height()), color=(255, 0, 0), thickness=2)  # Full image border
            # img.draw_string(4, 4, f"Person: {confidence:.2f}", color=(255, 255, 255), scale=2)      # Label text
            # TODO(anand): As we are have a memory constrain on the sd card(<=2GB), Need to calculate max number of images that can be saved and how images will be deleted after transmission.
            # processed_path = f"{IMG_DIR}/processed_{image_count}.jpg"
            # img.save(processed_path)  # Save image with annotations
        await asyncio.sleep(30)

def get_human_ts():
    if run_omv:
        _,_,_,_,h,m,s,_ = rtc.datetime()
        t=f"{m}:{s}"
    else:
        t = strftime("%M:%S", gmtime())
    return t

def log(msg):
    t = get_human_ts()
    print(f"{t} : {msg}")

msgs_sent = []
msgs_unacked = []
msgs_recd = []

# MSG TYPE = H(eartbeat), A(ck), B(egin), E(nd), C(hunk), S(hortest path)

def time_msec():
    if run_omv:
        delta = utime.ticks_diff(utime.ticks_ms(), clock_start) # compute time difference
    else:
        delta = int(utime.time() * 1000) - clock_start
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
    mid = f"{msgtype}{creator}{my_addr}{dest}{rrr}"
    return mid

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

def radio_send(data):
    global sent_count
    sent_count = sent_count + 1
    lendata = len(data)
    if len(data) > 254:
        print(f"Error msg too large : {len(data)}")
    data = lendata.to_bytes(1) + data
    uart.write(data)
    log(f"[SENT at {CURRENT_NETID} {len(data)} bytes] {data} at {time_msec()}")

def pop_and_get(mid):
    for i in range(len(msgs_unacked)):
        m, d, t = msgs_unacked[i]
        if m == mid:
            return msgs_unacked.pop(i)
    return None

async def send_single_msg(msgtype, creator, msgbytes, dest):
    mid = get_msg_id(msgtype, creator, dest)
    databytes = mid.encode() + b";" + msgbytes
    ackneeded = dest != "*" and ack_needed(msgtype)
    unackedid = 0
    timesent = time_msec()
    if ackneeded:
        unackedid = len(msgs_unacked)
        msgs_unacked.append((mid, msgbytes, timesent))
    else:
        msgs_sent.append((mid, msgbytes, timesent))
    if not ackneeded:
        radio_send(databytes)
        return (True, [])
    for retry_i in range(5):
        radio_send(databytes)
        await asyncio.sleep(ACK_SLEEP if ackneeded else MIN_SLEEP)
        for i in range(3):
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

def switch_netid(netid):
    global CURRENT_NETID
    if CURRENT_NETID == netid:
        return
    print(f"Switching netid from {CURRENT_NETID} to {netid}")
    if radio.change_netid(uart, netid):
        CURRENT_NETID = netid

async def send_msg(msgtype, creator, msgbytes, dest):
    if msgtype != "A":
        switch_netid(get_net_id(dest))
    retval = await send_msg_internal(msgtype, creator, msgbytes, dest)
    if msgtype != "A":
        switch_netid(get_net_id())
    return retval

def ack_time(smid):
    for (rmid, msgbytes, t) in msgs_recd:
        if rmid[0] == "A":
            msg = msgbytes.decode()
            if smid == msg[:MIDLEN]:
                missingids = []
                print(f"Checking for missing IDs in {msg[MIDLEN+1:]}")
                if msg[0] == 'E' and len(msg) > (MIDLEN+1):
                    missingids = [int(i) for i in msg[MIDLEN+1:].split(',')]
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
        if mid[0] == "A":
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

# === Async Receiver for openmv ===
async def radio_read():
    if run_omv:
        buffer = b""
        while True:
            if uart.any():
                buffer = uart.read(1)
                lendata = int.from_bytes(buffer)
                print(f"Lendata to read = {lendata}")
                if lendata > 0:
                    print(lendata)
                    buffer = uart.read(lendata)
                    process_message(buffer)
                    #processed_success = process_message(buffer)
                    #if not processed_success:
                    #    uart.read() # clear buffer.
                    #else:
                    #    time_of_last_radio_receive = time_msec()
            await asyncio.sleep(0.01)
    else:
        buffer = b""
        while True:
            await asyncio.sleep(0.01)
            while uart.in_waiting > 0:
                byte = uart.read(1)
                buffer += byte
                if byte == b'\n':
                    process_message(buffer)
                    buffer = b""

chunk_map = {} # chunk ID to (expected_chunks, [(iter, chunk_data)])

def begin_chunk(msg):
    global RECEIVING_IMAGE
    RECEIVING_IMAGE = True
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
        log(f"ERROR : Not enough bytes {len(msgbytes)} : {msg}")
        return
    cid = msgbytes[0:3].decode()
    print(f"")
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
    creator = mid[1]
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

def parse_header(data):
    if data == None:
        print(f"Weird that data is none")
        return None
    if len(data) < 9:
        return None
    try:
        mid = data[:MIDLEN].decode()
    except Exception as e:
        print(f"ERROR PARSING {data[:MIDLEN]} Error : {e}")
        return
    mst = mid[0]
    creator = mid[1]
    sender = mid[2]
    receiver = mid[3]
    for i in range(MIDLEN):
        if (mid[i] < 'A' or mid[i] > 'Z') and not (i == 3 and mid[i] == "*"):
            return None
    if chr(data[MIDLEN]) != ';':
        return None
    msg = data[MIDLEN+1:]
    return (mid, mst, creator, sender, receiver, msg)

hb_map = {}

def hb_process(mid, msgbytes):
    creator = mid[1]
    if running_as_cc():
        if creator not in hb_map:
            hb_map[creator] = 0
        hb_map[creator] += 1
        print(f"HB Counts = {hb_map}")
        #print(f"Only for debugging : HB msg = {enc.decrypt_rsa(msgbytes, enc.load_rsa_prv())}")
        print(f"Only for debugging : HB msg = {msgbytes.decode()}")
        return
    if len(shortest_path_to_cc) > 0:
        peer_addr = shortest_path_to_cc[0]
        print(f"Propogating H to {peer_addr}")
        asyncio.create_task(send_msg("H", creator, msgbytes, peer_addr))
    else:
        print(f"Can't forward HB because I dont have Spath yet")

def img_process(cid, msg, creator):
    clear_chunkid(cid)
    # TODO save image
    if running_as_cc():
        print(f"Received image of size {len(msg)}")
        img_bytes = msg
        #img_bytes = enc.decrypt_hybrid(msg, enc.load_rsa_prv())
        img = image.Image(320, 240, image.JPEG, buffer=img_bytes)
        print(len(img_bytes))
        fname = f"cc_{creator}_{cid}.jpg"
        print(f"Saving to file {fname}")
        img.save(fname)
    else:
        if len(shortest_path_to_cc) > 0:
            peer_addr = shortest_path_to_cc[0]
            print(f"Propogating H to {peer_addr}")
            send_msg("P", creator, msg, peer_addr)
        else:
            print(f"Can't forward Photo because I dont have Spath yet")

# If N messages seen in the last M minutes.
def scan_process(mid, msg):
    if msg not in seen_neighbours:
        seen_neighbours.append(msg)

def spath_process(mid, msg):
    global shortest_path_to_cc
    if running_as_cc():
        # print(f"Ignoring shortest path since I am cc")
        return
    if len(msg) == 0:
        print(f"Empty spath")
        return
    spath = msg.split(",")
    if my_addr in spath:
        print(f"Cyclic, ignoring {my_addr} already in {spath}")
        return
    if len(shortest_path_to_cc) == 0 or len(shortest_path_to_cc) > len(spath):
        print(f"Updating spath to {spath}")
        shortest_path_to_cc = spath
        if my_addr == "B":
            shortest_path_to_cc = ["A", "Z"]
        elif my_addr == "A":
            shortest_path_to_cc = ["Z"]
        for n in seen_neighbours:
            nmsg = my_addr + "," + ",".join(spath)
            print(f"Propogating spath from {spath} to {nmsg}")
            asyncio.create_task(send_msg("S", mid[1], nmsg.encode(), n))

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
    if receiver != "*" and my_addr != receiver:
        log(f"Skipping message as it is not for me but for {receiver} : {mid}")
        return
    log(f"[RECV {len(data)}] MID:{mid}:{msg} at {time_msec()}")
    msgs_recd.append((mid, msg, time_msec()))
    ackmessage = mid
    if mst == "N":
        scan_process(mid, msg.decode())
    if mst == "S":
        spath_process(mid, msg.decode())
    if mst == "H":
        asyncio.create_task(send_msg("A", my_addr, ackmessage.encode(), sender))
        hb_process(mid, msg)
    if mst == "B":
        asyncio.create_task(send_msg("A", my_addr, ackmessage.encode(), sender))
        begin_chunk(msg.decode())
    elif mst == "I":
        add_chunk(msg)
    elif mst == "E":
        alldone, retval, cid, recompiled, creator = end_chunk(mid, msg.decode())
        if alldone:
            global RECEIVING_IMAGE
            RECEIVING_IMAGE = False
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
    return True

async def send_heartbeat():
    while True:
        if RECEIVING_IMAGE or TRANSFERRING_IMAGE:
            print(f"Not sending HB because image transfer in progress {TRANSFERRING_IMAGE} {RECEIVING_IMAGE}")
            await asyncio.sleep(60)
            continue
        # TODO add last known GPS here also.
        print(f"Shortest path = {shortest_path_to_cc}")
        if len(shortest_path_to_cc) > 0:
            hbmsg = f"{my_addr}:{get_human_ts()}"
            peer_addr = shortest_path_to_cc[0]
            msgbytes = encrypt_if_needed("H", hbmsg.encode())
            await send_msg("H", my_addr, msgbytes, peer_addr)
        else:
            print("Not sending right now")
        await asyncio.sleep(HB_WAIT_SEC)

async def send_scan():
    i = 1
    while True:
        scanmsg = f"{my_addr}"
        await send_msg("N", my_addr, scanmsg.encode(), "*")
        await asyncio.sleep(60) # reduce after setup
        print(f"{my_addr} : Seen neighbours = {seen_neighbours}, Shortest path = {shortest_path_to_cc}, Sent messages = {sent_count}, Received messages = {recv_msg_count}")
        i = i + 1

async def send_spath():
    while True:
        sp = f"{my_addr}"
        for n in seen_neighbours:
            print(f"Sending shortest path to {n}")
            await send_msg("S", my_addr, sp.encode(), n)
            await asyncio.sleep(60)

async def print_summary():
    while True:
        await asyncio.sleep(10)
        print(f"My current NETID is {CURRENT_NETID}")
        print(f"Sent : {len(msgs_sent)} Recd : {len(msgs_recd)} Unacked : {len(msgs_unacked)}")
        #print(msgs_sent)
        #print(msgs_recd)
        #print(msgs_unacked)

async def time_since_last_read():
    while True:
        await asyncio.sleep(10)
        time_since_last = int((time_msec() - time_of_last_radio_receive) / 1000)
        print(f"Checking if radio needs to be rebooted, time since last = {time_since_last}")
        if time_since_last >= HB_WAIT_SEC:
            print(f"Time since last read = {time_since_last}, rebooting radio ...............")
            await asyncio.sleep(5)
            radio.hard_reboot(uart)
            print("Radio rebooted")

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


loranode = None
my_lora_addr = NET_ID_MAP[my_addr]

async def init_lora():
    global loranode
    print(f"Initializing LoRa SX126X module... my lora addr = {my_lora_addr}")
    loranode = sx1262.sx126x(
        uart_num=1,        # UART port number - adjust as needed
        freq=868,          # Frequency in MHz
        addr=my_lora_addr, # Node address
        power=22,          # Transmission power in dBm
        rssi=False,         # Enable RSSI reporting
        air_speed=2400,    # Air data rate
        m0_pin='P6',       # M0 control pin - adjust to your wiring
        m1_pin='P7'        # M1 control pin - adjust to your wiring
    )
    print("LoRa module initialized successfully!")
    print(f"Node address: {loranode.addr}")
    print(f"Frequency: {loranode.start_freq + loranode.offset_freq}.125MHz")

async def lora_radio_read():
    print("In Read Method")
    while True:
        message = loranode.receive()
        if message:
            print(f"In Main, message received = {message}")
        await asyncio.sleep(0.05)

async def lora_send_messages(n):
    global loranode
    if len(shortest_path_to_cc) == 0:
        print(f"Error, no shortest_path_to_cc yet {shortest_path_to_cc}")
        return
    dest = shortest_path_to_cc[0]
    target_addr = NET_ID_MAP[dest]
    print(f"Sending {n} messages to {target_addr}")
    for i in range(n):
        msg = f"Message from {my_addr},{my_lora_addr}, message num = {i}"
        print(f"Sending to {target_addr} : {msg}")
        loranode.send(target_addr, msg)
        await asyncio.sleep(10)

async def main():
    log(f"[INFO] Started device {my_addr} run_omv = {run_omv} my_lora_addr = {my_lora_addr}")
    await init_lora()
    print(shortest_path_to_cc)
    read_task = asyncio.create_task(lora_radio_read())
    send_task = asyncio.create_task(lora_send_messages(100))
    await asyncio.gather(read_task, send_task)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    log("Stopped.")
