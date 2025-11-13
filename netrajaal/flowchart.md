# Netrajaal System Flowchart and Process Documentation

## System Overview

The Netrajaal system is a mesh network of IoT devices that perform person detection, image capture, and wireless communication. The system consists of:
- **Command Center (CC)**: Node 219 - Central hub with cellular connectivity
- **Field Nodes**: Nodes 221, 222, 223, 225 - Edge devices with sensors

---

## Main Process Flow

### 1. System Initialization (`main()`)

```
START
  ├─> Device ID Detection (from unique_id)
  │   ├─> Set my_addr (219, 221, 222, 223, or 225)
  │   └─> Set shortest_path_to_cc (if not CC)
  │
  ├─> File System Setup
  │   ├─> Check SD card availability
  │   ├─> Set FS_ROOT (/sdcard or /flash)
  │   ├─> Create IMAGE_DIR (/ccimages for CC, /images for nodes)
  │   └─> Set LOG_FILE_PATH
  │
  ├─> Encryption Setup
  │   └─> Initialize EncNode with public key from {my_addr}.pub
  │
  ├─> Sensor Initialization
  │   ├─> sensor.reset()
  │   ├─> sensor.set_pixformat(RGB565)
  │   ├─> sensor.set_framesize(HD)
  │   └─> sensor.skip_frames(2000)
  │
  ├─> LoRa Initialization
  │   └─> init_lora()
  │       ├─> Create sx126x instance
  │       ├─> Configure UART, frequency, address, power
  │       └─> Set M0/M1 pins for config/normal mode
  │
  ├─> Start Async Tasks
  │   ├─> radio_read() - Message receiver
  │   ├─> print_summary_and_flush_logs() - Logging
  │   ├─> validate_and_remove_neighbours() - Network maintenance
  │   │
  │   └─> IF Command Center (219):
  │       ├─> init_sim() - Initialize cellular
  │       ├─> send_scan() - Network discovery
  │       └─> send_spath() - Broadcast shortest paths
  │   │
  │   └─> IF Field Node:
  │       ├─> send_scan() - Network discovery
  │       ├─> keep_sending_heartbeat() - Status updates
  │       ├─> person_detection_loop() - Person detection
  │       └─> image_sending_loop() - Image transmission
  │
  └─> Main Loop (24*7 hours)
      └─> Sleep 3600 seconds per iteration
```

---

## Core Modules and Functions

### 2. Person Detection Module (`detect.py`)

#### Detector Class

```
Detector.__init__()
  └─> Initialize (model loading commented out)

Detector.check_thermal_body()
  ├─> Read PIR_PIN.value()
  ├─> IF thermal detected:
  │   ├─> turn_ON_IR_emitter()
  │   └─> Return True
  └─> ELSE:
      ├─> turn_OFF_IR_emitter()
      └─> Return False

Detector.check_person()
  └─> Return check_thermal_body()
```

#### IR Emitter Control

```
turn_ON_IR_emitter()
  ├─> IF not ir_emitter_active:
  │   ├─> ir_emitter.on()
  │   ├─> Set ir_emitter_active = True
  │   └─> Sleep IR_WARMUP_TIME (100ms)
  └─> ELSE: Do nothing

turn_OFF_IR_emitter()
  ├─> IF ir_emitter_active:
  │   ├─> ir_emitter.off()
  │   └─> Set ir_emitter_active = False
  └─> ELSE: Do nothing
```

#### Person Detection Loop (`person_detection_loop()`)

```
WHILE True:
  ├─> Sleep 5 seconds
  ├─> IF image_in_progress:
  │   ├─> Skip detection
  │   └─> Sleep 20 seconds
  │
  ├─> Increment total_image_count
  ├─> Capture image: sensor.snapshot()
  ├─> detector.check_person()
  │
  ├─> IF person_detected:
  │   ├─> Increment person_image_count
  │   ├─> Generate random filename
  │   ├─> Save image to IMAGE_DIR/raw_{random}.jpg
  │   └─> Append to images_to_send queue
  │
  └─> Sleep PHOTO_TAKING_DELAY (1 second)
```

---

### 3. Encryption Module (`enc.py`)

#### EncNode Class

```
EncNode.__init__(my_addr)
  ├─> Load public key from {my_addr}.pub file
  ├─> Initialize PublicKey(n_pub, e=65537)
  └─> Initialize PrivKeyRepo for private keys

EncNode.get_pub_key()
  └─> Return public key

EncNode.get_prv_key_self()
  └─> Return private key for my_addr

EncNode.get_prv_key(othernode)
  └─> Return private key for othernode
```

#### Encryption Functions

```
encrypt_rsa(msgstr, public_key)
  └─> Encrypt message (max 117 bytes) using RSA
      └─> Return encrypted bytes

decrypt_rsa(msgstr, private_key)
  └─> Decrypt RSA-encrypted message
      └─> Return decrypted bytes

encrypt_aes(msg, aes_key, iv)
  ├─> Takes iv, a random IV (16 bytes)
  ├─> Create AES cipher (CBC mode)
  ├─> Pad message to 16-byte boundary
  └─> Return encrypted_msg

decrypt_aes(encrypted_msg, iv, aes_key)
  ├─> Create AES cipher (CBC mode)
  ├─> Decrypt message
  └─> Unpad and return decrypted message

encrypt_hybrid(msg, public_key)
  ├─> Generate random AES key (32 bytes)
  ├─> Encrypt message with AES
  ├─> Encrypt AES key with RSA
  ├─> Encrypt IV with RSA
  └─> Return: aes_key_rsa + iv_rsa + msg_aes

decrypt_hybrid(msg, private_key)
  ├─> Decrypt AES key (first 128 bytes)
  ├─> Decrypt IV (next 128 bytes)
  ├─> Decrypt message with AES
  └─> Return decrypted message
```

#### Message Encryption (`encrypt_if_needed()`)

```
encrypt_if_needed(mst, msg)
  ├─> IF ENCRYPTION_ENABLED is False:
  │   └─> Return msg as-is
  │
  ├─> IF message type is "H" (Heartbeat):
  │   ├─> IF len(msg) > 117 bytes:
  │   │   └─> Return msg as-is (too large for RSA)
  │   └─> ELSE:
  │       └─> Return encrypt_rsa(msg, encnode.get_pub_key())
  │
  ├─> IF message type is "P" (Photo):
  │   └─> Return encrypt_hybrid(msg, encnode.get_pub_key())
  │
  └─> ELSE:
      └─> Return msg as-is
```

---

### 4. LoRa Communication Module (`sx1262.py`)

#### sx126x Class Initialization

```
sx126x.__init__(uart_num, freq, addr, power, rssi, air_speed, ...)
  ├─> Initialize GPIO pins (M0, M1)
  ├─> Set M0=LOW, M1=HIGH (configuration mode)
  ├─> Initialize UART at 9600 baud
  ├─> Call set() to configure module
  ├─> Reopen UART at target baud rate (115200)
  └─> Set M0=LOW, M1=LOW (normal mode)
```

#### LoRa Configuration (`set()`)

```
set(freq, addr, power, rssi, air_speed, ...)
  ├─> Enter configuration mode (M0=LOW, M1=HIGH)
  ├─> Calculate frequency offset
  ├─> Build configuration register array
  ├─> Send configuration (retry up to 3 times)
  ├─> Wait for 0xC1 response (success)
  └─> Exit configuration mode (M0=LOW, M1=LOW)
```

#### LoRa Send/Receive

```
send(target_addr, message)
  ├─> Format message: [target_high][target_low][target_freq][own_high][own_low][own_freq][message]\n
  ├─> Write to UART
  └─> Sleep 150ms

receive()
  ├─> IF data available on UART:
  │   ├─> Sleep 150ms
  │   ├─> Read line from UART
  │   ├─> Extract message payload (skip first 6 bytes)
  │   └─> Return message
  └─> ELSE:
      └─> Return None
```

---

### 5. Message Processing System

#### Message Header Format

```
Message ID Format: TypeSourceDestRRRandom
- Type: 1 byte (H, A, B, E, C, I, S, N, V, P)
- Source: 1 byte (creator address)
- Dest: 1 byte (receiver address, or '*' for broadcast)
- RR: Random 3-character string
- Separator: ';'
- Payload: Variable length
```

#### Message Types

- **H**: Heartbeat - Status updates from nodes
- **A**: Acknowledgment - ACK for received messages
- **B**: Begin - Start of chunked message
- **E**: End - End of chunked message
- **C**: Chunk - Data chunk for large messages
- **I**: Image - Image data (chunked)
- **S**: Shortest Path - Network routing information
- **N**: Neighbor Scan - Network discovery
- **V**: Validate - Neighbor validation
- **P**: Photo - Image transmission

#### Message Parsing (`parse_header()`)

```
parse_header(data)
  ├─> IF len(data) < 9:
  │   └─> Return None
  │
  ├─> Extract message ID (first MIDLEN bytes)
  ├─> Parse message type (first byte)
  ├─> Parse creator (second byte)
  ├─> Parse sender (third byte)
  ├─> Parse receiver (fourth byte, '*' = -1)
  ├─> Verify separator ';'
  ├─> Extract payload (after separator)
  └─> Return (mid, mst, creator, sender, receiver, msg)
```

#### Message Sending (`send_msg()`)

```
send_msg(msgtype, creator, msgbytes, dest)
  │
  ├─> IF len(msgbytes) < FRAME_SIZE (195 bytes):
  │   └─> send_single_msg() - Send directly
  │
  └─> ELSE: - Chunked transmission
      ├─> Generate random image ID
      ├─> Split message into chunks (200 bytes each)
      ├─> Send "B" (Begin) message with metadata
      ├─> FOR each chunk:
      │   ├─> Acquire image lock
      │   ├─> Send "I" (Chunk) message
      │   └─> Sleep CHUNK_SLEEP
      │
      ├─> Send "E" (End) message
      ├─> Wait for ACK with missing chunks list
      ├─> IF missing chunks:
      │   ├─> Retry up to 50 times
      │   └─> Resend missing chunks
      └─> Return success status
```

#### Single Message Send (`send_single_msg()`)

```
send_single_msg(msgtype, creator, msgbytes, dest)
  ├─> Generate message ID
  ├─> Build message: mid + ";" + msgbytes
  ├─> IF ack_needed(msgtype):
  │   ├─> Add to msgs_unacked queue
  │   ├─> FOR retry in range(3):
  │   │   ├─> radio_send()
  │   │   ├─> Sleep ACK_SLEEP
  │   │   ├─> FOR wait in range(8):
  │   │   │   ├─> Check for ACK
  │   │   │   ├─> IF ACK received:
  │   │   │   │   ├─> Remove from msgs_unacked
  │   │   │   │   └─> Return (True, missing_chunks)
  │   │   │   └─> Sleep progressively longer
  │   │   └─> Retry if no ACK
  │   └─> Return (False, [])
  │
  └─> ELSE:
      ├─> radio_send()
      ├─> Add to msgs_sent
      └─> Return (True, [])
```

#### Message Reception (`process_message()`)

```
process_message(data)
  ├─> Parse header
  ├─> IF random flakiness test fails:
  │   └─> Drop message
  │
  ├─> Update recv_msg_count
  ├─> IF receiver != -1 and receiver != my_addr:
  │   └─> Ignore message (not for us)
  │
  ├─> Add to msgs_recd
  │
  └─> Route by message type:
      ├─> "N" (Neighbor Scan):
      │   └─> scan_process() - Add to seen_neighbours
      │
      ├─> "S" (Shortest Path):
      │   └─> spath_process() - Update routing table
      │
      ├─> "H" (Heartbeat):
      │   ├─> hb_process() - Process heartbeat
      │   └─> Send ACK
      │
      ├─> "B" (Begin Chunk):
      │   ├─> Acquire image lock
      │   ├─> begin_chunk() - Initialize chunk map
      │   └─> Send ACK
      │
      ├─> "I" (Chunk):
      │   └─> add_chunk() - Store chunk data
      │
      ├─> "E" (End Chunk):
      │   ├─> end_chunk() - Check for missing chunks
      │   ├─> IF all chunks received:
      │   │   ├─> Release image lock
      │   │   ├─> recompile_msg() - Reconstruct message
      │   │   ├─> Send ACK with "-1" (success)
      │   │   └─> img_process() - Process image
      │   └─> ELSE:
      │       └─> Send ACK with missing chunk list
      │
      ├─> "V" (Validate):
      │   └─> Send ACK
      │
      └─> "C" (Command):
          └─> command_process() - Execute command
```

---

### 6. Network Discovery and Routing

#### Neighbor Scanning (`send_scan()`)

```
send_scan()
  WHILE True:
    ├─> IF image_in_progress:
    │   └─> Skip and sleep 200 seconds
    │
    ├─> Create scan message: my_addr.to_bytes()
    ├─> Send "N" message to broadcast (65535)
    │
    ├─> IF iteration < DISCOVERY_COUNT (100):
    │   └─> Sleep SCAN_WAIT (30 seconds)
    └─> ELSE:
        └─> Sleep SCAN_WAIT_2 (1200 seconds) + random(1-120)
```

#### Shortest Path Broadcasting (`send_spath()`)

```
send_spath()
  WHILE True:
    ├─> IF image_in_progress:
    │   └─> Skip and sleep 200 seconds
    │
    ├─> Create path message: "{my_addr}"
    ├─> FOR each neighbor in seen_neighbours:
    │   └─> Send "S" message with path
    │
    ├─> IF iteration < DISCOVERY_COUNT:
    │   └─> Sleep SPATH_WAIT (30 seconds)
    └─> ELSE:
        └─> Sleep SPATH_WAIT_2 (1200 seconds) + random(1-120)
```

#### Shortest Path Processing (`spath_process()`)

```
spath_process(mid, msg)
  ├─> IF running_as_cc():
  │   └─> Return (ignore)
  │
  ├─> Parse path from message
  ├─> IF my_addr in path:
  │   └─> Return (cyclic path, ignore)
  │
  ├─> IF shortest_path_to_cc is empty OR new path is shorter:
  │   ├─> Update shortest_path_to_cc
  │   └─> FOR each neighbor:
  │       ├─> Create new path: [my_addr] + spath
  │       └─> Send "S" message to neighbor
  └─> ELSE:
      └─> Ignore (not better path)
```

#### Neighbor Validation (`validate_and_remove_neighbours()`)

```
validate_and_remove_neighbours()
  WHILE True:
    ├─> FOR each neighbor in seen_neighbours:
    │   ├─> Send "V" (Validate) message
    │   ├─> IF ACK received:
    │   │   └─> Neighbor is still reachable
    │   └─> ELSE:
    │       ├─> Mark for removal
    │       └─> IF neighbor in shortest_path_to_cc:
    │           └─> Clear shortest_path_to_cc
    │
    ├─> Remove unreachable neighbors
    └─> Sleep VALIDATE_WAIT_SEC (1200 seconds)
```

---

### 7. Heartbeat System

#### Heartbeat Sending (`keep_sending_heartbeat()`)

```
keep_sending_heartbeat()
  WHILE True:
    ├─> Sleep 3 seconds
    ├─> IF image_in_progress:
    │   └─> Skip and sleep 200 seconds
    │
    ├─> Call send_heartbeat()
    ├─> IF send failed:
    │   ├─> Increment consecutive_hb_failures
    │   ├─> IF failures > 1:
    │   │   ├─> Reinitialize LoRa
    │   │   └─> Reset failure counter
    │
    ├─> IF iteration < DISCOVERY_COUNT:
    │   └─> Sleep HB_WAIT (120 seconds) + random(3-10)
    └─> ELSE:
        └─> Sleep HB_WAIT_2 (1200 seconds) + random(1-120)
```

#### Heartbeat Creation (`send_heartbeat()`)

```
send_heartbeat()
  ├─> Get possible_paths()
  ├─> Read GPS coordinates from file
  ├─> Get GPS staleness timestamp
  ├─> Build heartbeat message:
  │   "{my_addr}:{uptime}:{total_images}:{person_images}:{gps}:{staleness}:{neighbours}:{path}"
  ├─> Encrypt heartbeat message
  ├─> FOR each peer in possible_paths:
  │   ├─> Send "H" message
  │   └─> IF success:
  │       ├─> Reset consecutive_hb_failures
  │       └─> Return True
  └─> Return False
```

#### Heartbeat Processing (`hb_process()`)

```
hb_process(mid, msgbytes, sender)
  ├─> Get possible_paths(sender)
  ├─> Extract creator from message ID
  │
  ├─> IF running_as_cc():
  │   ├─> Update hb_map[creator] counter
  │   ├─> Convert heartbeat to base64
  │   ├─> Create heartbeat_payload
  │   ├─> Upload to cloud via sim_upload_hb()
  │   └─> Return (don't forward)
  │
  └─> ELSE: - Field node
      ├─> FOR each peer in possible_paths:
      │   ├─> Forward "H" message
      │   └─> IF success:
      │       └─> Break
      └─> IF all forwards failed:
          └─> Log error
```

---

### 8. Image Transmission System

#### Image Sending Loop (`image_sending_loop()`)

```
image_sending_loop()
  WHILE True:
    ├─> Sleep 4 seconds
    ├─> Get possible_paths()
    ├─> IF no paths available:
    │   └─> Continue (can't send)
    │
    ├─> IF images_to_send queue not empty:
    │   ├─> Pop first image from queue
    │   ├─> Load image file
    │   ├─> Get image bytes
    │   ├─> Call send_image_to_mesh()
    │   ├─> IF send failed:
    │   │   └─> Push image back to queue
    │   └─> Sleep PHOTO_SENDING_DELAY (600 seconds)
```

#### Image Transmission (`send_image_to_mesh()`)

```
send_image_to_mesh(imgbytes)
  ├─> Encrypt image (hybrid encryption)
  ├─> Get possible_paths()
  ├─> FOR each peer in possible_paths:
  │   ├─> Acquire image lock
  │   ├─> Send "P" message (chunked if large)
  │   ├─> Release image lock
  │   └─> IF success:
  │       └─> Return True
  └─> Return False
```

#### Image Processing (`img_process()`)

```
img_process(cid, msg, creator, sender)
  ├─> Clear chunk ID from chunk_map
  │
  ├─> IF running_as_cc():
  │   ├─> Decrypt image (if encryption enabled)
  │   ├─> Create image.Image from bytes
  │   ├─> Save to IMAGE_DIR/cc_{creator}_{cid}.jpg
  │   ├─> Add to images_saved_at_cc list
  │   └─> Upload to cloud via sim_send_image()
  │
  └─> ELSE: - Field node
      ├─> Get possible_paths(sender)
      ├─> FOR each peer in possible_paths:
      │   ├─> Forward "P" message
      │   └─> IF success:
      │       └─> Break
      └─> IF all forwards failed:
          └─> Log error
```

#### Chunk Management

```
begin_chunk(msg)
  ├─> Parse: "msgtype:chunkid:numchunks"
  └─> Initialize chunk_map[chunkid] = (msgtype, numchunks, [])

add_chunk(msgbytes)
  ├─> Extract chunk ID (first 3 bytes)
  ├─> Extract chunk index (bytes 3-5)
  ├─> Extract chunk data (remaining bytes)
  └─> Append to chunk_map[chunkid][2]

get_missing_chunks(cid)
  ├─> Get expected_chunks from chunk_map
  ├─> FOR i in range(expected_chunks):
  │   ├─> Check if chunk i exists
  │   └─> IF missing:
  │       └─> Add to missing list
  └─> Return missing list

recompile_msg(cid)
  ├─> IF missing chunks exist:
  │   └─> Return None
  ├─> FOR each chunk in order:
  │   └─> Concatenate chunk data
  └─> Return complete message

end_chunk(mid, msg)
  ├─> Extract chunk ID
  ├─> Get missing chunks
  ├─> IF missing chunks exist:
  │   ├─> Build missing list string
  │   └─> Return (False, missing_str, None, None, None)
  └─> ELSE:
      ├─> Recompile message
      └─> Return (True, None, cid, recompiled, creator)
```

---

### 9. Cellular Communication Module (`cellular_driver.py`)

#### Cellular Initialization (`init_sim()`)

```
init_sim()
  ├─> Create Cellular instance
  ├─> Call cellular_system.initialize()
  └─> Return success status
```

#### Cellular Class (`Cellular`)

```
Cellular.__init__()
  ├─> Create SC16IS750 UART bridge
  ├─> Initialize connection state
  └─> Define APN configurations

Cellular.initialize()
  ├─> Send "AT" command (test modem)
  ├─> Check SIM card status
  ├─> Check signal strength
  ├─> Set network mode
  ├─> Wait for network registration
  ├─> Try APN configurations:
  │   ├─> airtelgprs
  │   ├─> airtelgprs.com
  │   ├─> www.airtelgprs.com
  │   ├─> internet
  │   └─> airtel.in
  ├─> Get IP address
  ├─> Initialize HTTP session
  └─> Return success status

Cellular.upload_data(data_payload, url)
  ├─> Convert payload to JSON
  ├─> Set HTTP URL
  ├─> Set content type (application/json)
  ├─> Setup HTTP data upload
  ├─> Send JSON data
  ├─> Execute POST request
  ├─> Parse HTTP response
  └─> Return result with status_code

Cellular.check_connection()
  ├─> Send "AT+CGPADDR=1"
  └─> Verify IP address still assigned

Cellular.reconnect()
  ├─> Reset connection state
  └─> Call initialize() again
```

#### Image Upload (`sim_send_image()`)

```
sim_send_image(creator, encimb)
  ├─> IF cellular_system not initialized:
  │   └─> Return False
  │
  ├─> Check connection (retry up to 3 times)
  │   ├─> IF connection lost:
  │   │   └─> Attempt reconnect()
  │
  ├─> Convert image to base64
  ├─> Create payload:
  │   {
  │     "machine_id": creator,
  │     "message_type": "event",
  │     "image": base64_image
  │   }
  │
  ├─> Upload with retry (up to 3 times):
  │   ├─> Call cellular_system.upload_data()
  │   ├─> IF status_code == 200:
  │   │   └─> Return True
  │   └─> ELSE:
  │       └─> Exponential backoff and retry
  └─> Return False
```

#### Heartbeat Upload (`sim_upload_hb()`)

```
sim_upload_hb(heartbeat_data)
  ├─> IF not command center:
  │   └─> Return False
  │
  ├─> Call cellular_system.upload_data()
  ├─> IF status_code == 200:
  │   └─> Return True
  └─> ELSE:
      └─> Return False
```

---

### 10. GPS Module (`gps_driver.py`)

#### GPS Initialization (`keep_updating_gps()`)

```
keep_updating_gps()
  ├─> Wait 3 seconds (let LoRa settle)
  ├─> Initialize SC16IS750 UART bridge
  ├─> Initialize GPS parser
  │
  └─> WHILE True:
      ├─> IF image_in_progress:
      │   └─> Sleep longer
      │
      ├─> Clear stale GPS data
      ├─> Call gps.update()
      │
      ├─> IF GPS has fix:
      │   ├─> Get coordinates
      │   ├─> IF coordinates valid:
      │   │   ├─> Update gps_str
      │   │   └─> Update gps_last_time
      │   └─> ELSE:
      │       └─> Log "GPS has fix but no coordinates"
      │
      ├─> ELSE:
      │   └─> Log "GPS has no fix"
      │
      ├─> Clear buffer periodically (every 30 reads)
      │
      ├─> IF no successful read in 100 iterations:
      │   ├─> Reinitialize GPS hardware
      │   └─> Reset last_successful_read
      │
      └─> Sleep GPS_WAIT_SEC (5 seconds)
```

#### GPS Class (`GPS`)

```
GPS.__init__(uart)
  ├─> Store UART reference
  ├─> Initialize buffer
  └─> Initialize coordinates

GPS.update()
  ├─> Read data from UART
  ├─> Append to buffer
  ├─> Process complete sentences (NMEA)
  ├─> Parse GGA or RMC sentences
  └─> Update coordinates if valid

GPS._parse_sentence(sentence)
  ├─> Validate checksum
  ├─> IF GGA sentence:
  │   └─> _parse_gga()
  └─> IF RMC sentence:
      └─> _parse_rmc()

GPS._parse_gga(sentence)
  ├─> Extract fix quality
  ├─> IF quality > 0:
  │   ├─> Extract latitude/longitude
  │   ├─> Convert NMEA to decimal
  │   └─> Write to gps_coordinate.txt file
  └─> ELSE:
      └─> Return (no fix)

GPS._parse_rmc(sentence)
  ├─> Check status (A = active)
  ├─> IF status == 'A':
  │   ├─> Extract latitude/longitude
  │   ├─> Convert NMEA to decimal
  │   └─> Write to gps_coordinate.txt file
  └─> ELSE:
      └─> Return (void)

GPS.write_coordinates_to_file(lat, lon)
  ├─> Open gps_coordinate.txt
  ├─> Write: "{lat},{lon}"
  ├─> Write: "Latitude: {lat}"
  ├─> Write: "Longitude: {lon}"
  └─> Write: "Updated: {timestamp}"

GPS.has_fix()
  └─> Return fix_quality > 0

GPS.get_coordinates()
  ├─> IF has_fix():
  │   └─> Return (latitude, longitude)
  └─> ELSE:
      └─> Return (None, None)
```

---

### 11. Command Processing

#### Command Execution (`execute_command()`)

```
execute_command(command)
  ├─> IF command == "SENDHB":
  │   └─> asyncio.create_task(send_heartbeat())
  │
  ├─> IF command == "SENDIMG":
  │   └─> take_image_and_send_now()
  │
  └─> IF command == "RESET":
      ├─> log_to_file()
      └─> machine.reset()
```

#### Command Processing (`command_process()`)

```
command_process(mid, msg)
  ├─> Decode message string
  ├─> Parse: "dest;path;command"
  │
  ├─> IF dest == my_addr:
  │   └─> execute_command(command)
  │
  └─> ELSE:
      ├─> Get next hop from path
      └─> Forward "C" message to next hop
```

---

### 12. Utility Functions

#### Logging System

```
log(msg)
  ├─> Get human-readable timestamp
  ├─> Format: "{my_addr}@{time} : {msg}"
  ├─> Add to log_entries_buffer
  └─> Print to console

log_to_file()
  ├─> Open LOG_FILE_PATH
  ├─> Write all entries from log_entries_buffer
  ├─> Flush file
  └─> Clear buffer

print_summary_and_flush_logs()
  WHILE True:
    ├─> Sleep 30 seconds
    ├─> IF image_in_progress:
    │   └─> Skip and sleep 200 seconds
    │
    ├─> Log statistics:
    │   - msgs_sent count
    │   - msgs_recd count
    │   - msgs_unacked count
    │   - lora_reinit_count
    └─> Call log_to_file()
```

#### Image Lock Management

```
acquire_image_lock()
  ├─> Set image_in_progress = True
  ├─> Sleep 120 seconds
  └─> IF still locked:
      └─> Release lock

release_image_lock()
  └─> Set image_in_progress = False
```

#### Path Management

```
possible_paths(sender)
  ├─> Get shortest_path_to_cc[0] (if exists)
  ├─> FOR each neighbor in seen_neighbours:
  │   ├─> IF neighbor != my_addr AND neighbor != sender AND neighbor != sp0:
  │   │   └─> Add to possible_paths
  └─> Return possible_paths list
```

#### Time Utilities

```
time_msec()
  └─> Return milliseconds since clock_start

time_sec()
  └─> Return seconds since clock_start

get_human_ts()
  └─> Return formatted time string (MM:SS)
```

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    NETRAAJAL MESH NETWORK                     │
└─────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐
│  Command Center  │         │   Field Node     │
│    (Node 219)    │◄───────►│  (221,222,223,225)│
└──────────────────┘         └──────────────────┘
       │                            │
       │                            │
       ▼                            ▼
┌──────────────┐            ┌──────────────┐
│   Cellular   │            │   LoRa Mesh  │
│  (SIM7600)   │            │   (SX1262)   │
└──────────────┘            └──────────────┘
       │                            │
       │                            │
       ▼                            ▼
┌──────────────┐            ┌──────────────┐
│   Cloud API  │            │  Neighbor    │
│  (n8n.vyomos)│            │   Discovery  │
└──────────────┘            └──────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    FIELD NODE COMPONENTS                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Camera    │  │  PIR Sensor │  │  GPS Module │          │
│  │  (OpenMV)   │  │             │  │  (NMEA)    │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│        │                │                │                   │
│        ▼                ▼                ▼                   │
│  ┌──────────────────────────────────────────────┐           │
│  │         Person Detection Loop                 │           │
│  │  - Capture image every 5 seconds              │           │
│  │  - Check PIR sensor                           │           │
│  │  - Save image if person detected              │           │
│  └──────────────────────────────────────────────┘           │
│                                                               │
│  ┌──────────────────────────────────────────────┐           │
│  │         Image Transmission Loop               │           │
│  │  - Encrypt image (hybrid)                     │           │
│  │  - Chunk if > 195 bytes                       │           │
│  │  - Send via LoRa mesh                         │           │
│  │  - Retry on failure                           │           │
│  └──────────────────────────────────────────────┘           │
│                                                               │
│  ┌──────────────────────────────────────────────┐           │
│  │         Network Maintenance                  │           │
│  │  - Send neighbor scan (every 30s/1200s)      │           │
│  │  - Send heartbeat (every 120s/1200s)         │           │
│  │  - Validate neighbors (every 1200s)          │           │
│  │  - Update shortest path                       │           │
│  └──────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                 COMMAND CENTER COMPONENTS                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────┐           │
│  │         Network Discovery                     │           │
│  │  - Broadcast shortest paths                   │           │
│  │  - Maintain neighbor list                     │           │
│  └──────────────────────────────────────────────┘           │
│                                                               │
│  ┌──────────────────────────────────────────────┐           │
│  │         Heartbeat Aggregation                 │           │
│  │  - Receive heartbeats from all nodes           │           │
│  │  - Upload to cloud via cellular               │           │
│  └──────────────────────────────────────────────┘           │
│                                                               │
│  ┌──────────────────────────────────────────────┐           │
│  │         Image Reception                       │           │
│  │  - Receive images from field nodes            │           │
│  │  - Decrypt images                             │           │
│  │  - Save to /ccimages                          │           │
│  │  - Upload to cloud via cellular               │           │
│  └──────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## Message Flow Examples

### Example 1: Person Detection and Image Transmission

```
Field Node (222)
  │
  ├─> person_detection_loop()
  │   ├─> Capture image
  │   ├─> detector.check_person() → True
  │   └─> Save image to /images/raw_ABC.jpg
  │
  ├─> image_sending_loop()
  │   ├─> Load image file
  │   ├─> encrypt_hybrid(image_bytes)
  │   ├─> send_image_to_mesh()
  │   │   ├─> Chunk if > 195 bytes
  │   │   ├─> Send "B" message (Begin)
  │   │   ├─> Send "I" messages (Chunks)
  │   │   └─> Send "E" message (End)
  │   │
  │   └─> Route via shortest_path_to_cc [219]
  │
  └─> Command Center (219)
      ├─> Receive chunks
      ├─> Recompile image
      ├─> decrypt_hybrid(image_bytes)
      ├─> Save to /ccimages/cc_222_ABC.jpg
      └─> sim_send_image() → Cloud API
```

### Example 2: Heartbeat Flow

```
Field Node (222)
  │
  ├─> keep_sending_heartbeat()
  │   ├─> send_heartbeat()
  │   │   ├─> Build: "222:3600:100:5:28.613,77.209:1200:[221,223]:[219]"
  │   │   ├─> encrypt_rsa(heartbeat_msg)
  │   │   └─> Send "H" message to 219
  │   │
  │   └─> Route via shortest_path_to_cc [219]
  │
  └─> Command Center (219)
      ├─> hb_process()
      │   ├─> Update hb_map[222]
      │   ├─> Convert to base64
      │   └─> sim_upload_hb() → Cloud API
      │
      └─> Cloud receives heartbeat data
```

### Example 3: Network Discovery

```
Command Center (219)
  │
  ├─> send_scan()
  │   └─> Send "N" message (broadcast: 65535)
  │
  ├─> Field Node (222) receives
  │   ├─> scan_process()
  │   └─> Add 219 to seen_neighbours
  │
  ├─> send_spath()
  │   └─> Send "S" message: "219" to all neighbors
  │
  └─> Field Node (222) receives
      ├─> spath_process()
      ├─> Update shortest_path_to_cc = [219]
      └─> Propagate: "222,219" to its neighbors
```

---

## Constants and Configuration

### Timing Constants
- `MIN_SLEEP`: 0.1 seconds
- `ACK_SLEEP`: 0.2 seconds
- `CHUNK_SLEEP`: 0.3 seconds
- `DISCOVERY_COUNT`: 100 iterations
- `HB_WAIT`: 120 seconds (initial heartbeat interval)
- `HB_WAIT_2`: 1200 seconds (steady-state heartbeat interval)
- `SPATH_WAIT`: 30 seconds (initial path broadcast)
- `SPATH_WAIT_2`: 1200 seconds (steady-state path broadcast)
- `SCAN_WAIT`: 30 seconds (initial neighbor scan)
- `SCAN_WAIT_2`: 1200 seconds (steady-state neighbor scan)
- `VALIDATE_WAIT_SEC`: 1200 seconds (neighbor validation)
- `PHOTO_TAKING_DELAY`: 1 second
- `PHOTO_SENDING_DELAY`: 600 seconds
- `GPS_WAIT_SEC`: 5 seconds

### Communication Constants
- `MIDLEN`: 7 bytes (message ID length)
- `FRAME_SIZE`: 195 bytes (max single message size)
- `AIR_SPEED`: 19200 bps (LoRa air data rate)
- `FLAKINESS`: 0% (message drop probability for testing)

### Device Addresses
- Command Center: 219
- Field Nodes: 221, 222, 223, 225

---

## Error Handling and Recovery

### LoRa Communication Failures
- Retry up to 3 times for message sending
- Reinitialize LoRa after consecutive heartbeat failures
- Progressive sleep delays for ACK waiting

### Image Transmission Failures
- Failed images are pushed back to queue
- Chunk retransmission for missing chunks
- Image lock timeout (120 seconds)

### Cellular Connection Failures
- Connection health check with retry (3 attempts)
- Automatic reconnection on failure
- Multiple APN configurations for reliability
- Exponential backoff for upload retries

### GPS Failures
- Periodic buffer clearing to prevent overflow
- Reinitialization after 100 failed reads
- Graceful degradation (continues without GPS)

### Neighbor Validation
- Periodic validation every 1200 seconds
- Automatic removal of unreachable neighbors
- Path recalculation on neighbor loss

---

## Security Features

1. **RSA Encryption**: Heartbeat messages (max 117 bytes)
2. **Hybrid Encryption**: Image data (AES + RSA)
3. **Message Authentication**: Message IDs with random components
4. **Acknowledgment System**: Ensures message delivery
5. **Private Key Management**: Secure storage via PrivKeyRepo

---

## File System Structure

```
/sdcard (or /flash)
├── /ccimages/          (Command Center only)
│   └── cc_{creator}_{cid}.jpg
├── /images/            (Field Nodes only)
│   └── raw_{random}.jpg
├── mainlog.txt         (System logs)
└── gps_coordinate.txt (GPS coordinates)
    ├── "{lat},{lon}"
    ├── "Latitude: {lat}"
    ├── "Longitude: {lon}"
    └── "Updated: {timestamp}"
```

---

## End of Documentation

This flowchart documents all major processes and functions in the Netrajaal system. For implementation details, refer to the source code files.

