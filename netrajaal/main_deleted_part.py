from logger import logger
import uasyncio as asyncio

async def log_status(): # Not in use
    # Input: None; Output: None (logs transmission statistics)
    await asyncio.sleep(1)
    logger.info("[STATUS] $$$$ %%%%% ###### Printing status ###### $$$$$$ %%%%%%%%")
    logger.info(f"[STATUS] So far sent {len(msgs_sent)} messages and received {len(msgs_recd)} messages")
    ackts = []
    msgs_not_acked = []
    for mid, msg, t in msgs_sent:
        if mid[0] == b"A":
            continue
        #logger.info("Getting ackt for " + s + "which was sent at " + str(t))
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
        logger.info(f"[ACK Times] 50% = {mid:.2f}s, 90% = {p90:.2f}s")
        logger.info(f"[STATUS] So far {len(msgs_not_acked)} messsages havent been acked")
        logger.info(f"[STATUS] {msgs_not_acked}")



def fake_listen_http():
    # Input: None; Output: tuple(command: str, dest: int, cpath: list[int]) for simulated commands
    command = "SENDHB"
    dest = 222
    cpath = [219,222]
    return (command, dest, cpath)


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
            logger.info(f"[STATUS] Skipping print summary because image in progress")
            await asyncio.sleep(200)
            continue
        logger.info(f"[CMD] Randomly sending a command {command} to {dest}, via {cpath}")
        if dest == my_addr:
            execute_command(command)
            continue
        next_dest = get_next_on_path(cpath)
        if next_dest is not None:
            logger.info(f"[CMD] Propogating command to {next_dest}")
            cpathstr = ",".join(str(x) for x in cpath)
            command = f"{dest};{cpathstr};{command}"
            await send_msg("C", my_addr, command.encode(), next_dest)
        else:
            logger.info(f"[CMD] Next dest seems to be None")
            
            
            
            

# ============================================================================
# PIR SENSOR DETECTION: POLLING-BASED
# ============================================================================
# This is the previous implementation using software polling

# ADVANTAGES of polling:
#   - Simpler code (no interrupt handlers)
#   - Good for slow-changing signals

# DISADVANTAGES of polling:
#   - Wastes CPU cycles (wakes every 5 seconds even with no motion)
#   - Delayed response (up to 5 seconds delay)
#   - Higher power consumption (constant wake-ups)
#   - Can miss brief motions between polls

import sensor
import random
images_to_send = []
PHOTO_TAKING_DELAY = 600
MY_IMAGE_DIR = "/sdcard/myimages"
def get_rand():
    # Input: None; Output: str random 3-letter uppercase identifier
    rstr = ""
    for i in range(3):
        rstr += chr(65+random.randint(0,25))
    return rstr

async def person_detection_loop():
    """Previous polling-based implementation"""
    # Input: None; Output: None (runs continuous detection, updates counters and queue)
    global person_image_count, total_image_count

    while True:
        # Poll every 5 seconds - wastes CPU even when no motion
        await asyncio.sleep(5)

        global image_in_progress
        if image_in_progress:
            logger.info(f"Skipping DETECTION because image in progress")
            await asyncio.sleep(20)
            continue

        # Software polling: Read PIR pin value (inefficient)
        # This actively checks the pin every 5 seconds
        # person_detected = detector.check_person()  # Calls PIR_PIN.value()

        # For testing without actual PIR: use if True instead
        # if True:
        if True:
            img = None
            try:
                img = sensor.snapshot()
                person_image_count += 1
                total_image_count += 1
                raw_path = f"{MY_IMAGE_DIR}/raw_{get_rand()}.jpg"
                logger.info(f"Saving image to {raw_path} : imbytesize = {len(img.bytearray())}...")
                img.save(raw_path)
                # Limit queue size to prevent memory overflow
                if len(images_to_send) >= MAX_IMAGES_TO_SEND:
                    # Remove oldest entry
                    oldest = images_to_send.pop(0)
                    logger.info(f"Queue full, removing oldest image: {oldest}")
                images_to_send.append(raw_path)
                logger.info(f"Saved image: {raw_path}")
            except Exception as e:
                logger.error(f"Unexpected error in image taking and saving: {e}")
            finally:
                # Explicitly clean up image object
                if img is not None:
                    del img
                    gc.collect()  # Help GC reclaim memory immediately

        await asyncio.sleep(PHOTO_TAKING_DELAY)
        logger.info(f"Person detected Image count: {person_image_count}")
        
        
# asyncio.create_task(listen_commands_from_cloud())


    

# # ---------------------------------------------------------------------------
# # Command Execution and Routing
# # ---------------------------------------------------------------------------

# def get_next_on_path(cpath):
#     # Input: cpath: list of str/int path nodes; Output: int or None next hop for this device
#     for i in range(len(cpath) - 1):
#         n = cpath[i]
#         if n == my_addr:
#             return cpath[i+1]
#     return None

# def execute_command(command):
#     # Input: command: str command identifier; Output: None (performs device-specific action)
#     logger.info(f"[CMD] Gonna execute_command {command} on {my_addr}")
#     if command == "SENDHB":
#         asyncio.create_task(send_heartbeat())
#     elif command == "SENDIMG":
#         take_image_and_send_now()
#     elif command == "RESET":
#         logger.info(f"Resetting maching")
#         machine.reset()

# async def command_process(msg_uid, msg):
#     # Input: msg_uid: bytes, msg: bytes command payload; Output: None (executes or forwards command)
#     try:
#         msgstr = msg.decode()
#     except Exception as e:
#         logger.error(f"[CMD] could not decode {msg} : {e}")
#     parts = msgstr.split(";")
#     if len(parts) != 3:
#         logger.error(f"[CMD] error in parsing msgstr, got {len(parts)} parts")
#     dest = int(parts[0])
#     cpath = parts[1].split(",")
#     command = parts[2]
#     if dest == my_addr:
#         execute_command(command)
#         return
#     next_dest = get_next_on_path(cpath)
#     if next_dest is not None:
#         logger.info(f"[CMD] Propogating command to {next_dest}")
#         await send_msg("C", my_addr, msgstr.encode(), next_dest)
#     else:
#         logger.info(f"[CMD] Next dest seems None for {msg}")


# def take_image_and_send_now():
#     # Input: None; Output: None (captures immediate snapshot and schedules send)
#     img = sensor.snapshot()
#     asyncio.create_task(send_img_to_nxt_dst(img.to_jpeg().bytearray()))
    

# elif msg_typ == "C":
#     asyncio.create_task(command_process(msg_uid, msg))





# ===== DELETE 12 dec =====
# removed image saving part at CC
# async def img_process(img_id, msg, creator, sender):
#     # Input: img_id: str, msg: bytes (possibly encrypted image), creator: int, sender: int; Output: None (stores or forwards image)
#     clear_chunkid(img_id)
#     if running_as_cc():
#         logger.info(f"[IMG] Received image of size {len(msg)}")
#         # ----- TODO REMOVE THIS IS FOR DEBUGGING ONLY -------
#         img_bytes = None
#         img = None
#         try:
#             # if ENCRYPTION_ENABLED:
#             #     img_bytes = enc.decrypt_hybrid(msg, encnode.get_prv_key(creator))
#             # else:
#             #     img_bytes = msg
#             # img = image.Image(320, 240, image.JPEG, buffer=img_bytes)
#             # fname = f"{NET_IMAGE_DIR}/cc_{creator}_{img_id}.jpg"
#             # logger.info(f"[IMG] Saving to file {fname}, img_size: {len(img_bytes)} bytes")
#             # img.save(fname)
            
#             # images_saved_at_cc.append(fname)
#             # if len(images_saved_at_cc) > MAX_IMAGES_SAVED_AT_CC: # Limit list size
#             #     images_saved_at_cc.pop(0)
#             # ------------------------------------------------------
#             asyncio.create_task(upload_image(creator, msg)) # TODO will be replaced by upload_payload_to_server later
#         finally:
#             # Explicitly clean up image objects
#             if img_bytes is not None:
#                 del img_bytes
#             if img is not None:
#                 del img
#             # Help GC reclaim memory
#             gc.collect()


# def cleanup_cc_images_list():
#     """Clean up the images_saved_at_cc list if too large"""
#     global images_saved_at_cc
#     if len(images_saved_at_cc) > MAX_IMAGES_SAVED_AT_CC:
#         # Keep only the most recent entries
#         images_saved_at_cc = images_saved_at_cc[-MAX_IMAGES_SAVED_AT_CC:]
#         logger.info(f"[MEM] Trimmed images_saved_at_cc to {MAX_IMAGES_SAVED_AT_CC} entries")
        
        

# # Clean up CC images list
# if running_as_cc():
#     cleanup_cc_images_list()
