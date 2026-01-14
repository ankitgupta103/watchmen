# Message Types Documentation

## Heartbeat (H)

**Sent:** Every 3 seconds initially, then every 600-610s (or 1200-1320s after initial period)

**Message Structure:**
```
{msg_uid};{my_addr}:{time_sec()}:{total_image_count}:{person_image_count}:{gps_coords}:{gps_staleness}:{seen_neighbours}:{shortest_path_to_cc}
```

**Fields:**
- `msg_uid`: bytes (7 bytes) - Message identifier (msg_typ + creator + sender + dest + random)
- `my_addr`: int - Device address
- `time_sec()`: int - Uptime in seconds
- `total_image_count`: int - Total photos taken
- `person_image_count`: int - Events seen
- `gps_coords`: str - GPS coordinates (lat,long format)
- `gps_staleness`: float - GPS staleness in seconds
- `seen_neighbours`: list - List of neighbor node IDs
- `shortest_path_to_cc`: list - Shortest path to command center

**Response (ACK):**
- Type: A
- Structure: `{msg_uid}`
- Payload: `msg_uid` (7 bytes) - Message identifier of the original H message

**Upload to Server:**
- `machine_id`: int
- `message_type`: str - "heartbeat"
- `heartbeat_data`: bytes (base64 encoded)
- `epoch_ms`: int

---

## Text Event (T)

**Sent:** When PIR sensor detects motion (event-driven)

**Message Structure:**
```
{msg_uid};{my_addr}:{epoch_ms}:{gps_coords}:{gps_staleness}
```

**Fields:**
- `msg_uid`: bytes (7 bytes) - Message identifier
- `my_addr`: int - Device address
- `epoch_ms`: int - Event timestamp in milliseconds
- `gps_coords`: str - GPS coordinates
- `gps_staleness`: float - GPS staleness in seconds

**Response (ACK):**
- Type: A
- Structure: `{msg_uid}`
- Payload: `msg_uid` (7 bytes) - Message identifier of the original T message

**Upload to Server:**
- `machine_id`: int
- `message_type`: str - "event_text"
- `event_data`: bytes (base64 encoded)
- `epoch_ms`: int

---

## Neighbor Scan (N)

**Sent:** Every 30s initially, then every 1200-1320s (broadcast to all nodes)

**Message Structure:**
```
{msg_uid};{node_id}
```

**Fields:**
- `msg_uid`: bytes (7 bytes) - Message identifier
- `node_id`: bytes (1 byte) - Node address (0-255)

**Response:** None (no ACK)

---

## Validation/Ping (V)

**Sent:** Every 1200s to validate neighbor connectivity

**Message Structure:**
```
{msg_uid};Nothing
```

**Fields:**
- `msg_uid`: bytes (7 bytes) - Message identifier
- Message: bytes - Fixed value b"Nothing"

**Response (ACK):**
- Type: A
- Structure: `{msg_uid}`
- Payload: `msg_uid` (7 bytes) - Message identifier of the original V message

---

## Wait (W)

**Sent:** When device is busy processing another transfer

**Message Structure:**
```
{msg_uid};20
```

**Fields:**
- `msg_uid`: bytes (7 bytes) - Message identifier
- Wait time: str - Fixed value "20"

**Response:** None (no ACK)

---

## Acknowledgment (A)

**Sent:** In response to H, T, V messages (0.2s delay between multiple ACKs)

**Message Structure:**
```
{msg_uid};{original_msg_uid}
```
or
```
{msg_uid};{original_msg_uid}:-1
```
or
```
{msg_uid};{original_msg_uid}:{missing_chunk_str}
```

**Fields:**
- `msg_uid`: bytes (7 bytes) - ACK message identifier
- `original_msg_uid`: bytes (7 bytes) - Message identifier of the original message being acknowledged
- Status (optional): str - "-1" for success, or comma-separated missing chunk indices

**Response:** None (no ACK)
