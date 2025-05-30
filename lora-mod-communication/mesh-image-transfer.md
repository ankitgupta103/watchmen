# Image Transfer Over LoRa Using Raspberry Pi and Ra-01SH (SX1262)

## Overview

This guide explains how to transfer a small image (\~25-30 kB) between two or more Raspberry Pis using the Ra-01SH (based on SX1262) LoRa module via LoRa communication. It covers end-to-end setup, data fragmentation, transmission, reception, and reconstruction for both single-node and multi-node setups.

---

## Hardware Requirements

* 2 or more Raspberry Pi boards (any model, ideally with GPIO and SPI support)
* 1x Ra-01SH (SX1262-based) LoRa module per Raspberry Pi
* Jumper wires
* Antennas matched for 868/915 MHz

---

## LoRa Module and Capabilities

**Ra-01SH (SX1262) Highlights:**

* Frequency range: 803 MHz \~ 930 MHz
* Supports LoRa, FSK, GFSK, MSK, GMSK, and OOK
* Supports up to **256-byte** payload per packet (non-LoRaWAN)
* TX Power: up to +22 dBm
* Sensitivity: as low as -140 dBm
* Power supply: 3.3 V (recommended current > 200 mA)
* Interface: SPI

> ⚠️ Note: The 256-byte payload is supported when using the SX1262 directly (LoRa mode), not LoRaWAN mode.

---

## LoRa Communication Limitations

Despite the 256-byte payload capacity, LoRa has these constraints:

* **Half-duplex**: Only one-way communication at a time
* **Low data rate**: Typically 0.3 kbps to 27 kbps
* **Transmission delay**: 1–2 seconds per frame depending on SF and bandwidth
* **Interference sensitivity**: Obstructions or other devices can cause data loss
* **Regulatory limits**: Duty cycle restrictions in EU/US regions limit continuous transmission

---

## System Architecture

### Single Sender - Single Receiver:

```
┌────────────┐     SPI     ┌────────────┐      RF       ┌────────────┐     SPI     ┌────────────┐
│ Raspberry  │────────────▶│ Ra-01SH TX │──────────────▶│ Ra-01SH RX │────────────▶│ Raspberry  │
│ Pi Sender  │             └────────────┘                └────────────┘             │ Pi Gateway│
└────────────┘                                                             └────────────┘
```

### Multi Sender - One Receiver (Gateway):

```
┌────────────┐                ┌────────────┐
│ Sender Pi 1│                │ Sender Pi 2│
└─────┬──────┘                └─────┬──────┘
      │                               │
      ▼                               ▼
┌────────────┐      RF      ┌────────────┐      RF      ┌────────────┐
│ Ra-01SH TX │─────────────▶ Ra-01SH RX │ <────────────│ Ra-01SH TX │
└─────┬──────┘              └─────┬──────┘              └─────┬──────┘
      │                               │
      ▼                               ▼
┌────────────┐                ┌────────────┐
│ Raspberry  │                │ Raspberry  │
│ Pi Gateway │                │ Pi Gateway │
└────────────┘                └────────────┘
```

---

## Image Preprocessing

Convert the image into a base64 string and split it into chunks up to 230–250 bytes (leaving room for headers/metadata).

```python
# image_utils.py
import base64

def image_to_chunks(path, chunk_size=240):
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode('utf-8')
    return [encoded[i:i+chunk_size] for i in range(0, len(encoded), chunk_size)]
```

---

## Sender Node (Transmitter) Logic

Each sender should add a unique `node_id` or `sender_id` to every message.

```python
# sender.py
node_id = "NODE01"  # Unique ID per node
...
payload = {
    "node_id": node_id,
    "frame_id": frame_id,
    "total_frames": len(image_chunks),
    "payload": chunk
}
```

---

## Receiver Node (Gateway) Logic

The receiver identifies sender using the `node_id` and stores data separately.

```python
# receiver.py
if data["node_id"] not in received_data:
    received_data[data["node_id"]] = {}
received_data[data["node_id"]][data["frame_id"]] = data["payload"]
```

Once `total_frames` are received for a node, the image is reassembled and saved with the node ID:

```python
with open(f"received_{node_id}.jpg", "wb") as f:
    f.write(base64.b64decode(full))
```

---

## Error Handling and Retransmission

* Use ACK messages with sender-specific frame tracking
* Each sender resends unacknowledged frames with retry limit
* Optionally schedule node transmissions using a time slot to prevent collision

---

## Multi-Node Communication

### Strategies:

1. **Time Slot Scheduling**:

   * Each node transmits during its assigned time slot (e.g., every 5s)
   * Simple, avoids RF collision

2. **Polling-Based**:

   * Gateway sends a poll packet: `"NODE01_READY?"`
   * Only the polled node replies

3. **ALOHA with Retries**:

   * Nodes transmit randomly and retry on failure
   * Least efficient but simplest

4. **Token-Passing (Advanced)**:

   * Gateway passes a token to a node, allowing it to send
   * After sending, node releases token to next

### Node Identification:

* Use short unique `node_id` per device
* Include node ID in every transmission for proper routing and file saving

---

## Performance Tips

* Use **Spreading Factor 7** for higher speed, SF12 for max distance
* Use `set_pa_config()` to set TX power:

  ```python
  lora.set_pa_config(pa_select=1, max_power=0x0F, output_power=0x0E)
  ```
* Reduce interference by testing in clear RF environments
* Add LED status indicators for send/receive/debug

---

## Running the System

1. Install required Python packages:

   ```sh
   pip install pySX127x pycryptodome
   ```
2. Connect Ra-01SH SPI and DIO pins correctly (see board\_config.py)
3. Run `receiver.py` on Gateway Pi
4. Run `sender.py` on each Sender Pi (with unique `node_id`)

---

## Potential Issues and Mitigation# Image Transfer Over LoRa Using Raspberry Pi and Ra-01SH (SX1262)

## Table of Contents

* [Overview](#overview)
* [Hardware Requirements](#hardware-requirements)
* [LoRa Module and Capabilities](#lora-module-and-capabilities)
* [LoRa Communication Limitations](#lora-communication-limitations)
* [System Architecture](#system-architecture)
* [Image Preprocessing](#image-preprocessing)
* [Sender Node (Transmitter) Logic](#sender-node-transmitter-logic)
* [Receiver Node (Gateway) Logic](#receiver-node-gateway-logic)
* [Error Handling and Retransmission](#error-handling-and-retransmission)
* [Multi-Node Communication](#multi-node-communication)
* [Performance Tips](#performance-tips)
* [Running the System](#running-the-system)
* [Potential Issues and Mitigation](#potential-issues-and-mitigation)
* [Future Improvements](#future-improvements)

---

## Overview

This guide explains how to transfer a small image (\~25-30 kB) between two or more Raspberry Pis using the Ra-01SH (based on SX1262) LoRa module via LoRa communication. It covers end-to-end setup, data fragmentation, transmission, reception, and reconstruction for both single-node and multi-node setups.

---

## Hardware Requirements

* 2 or more Raspberry Pi boards (any model, ideally with GPIO and SPI support)
* 1x Ra-01SH (SX1262-based) LoRa module per Raspberry Pi
* Jumper wires
* Antennas matched for 868/915 MHz

---

## LoRa Module and Capabilities

**Ra-01SH (SX1262) Highlights:**

* Frequency range: 803 MHz \~ 930 MHz
* Supports LoRa, FSK, GFSK, MSK, GMSK, and OOK
* Supports up to **256-byte** payload per packet (non-LoRaWAN)
* TX Power: up to +22 dBm
* Sensitivity: as low as -140 dBm
* Power supply: 3.3 V (recommended current > 200 mA)
* Interface: SPI

> ⚠️ Note: The 256-byte payload is supported when using the SX1262 directly (LoRa mode), not LoRaWAN mode.

---

## LoRa Communication Limitations

Despite the 256-byte payload capacity, LoRa has these constraints:

* **Half-duplex**: Only one-way communication at a time
* **Low data rate**: Typically 0.3 kbps to 27 kbps
* **Transmission delay**: 1–2 seconds per frame depending on SF and bandwidth
* **Interference sensitivity**: Obstructions or other devices can cause data loss
* **Regulatory limits**: Duty cycle restrictions in EU/US regions limit continuous transmission

---

## System Architecture

### Single Sender - Single Receiver:

```
┌────────────┐     SPI     ┌────────────┐      RF       ┌────────────┐     SPI     ┌────────────┐
│ Raspberry  │────────────▶│ Ra-01SH TX │──────────────▶│ Ra-01SH RX │────────────▶│ Raspberry  │
│ Pi Sender  │             └────────────┘                └────────────┘             │ Pi Gateway│
└────────────┘                                                             └────────────┘
```

### Multi Sender - One Receiver (Gateway):

```
┌────────────┐                ┌────────────┐
│ Sender Pi 1│                │ Sender Pi 2│
└─────┬──────┘                └─────┬──────┘
      │                               │
      ▼                               ▼
┌────────────┐      RF      ┌────────────┐      RF      ┌────────────┐
│ Ra-01SH TX │─────────────▶ Ra-01SH RX │ <────────────│ Ra-01SH TX │
└─────┬──────┘              └─────┬──────┘              └─────┬──────┘
      │                               │
      ▼                               ▼
┌────────────┐                ┌────────────┐
│ Raspberry  │                │ Raspberry  │
│ Pi Gateway │                │ Pi Gateway │
└────────────┘                └────────────┘
```

---

## Image Preprocessing

Convert the image into a base64 string and split it into chunks up to 230–250 bytes (leaving room for headers/metadata).

```python
# image_utils.py
import base64

def image_to_chunks(path, chunk_size=240):
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode('utf-8')
    return [encoded[i:i+chunk_size] for i in range(0, len(encoded), chunk_size)]
```

---

## Sender Node (Transmitter) Logic

Each sender should add a unique `node_id` or `sender_id` to every message.

```python
# sender.py
node_id = "NODE01"  # Unique ID per node
...
payload = {
    "node_id": node_id,
    "frame_id": frame_id,
    "total_frames": len(image_chunks),
    "payload": chunk
}
```

---

## Receiver Node (Gateway) Logic

The receiver identifies sender using the `node_id` and stores data separately.

```python
# receiver.py
if data["node_id"] not in received_data:
    received_data[data["node_id"]] = {}
received_data[data["node_id"]][data["frame_id"]] = data["payload"]
```

Once `total_frames` are received for a node, the image is reassembled and saved with the node ID:

```python
with open(f"received_{node_id}.jpg", "wb") as f:
    f.write(base64.b64decode(full))
```

---

## Error Handling and Retransmission

* Use ACK messages with sender-specific frame tracking
* Each sender resends unacknowledged frames with retry limit
* Optionally schedule node transmissions using a time slot to prevent collision

---

## Multi-Node Communication

### Strategies:

1. **Time Slot Scheduling**:

   * Each node transmits during its assigned time slot (e.g., every 5s)
   * Simple, avoids RF collision

2. **Polling-Based**:

   * Gateway sends a poll packet: `"NODE01_READY?"`
   * Only the polled node replies

3. **ALOHA with Retries**:

   * Nodes transmit randomly and retry on failure
   * Least efficient but simplest

4. **Token-Passing (Advanced)**:

   * Gateway passes a token to a node, allowing it to send
   * After sending, node releases token to next

### Node Identification:

* Use short unique `node_id` per device
* Include node ID in every transmission for proper routing and file saving

---

## Performance Tips

* Use **Spreading Factor 7** for higher speed, SF12 for max distance
* Use `set_pa_config()` to set TX power:

  ```python
  lora.set_pa_config(pa_select=1, max_power=0x0F, output_power=0x0E)
  ```
* Reduce interference by testing in clear RF environments
* Add LED status indicators for send/receive/debug

---

## Running the System

1. Install required Python packages:

   ```sh
   pip install pySX127x pycryptodome
   ```
2. Connect Ra-01SH SPI and DIO pins correctly (see board\_config.py)
3. Run `receiver.py` on Gateway Pi
4. Run `sender.py` on each Sender Pi (with unique `node_id`)

---

## Potential Issues and Mitigation

| Issue                           | Description                                        | Mitigation                                        |
| ------------------------------- | -------------------------------------------------- | ------------------------------------------------- |
| Frame loss                      | Packets may be lost due to interference or timeout | Use ACK + retry mechanism                         |
| Node collision                  | Multiple nodes transmitting at once                | Use time slot scheduling or polling               |
| Power instability               | Ra-01SH needs stable 3.3V, >200mA                  | Use a low-dropout regulator (LDO), add capacitors |
| Duty cycle limits (e.g., in EU) | Transmitting too frequently can violate regulation | Limit transmission interval; stagger data         |
| Buffer overflows or crashes     | Sending >256-byte frame may crash LoRa driver      | Split into max 230–240-byte chunks                |

---

## Future Improvements

* Use CRC or hash checks for data integrity
* Add retry queue for failed transmissions
* Implement compression (e.g., zlib)
* Add GUI interface to view/send images
* Switch to raw LoRa (non-LoRaWAN) to use full 256-byte payload easily
* Implement token-passing or polling-based protocol for scalable multi-node systems

---

## References

* [pySX127x GitHub](https://github.com/mayeranalytics/pySX127x)
* [Ra-01SH Datasheet](https://docs.ai-thinker.com/_media/lora/docs/ra-01sh_specification_v1.1.pdf)
* [LoRaWAN Image Transfer Example](https://github.com/jeroennijhof/LoRaWAN-image-transfer)

---

**Author**: Your Name
**Last Updated**: May 2025


| Issue                           | Description                                        | Mitigation                                        |
| ------------------------------- | -------------------------------------------------- | ------------------------------------------------- |
| Frame loss                      | Packets may be lost due to interference or timeout | Use ACK + retry mechanism                         |
| Node collision                  | Multiple nodes transmitting at once                | Use time slot scheduling or polling               |
| Power instability               | Ra-01SH needs stable 3.3V, >200mA                  | Use a low-dropout regulator (LDO), add capacitors |
| Duty cycle limits (e.g., in EU) | Transmitting too frequently can violate regulation | Limit transmission interval; stagger data         |
| Buffer overflows or crashes     | Sending >256-byte frame may crash LoRa driver      | Split into max 230–240-byte chunks                |

---

## Future Improvements

* Use CRC or hash checks for data integrity
* Add retry queue for failed transmissions
* Implement compression (e.g., zlib)
* Add GUI interface to view/send images
* Switch to raw LoRa (non-LoRaWAN) to use full 256-byte payload easily
* Implement token-passing or polling-based protocol for scalable multi-node systems

---

## References

* [pySX127x GitHub](https://github.com/mayeranalytics/pySX127x)
* [Ra-01SH Datasheet](https://docs.ai-thinker.com/_media/lora/docs/ra-01sh_specification_v1.1.pdf)
* [LoRaWAN Image Transfer Example](https://github.com/jeroennijhof/LoRaWAN-image-transfer)

---

**Author**: Your Name
**Last Updated**: May 2025
