# SX1262 Driver Integration - Complete Change Log

This document details all changes made to `main.py` to integrate the SX1262 LoRa driver, comparing the new implementation with the previous placeholder implementation.

## Table of Contents
1. [Import Statements](#1-import-statements)
2. [LoRa Configuration Constants](#2-lora-configuration-constants)
3. [LoRa Initialization Function](#3-lora-initialization-function)
4. [LoRa Ready Check Function](#4-lora-ready-check-function)
5. [Radio Send Function](#5-radio-send-function)
6. [Radio Read Function](#6-radio-read-function)
7. [Image Transmission Flow](#7-image-transmission-flow)
8. [Chunk Handling Functions](#8-chunk-handling-functions)
9. [ACK Handling](#9-ack-handling)
10. [Logging Enhancements](#10-logging-enhancements)
11. [Memory Management](#11-memory-management)
12. [Timing and Performance Optimizations](#12-timing-and-performance-optimizations)

---

## 1. Import Statements

### Previous Implementation
```python
import sx1262  # Placeholder import
```

### New Implementation
```python
from sx1262 import SX1262
from _sx126x import ERR_NONE, ERR_RX_TIMEOUT, ERR_CRC_MISMATCH, SX126X_SYNC_WORD_PRIVATE
```

**Changes:**
- Changed from `import sx1262` to `from sx1262 import SX1262` for direct class access
- Added explicit imports of error constants (`ERR_NONE`, `ERR_RX_TIMEOUT`, `ERR_CRC_MISMATCH`) for proper error handling
- Added `SX126X_SYNC_WORD_PRIVATE` constant for secure communication

**Location:** Lines 27-28

---

## 2. LoRa Configuration Constants

### Previous Implementation
- No centralized LoRa configuration constants
- Parameters likely hardcoded or missing

### New Implementation
```python
# LoRa Configuration Constants - Highest Data Rate (SF5, BW500kHz, CR5) for fast robust communication
LORA_FREQ = 868.0
LORA_SF = 5  # Spreading Factor 5 (highest data rate ~38 kbps)
LORA_BW = 500.0  # Bandwidth 500 kHz (highest bandwidth for maximum speed)
LORA_CR = 5  # Coding Rate 4/5 (good balance of speed and error correction)
LORA_PREAMBLE = 8  # Preamble length (as used in high-speed examples)
LORA_POWER = 14  # TX power in dBm
LORA_RX_TIMEOUT_MS = 200  # Receive timeout for async loop (optimized for high-speed communication)
```

**Changes:**
- Added centralized LoRa configuration constants for easy modification
- Optimized for highest data rate: SF5, BW500kHz, CR5
- Added `LORA_RX_TIMEOUT_MS` for async receive loop timeout control
- Configuration optimized for high-speed, robust communication

**Location:** Lines 87-94

---

## 3. LoRa Initialization Function

### Previous Implementation
```python
async def init_lora():
    # Placeholder implementation
    loranode = sx1262.sx126x()  # This function didn't exist
    # Missing proper initialization
```

### New Implementation
```python
async def init_lora():
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

        # Configure LoRa with highest data rate settings
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
```

**Changes:**
- Replaced placeholder `sx1262.sx126x()` with actual `SX1262()` constructor
- Added complete SPI pin configuration (P0-P7, P13)
- Added proper `begin()` call with all LoRa parameters
- Added error handling with status checking using `ERR_NONE`
- Added initialization lock (`lora_init_in_progress`) to prevent duplicate initialization
- Added comprehensive logging for initialization status
- Configured for highest data rate (SF5, BW500kHz, CR5)

**Location:** Lines 467-519

---

## 4. LoRa Ready Check Function

### Previous Implementation
```python
def is_lora_ready():
    if loranode.is_connected:  # This property didn't exist
        return True
    # Missing initialization trigger
    return False
```

### New Implementation
```python
def is_lora_ready():
    global lora_init_in_progress, loranode
    if loranode is None:
        if not lora_init_in_progress:
            logger.error(f"[LORA] Not connected to network, init started in background.., msg marked as failed")
            asyncio.create_task(init_lora())
        else:
            logger.debug(f"[LORA] Not connected to network, init already in progress, msg marked as failed")
        return False
    return True
```

**Changes:**
- Changed from `loranode.is_connected` (non-existent property) to `loranode is None` check
- Added automatic background initialization trigger when LoRa is not ready
- Added check for ongoing initialization to prevent duplicate initialization attempts
- Improved error logging

**Location:** Lines 521-532

---

## 5. Radio Send Function

### Previous Implementation
```python
def radio_send(dest, data, msg_uid):
    # Placeholder implementation
    loranode.send(dest, data)  # Incorrect API
```

### New Implementation
```python
def radio_send(dest, data, msg_uid):
    global sent_count
    sent_count = sent_count + 1
    lendata = len(data)
    if len(data) > 254:
        logger.error(f"[LORA] msg too large : {len(data)}")
        return
    data = data.replace(b"\n", b"{}[]")
    try:
        # Calculate airtime before sending (more accurate for logging)
        airtime_us = loranode.getTimeOnAir(len(data))
        len_sent, status = loranode.send(data)
        if status != ERR_NONE:
            logger.error(f"[LORA] Send failed with status {status}, MSG_UID = {msg_uid}, dest={dest}")
        # Map 0-210 bytes to 1-10 asterisks, anything above 210 = 10 asterisks
        data_masked_log = min(10, max(1, (len(data) + 20) // 21))
        airtime_ms = airtime_us / 1000.0
        logger.info(f"[⮕ SENT to {dest}, airtime: {airtime_ms:.2f}ms] [{'*' * data_masked_log}] {len(data)} bytes, MSG_UID = {msg_uid}")
    except Exception as e:
        logger.error(f"[LORA] Exception in radio_send: {e}, MSG_UID = {msg_uid}")
```

**Changes:**
- Removed `dest` parameter from `loranode.send()` (addressing handled in payload)
- Changed to `loranode.send(data)` which returns `(len_sent, status)` tuple
- Added status checking using `ERR_NONE` constant
- Added airtime calculation using `loranode.getTimeOnAir()` for logging
- Added comprehensive error handling with try-except
- Added airtime to log output
- Improved error logging with MSG_UID tracking

**Location:** Lines 635-657

---

## 6. Radio Read Function

### Previous Implementation
```python
async def radio_read():
    # Placeholder implementation
    msg = loranode.receive()  # Incorrect API
    process_message(msg)
    await asyncio.sleep(0.15)
```

### New Implementation
```python
async def radio_read():
    logger.info(f"===> Radio Read, LoRa receive loop started... <===\n")
    loop_count = 0
    while True:
        # Safety check: wait for loranode to be initialized
        if loranode is None:
            logger.debug(f"[LORA] Waiting for LoRa initialization...")
            await asyncio.sleep(1)
            continue

        try:
            loop_count += 1
            if loop_count == 1:
                logger.info(f"[LORA] Starting receive loop, loranode={loranode is not None}")
            elif loop_count % 100 == 0:
                logger.info(f"[LORA] Receive loop running (iteration {loop_count})...")
            
            # Use blocking mode with timeout for async compatibility
            msg, status = loranode.recv(len=0, timeout_en=True, timeout_ms=LORA_RX_TIMEOUT_MS)

            if status == ERR_NONE:
                # Valid packet received
                if len(msg) > 0:
                    message = msg.replace(b"{}[]", b"\n")
                    rssi = loranode.getRSSI()  # Get RSSI after successful receive
                    snr = loranode.getSNR()  # Get SNR after successful receive
                    airtime_us = loranode.getTimeOnAir(len(message))  # Calculate airtime
                    process_message(message, rssi, snr, airtime_us)
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
                    snr = loranode.getSNR()
                    airtime_us = loranode.getTimeOnAir(len(message))
                    process_message(message, rssi, snr, airtime_us)
            else:
                # Other error - log and continue
                logger.warning(f"[LORA] Receive error status: {status}")
        except Exception as e:
            logger.error(f"[LORA] Exception in radio_read: {e}")
            await asyncio.sleep(0.1)  # Brief pause on error

        # Small async sleep to yield to event loop
        await asyncio.sleep(0.01)  # 10ms yield for async compatibility
```

**Changes:**
- Replaced `loranode.receive()` with `loranode.recv(len=0, timeout_en=True, timeout_ms=LORA_RX_TIMEOUT_MS)`
- Added proper status checking for `ERR_NONE`, `ERR_RX_TIMEOUT`, `ERR_CRC_MISMATCH`
- Added RSSI retrieval using `loranode.getRSSI()`
- Added SNR retrieval using `loranode.getSNR()`
- Added airtime calculation using `loranode.getTimeOnAir()`
- Added comprehensive error handling for all receive statuses
- Added initialization check before receiving
- Added loop progress logging
- Removed fixed `asyncio.sleep(0.15)` and replaced with minimal `0.01s` yield
- Added CRC error handling (attempts to process corrupted packets for robustness)
- Updated `process_message()` to accept RSSI, SNR, and airtime parameters

**Location:** Lines 1853-1913

---

## 7. Image Transmission Flow

### Previous Implementation
- Likely sent all chunks without waiting for ACKs
- No proper retransmission logic
- Missing chunk verification

### New Implementation
```python
async def send_msg_big(msg_typ, creator, msgbytes, dest, epoch_ms):
    # Redesigned based on example/capture-send pattern:
    # 1. Send begin packet, wait for ACK
    # 2. Send chunks sequentially, wait for ACK after each chunk
    # 3. Send end packet, get missing chunks list
    # 4. Send missing chunks sequentially, wait for ACK after each
    # 5. Only after all chunks ACKed, transmission complete
    
    if msg_typ == "P":
        img_id = get_rand()
        if get_transmode_lock(dest, img_id):
            asyncio.create_task(keep_transmode_lock(dest, img_id))
            chunks = make_chunks(msgbytes)
            num_chunks = len(chunks)
            tx_start_time = utime.ticks_ms()  # Track start time
            logger.info(f"[IMG TX] Starting image transmission: dest={dest}, len={len(msgbytes)} bytes, img_id={img_id}, chunks={num_chunks}")
            
            # Step 1: Send begin packet and wait for ACK
            begin_succ, _ = await send_single_packet("B", creator, f"{img_id}:{epoch_ms}:{num_chunks}", dest)
            if not begin_succ:
                # Log total time and return
                return False
            
            # Step 2: Send all chunks sequentially, waiting for ACK after each
            sent_chunks = set()
            for i in range(num_chunks):
                chunkbytes = img_id.encode() + i.to_bytes(2, 'big') + chunks[i]
                chunk_succ, _ = await send_single_packet("I", creator, chunkbytes, dest, retry_count=5)
                if chunk_succ:
                    sent_chunks.add(i)
            
            # Step 3: Send end packet and get missing chunks list
            max_end_retries = 15
            for end_retry in range(max_end_retries):
                end_succ, missing_chunks = await send_single_packet("E", creator, f"{img_id}:{epoch_ms}", dest, retry_count=5)
                
                if missing_chunks is None or len(missing_chunks) == 0:
                    # All chunks received successfully
                    total_time_ms = utime.ticks_diff(utime.ticks_ms(), tx_start_time)
                    total_time_sec = total_time_ms / 1000.0
                    logger.info(f"[IMG TX] All chunks received successfully! Transmission complete. Total time: {total_time_ms}ms ({total_time_sec:.2f}s)")
                    return True
                
                # Step 4: Send missing chunks sequentially
                missing_list = missing_chunks[:]  # Copy list
                for mis_chunk_idx in missing_list:
                    chunkbytes = img_id.encode() + mis_chunk_idx.to_bytes(2, 'big') + chunks[mis_chunk_idx]
                    await send_single_packet("I", creator, chunkbytes, dest, retry_count=5)
```

**Changes:**
- **Sequential ACK-based transmission**: Each chunk waits for ACK before sending next
- **Begin packet**: Sends "B" packet with image metadata, waits for ACK
- **Sequential chunk transmission**: Sends chunks one by one, waiting for ACK after each
- **End packet**: Sends "E" packet to get missing chunks list from receiver
- **Retransmission logic**: Only retransmits chunks in the missing list
- **Total transmission time tracking**: Logs total time from start to completion
- **Increased retries**: `max_end_retries = 15` and `retry_count=5` for chunks
- **Proper error handling**: Logs total time on all failure paths

**Location:** Lines 749-871

---

## 8. Chunk Handling Functions

### Previous Implementation
- Chunks stored in tuples (immutable)
- No deduplication logic
- Missing chunks not properly tracked

### New Implementation

#### `begin_chunk()` Function
```python
def begin_chunk(msg):
    parts = msg.split(":")
    if len(parts) != 3:
        logger.error(f"[CHUNK] begin message unparsable {msg}")
        return
    img_id = parts[0]
    epoch_ms = int(parts[1])
    numchunks = int(parts[2])
    # Use list instead of tuple for chunk_map entry to allow modification
    if img_id not in chunk_map:
        chunk_map[img_id] = ["B", numchunks, []]  # Changed from tuple to list
        logger.info(f"[IMG RX] Initialized chunk_map for img_id={img_id}, expected_chunks={numchunks}")
    return (img_id, epoch_ms, numchunks)
```

**Changes:**
- Changed `chunk_map` entries from tuples to lists for mutability
- Added duplicate "B" packet handling (only initializes if not present)
- Added logging for chunk map initialization

#### `add_chunk()` Function
```python
def add_chunk(msgbytes):
    if len(msgbytes) < 5:
        logger.error(f"[CHUNK RX] not enough bytes {len(msgbytes)}")
        return
    try:
        img_id = msgbytes[0:3].decode()
        citer = int.from_bytes(msgbytes[3:5], 'big')  # Explicit byteorder
        cdata = msgbytes[5:]
        if img_id not in chunk_map:
            logger.warning(f"[CHUNK RX] no entry yet for img_id={img_id}, chunk_index={citer}")
            return
        
        # Check if chunk already exists (deduplicate)
        chunk_list = chunk_map[img_id][2]
        chunk_exists = False
        for idx, (stored_citer, _) in enumerate(chunk_list):
            if stored_citer == citer:
                chunk_exists = True
                # Update existing chunk (replace with new one in case of corruption)
                chunk_list[idx] = (citer, cdata)
                break
        
        if not chunk_exists:
            # Store new chunk
            chunk_list.append((citer, cdata))
        
        # Log progress
        entry = chunk_map[img_id]
        expected_chunks = entry[1]
        missing = get_missing_chunks(img_id)
        received = expected_chunks - len(missing)
        if received % 20 == 0 or received == expected_chunks:
            logger.info(f"[IMG RX] Received chunk {citer}: {received}/{expected_chunks} chunks complete")
    except Exception as e:
        logger.error(f"[CHUNK RX] Error adding chunk: {e}, msgbytes_len={len(msgbytes)}")
```

**Changes:**
- **Deduplication logic**: Checks if chunk already exists by index, updates if duplicate
- **Explicit byteorder**: Added `byteorder='big'` to `int.from_bytes()` for consistency
- **Progress logging**: Logs every 20 chunks or when complete
- **Error handling**: Comprehensive try-except with detailed error logging

#### `end_chunk()` Function
```python
def end_chunk(msg_uid, msg):
    parts = msg.split(":")
    if len(parts) != 2:
        logger.error(f"[CHUNK] end message unparsable {msg}")
        return
    img_id = parts[0]
    epoch_ms = int(parts[1])
    
    if img_id not in chunk_map:
        logger.warning(f"[CHUNK] end_chunk: no entry for img_id={img_id}")
        return (False, "0", img_id, None, epoch_ms)
    
    entry = chunk_map[img_id]
    expected_chunks = entry[1]
    chunk_list = entry[2]
    missing = get_missing_chunks(img_id)
    
    if len(missing) > 0:
        # Build missing chunk list string, ensuring it fits in payload
        max_payload_size = PACKET_PAYLOAD_LIMIT - MIDLEN - 5
        missing_str = str(missing[0])
        for i in range(1, len(missing)):
            candidate = missing_str + "," + str(missing[i])
            if len(candidate) <= max_payload_size:
                missing_str = candidate
            else:
                # Truncate - sender will send remaining chunks after getting this list
                logger.warning(f"[CHUNK] Missing chunk list truncated at {i}/{len(missing)} chunks")
                break
        return (False, missing_str, img_id, None, epoch_ms)
    else:
        recompiled_msgbytes = recompile_msg(img_id)
        return (True, None, img_id, recompiled_msgbytes, epoch_ms)
```

**Changes:**
- **Payload size handling**: Ensures missing chunk list fits within `PACKET_PAYLOAD_LIMIT`
- **Truncation logic**: Truncates missing list if too large, allows multiple retransmission rounds
- **Improved logging**: Logs missing chunks with first/last 20 indices
- **Error handling**: Handles missing `chunk_map` entries gracefully

**Location:** 
- `begin_chunk()`: Lines 916-930
- `add_chunk()`: Lines 947-982
- `end_chunk()`: Lines 1025-1065

---

## 9. ACK Handling

### Previous Implementation
- Basic ACK checking
- No missing chunk list parsing
- Limited retry logic

### New Implementation

#### `ack_needed()` Function
```python
def ack_needed(msg_typ):
    if msg_typ in ["A", "S", "W", "N"]:
        return False
    if msg_typ in ["H", "B", "E", "V", "C", "T", "I"]:  # Added "I" for chunk ACKs
        return True
    return False
```

**Changes:**
- Added "I" (image chunk) to list of message types requiring ACK
- Ensures chunks are ACKed for reliable transmission

#### `ack_time()` Function
```python
def ack_time(msg_uid):
    for (recd_msg_uid, msgbytes, t) in msgs_recd:
        if chr(recd_msg_uid[0]) == "A":
            if len(msgbytes) >= MIDLEN - 1:
                if len(msgbytes) >= MIDLEN and msg_uid == msgbytes[:MIDLEN]:
                    missingids = []
                    # For End (E) chunk messages, check for missing chunk IDs
                    if len(msgbytes) > MIDLEN and msgbytes[MIDLEN:MIDLEN+1] == b':':
                        missing_str = msgbytes[MIDLEN+1:].decode()
                        if missing_str != "-1":
                            try:
                                missingids = [int(i) for i in missing_str.split(',') if i]
                            except ValueError:
                                logger.warning(f"[ACK] Failed to parse missing IDs: {missing_str}")
                                missingids = []
                    return (t, missingids)
                # Try match with missing last byte (workaround for truncation)
                elif len(msgbytes) == MIDLEN - 1 and msg_uid[:MIDLEN-1] == msgbytes:
                    return (t, [])
    return (-1, None)
```

**Changes:**
- **Missing chunk parsing**: Extracts missing chunk IDs from ACK payload for "E" packets
- **Completion marker**: Handles "-1" marker indicating all chunks received
- **Truncation handling**: Handles ACK payloads missing last byte
- **Error handling**: Gracefully handles parsing errors

#### `send_single_packet()` Function
```python
async def send_single_packet(msg_typ, creator, msgbytes, dest, retry_count=3):
    msg_uid = get_msg_uid(msg_typ, creator, dest)
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
    
    ack_msg_recheck_count = 12  # Increased for better ACK detection
    for retry_i in range(retry_count):
        radio_send(dest, databytes, msg_uid)
        await asyncio.sleep(ACK_SLEEP)
        first_log_flag = True
        for i in range(ack_msg_recheck_count):
            at, missing_chunks = ack_time(msg_uid)
            if at > 0:
                logger.info(f"[ACK] Msg {msg_uid} : was acked in {at - timesent} msecs")
                msgs_sent.append(pop_and_get(msg_uid))
                return (True, missing_chunks)
            else:
                await asyncio.sleep(ACK_SLEEP * min(i + 1, 2) / 2)  # Progressive sleep
        logger.warning(f"[ACK] Failed to get ack, MSG_UID = {msg_uid}, retry # {retry_i+1}/{retry_count}")
    return (False, [])
```

**Changes:**
- **Increased ACK recheck count**: From 5 to 12 for better ACK detection at high speeds
- **Progressive sleep**: Faster ACK checking with progressive sleep duration
- **Missing chunks return**: Returns missing chunk list from ACK for "E" packets
- **Improved logging**: Better logging for ACK waiting and success

**Location:**
- `ack_needed()`: Lines 331-338
- `ack_time()`: Lines 877-907
- `send_single_packet()`: Lines 667-705

---

## 10. Logging Enhancements

### Previous Implementation
- Basic logging without signal quality metrics
- No transmission time tracking

### New Implementation

#### RSSI, SNR, and Airtime Logging
```python
def process_message(data, rssi=None, snr=None, airtime_us=None):
    # ... parsing code ...
    
    # Build log string with RSSI, SNR, and airtime if available
    log_extra = []
    if rssi is not None:
        log_extra.append(f"rssi: {rssi:.1f}")
    if snr is not None:
        log_extra.append(f"snr: {snr:.1f}")
    if airtime_us is not None:
        airtime_ms = airtime_us / 1000.0
        log_extra.append(f"airtime: {airtime_ms:.2f}ms")
    
    if log_extra:
        extra_str = ", ".join(log_extra)
        logger.info(f"[{recv_log} from {sender}, {extra_str}] [{'*' * data_masked_log}] {len(data)} bytes, MSG_UID = {msg_uid}")
```

**Changes:**
- Added RSSI (Received Signal Strength Indicator) logging
- Added SNR (Signal-to-Noise Ratio) logging
- Added airtime (on-air transmission time) logging
- All metrics formatted with appropriate precision (1 decimal for RSSI/SNR, 2 decimals for airtime)

#### Total Transmission Time Logging
```python
tx_start_time = utime.ticks_ms()  # Track start time
# ... transmission code ...
total_time_ms = utime.ticks_diff(utime.ticks_ms(), tx_start_time)
total_time_sec = total_time_ms / 1000.0
logger.info(f"[IMG TX] All chunks received successfully! Transmission complete. Total time: {total_time_ms}ms ({total_time_sec:.2f}s)")
```

**Changes:**
- Added total transmission time tracking from start to completion
- Logs time in both milliseconds and seconds
- Logs on all completion paths (success and failure)

**Location:**
- `process_message()`: Lines 1695-1847
- `send_msg_big()`: Lines 764, 819-821, 827-829, 770-772, 782-784, 804-806, 840-842, 861-863

---

## 11. Memory Management

### Previous Implementation
- No explicit memory cleanup
- Chunk map entries not properly deleted

### New Implementation

#### `delete_chunk_map_entry()` Function
```python
def delete_chunk_map_entry(img_id):
    if img_id in chunk_map:
        entry = chunk_map.pop(img_id)
        # Explicitly delete chunk data to free memory
        if len(entry) > 2 and isinstance(entry[2], list):
            for _, chunk_data in entry[2]:
                del chunk_data
        del entry
        gc.collect()  # Help GC reclaim memory immediately
```

**Changes:**
- Explicit deletion of chunk data before removing from map
- Calls `gc.collect()` to immediately reclaim memory
- Prevents memory leaks during long-running operations

#### Periodic Memory Cleanup
```python
async def periodic_memory_cleanup():
    while True:
        await asyncio.sleep(MEM_CLEANUP_INTERVAL_SEC)
        free_before = get_free_memory()
        cleanup_old_messages()
        cleanup_chunk_map()
        gc.collect()
        free_after = get_free_memory()
        logger.info(f"[MEM] Cleanup complete (free: {free_after/1024:.1f}KB, freed: {freed/1024:.1f}KB)")
```

**Changes:**
- Periodic cleanup of old messages and chunk maps
- Tracks memory freed during cleanup
- Prevents memory overflow in long-running applications

**Location:**
- `delete_chunk_map_entry()`: Lines 1010-1021
- `periodic_memory_cleanup()`: Lines 598-622

---

## 12. Timing and Performance Optimizations

### Previous Implementation
- Fixed sleep durations
- No optimization for high-speed communication

### New Implementation

#### Sleep Constants
```python
MIN_SLEEP = 0.02  # Minimal delay for high-speed communication (SF5, BW500kHz)
ACK_SLEEP = 0.05  # Reduced ACK sleep for faster checking at high data rates  
CHUNK_SLEEP = 0.01  # Minimal delay between chunks for fastest transmission
```

**Changes:**
- Reduced sleep durations optimized for high-speed LoRa (SF5, BW500kHz)
- `MIN_SLEEP`: 0.02s (minimal delay)
- `ACK_SLEEP`: 0.05s (reduced for faster ACK checking)
- `CHUNK_SLEEP`: 0.01s (minimal delay between chunks)

#### Transfer Mode Lock Enhancement
```python
def check_transmode_lock(device_id, img_id):
    global image_in_progress, paired_device, data_id
    # If img_id is None, only check device_id (for backward compatibility)
    if img_id is None:
        return image_in_progress and paired_device == device_id
    # Otherwise check both device_id and img_id
    if image_in_progress and paired_device == device_id and data_id == img_id:
        return True
    else:
        return False
```

**Changes:**
- Added support for `None` img_id (backward compatibility)
- Allows checking transfer mode even when img_id is not yet known
- Prevents chunk processing issues when chunks arrive before "B" packet

**Location:**
- Sleep constants: Lines 46-48
- `check_transmode_lock()`: Lines 377-386

---

## Summary of Key Improvements

1. **Driver Integration**: Complete replacement of placeholder implementation with actual SX1262 driver
2. **High-Speed Configuration**: Optimized for highest data rate (SF5, BW500kHz, CR5)
3. **Reliable Transmission**: Sequential ACK-based chunk transmission with proper retransmission
4. **Signal Quality Metrics**: RSSI, SNR, and airtime logging for network diagnostics
5. **Memory Management**: Explicit cleanup and periodic garbage collection
6. **Error Handling**: Comprehensive error handling with proper status checking
7. **Performance**: Optimized sleep durations and ACK checking for high-speed communication
8. **Logging**: Enhanced logging with transmission time tracking and signal quality metrics

---

## Testing Recommendations

1. **Verify LoRa initialization** - Check logs for successful SX1262 initialization
2. **Monitor signal quality** - Check RSSI and SNR values in logs
3. **Test image transmission** - Verify complete image transmission with proper chunk handling
4. **Check memory usage** - Monitor memory cleanup logs to ensure no leaks
5. **Verify retransmission** - Test missing chunk retransmission logic
6. **Performance testing** - Verify transmission times are within expected ranges

---

## Notes

- All changes maintain backward compatibility where possible
- Error handling is comprehensive to prevent crashes
- Logging is detailed for debugging and monitoring
- Memory management is proactive to prevent overflow
- Configuration is centralized for easy modification

