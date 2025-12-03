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