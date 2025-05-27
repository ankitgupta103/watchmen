# Image Transfer Over LoRa Using Raspberry Pi and Ra-01SH (SX1262)

## Overview

This guide explains how to transfer a small image (\~25-30 kB) between two Raspberry Pis using the Ra-01SH (based on SX1262) LoRa module via LoRa communication. It covers end-to-end setup, data fragmentation, transmission, reception, and reconstruction.

---

## Hardware Requirements

* 2x Raspberry Pi boards (any model, ideally with GPIO and SPI support)
* 2x Ra-01SH (SX1262-based) LoRa modules
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

> ⚠️ Note: The 256-byte payload is supported when using the SX1262 directly (LoRa mode), not LoRaWAN mode. LoRaWAN restricts the payload further (typical 51–222 bytes depending on region and settings).

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

```
┌────────────┐     SPI     ┌────────────┐      RF       ┌────────────┐     SPI     ┌────────────┐
│ Raspberry  │────────────▶│ Ra-01SH TX │──────────────▶│ Ra-01SH RX │────────────▶│ Raspberry  │
│ Pi Sender  │             └────────────┘                └────────────┘             │ Pi Gateway│
└────────────┘                                                             └────────────┘
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

```python
# sender.py
from SX127x.LoRa import LoRa
from LoRaWAN.MHDR import MHDR
import LoRaWAN
import json
from image_utils import image_to_chunks

image_chunks = image_to_chunks("test.jpg")
frame_id = 0

for chunk in image_chunks:
    payload = {
        "frame_id": frame_id,
        "total_frames": len(image_chunks),
        "payload": chunk
    }
    json_data = json.dumps(payload)
    data = list(map(ord, json_data))
    lorawan = LoRaWAN.new(nwskey, appskey)
    lorawan.create(MHDR.UNCONF_DATA_UP, {
        'devaddr': devaddr,
        'fcnt': frame_id,
        'data': data
    })
    lora.write_payload(lorawan.to_raw())
    lora.set_mode(MODE.TX)
    frame_id += 1
```

---

## Receiver Node (Gateway) Logic

```python
# receiver.py
from SX127x.LoRa import LoRa
from LoRaWAN.MHDR import MHDR
import LoRaWAN
import json, base64

received_data = {}

def on_rx_done():
    payload = lora.read_payload(nocheck=True)
    lorawan = LoRaWAN.new(nwskey, appskey)
    lorawan.read(payload)
    data = json.loads("".join(map(chr, lorawan.get_payload())))
    received_data[data["frame_id"]] = data["payload"]

    if len(received_data) == data["total_frames"]:
        full = "".join([received_data[i] for i in sorted(received_data)])
        with open("received.jpg", "wb") as f:
            f.write(base64.b64decode(full))
        print("Image saved successfully")
```

---

## Error Handling and Retransmission

* Add ACK after each frame (receiver sends back ACK message with frame ID)
* If no ACK is received within timeout, sender retries up to 3–5 times
* Store `frame_id` to resume broken transfers

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
4. Run `sender.py` on Transmitter Pi

---

## Potential Issues and Mitigation

| Issue                           | Description                                        | Mitigation                                        |
| ------------------------------- | -------------------------------------------------- | ------------------------------------------------- |
| Frame loss                      | Packets may be lost due to interference or timeout | Use ACK + retry mechanism                         |
| Corrupted data                  | Partial or incorrect payload received              | Use base64 with CRC/checksum validation           |
| Power instability               | Ra-01SH needs stable 3.3V, >200mA                  | Use a low-dropout regulator (LDO), add capacitors |
| Duty cycle limits (e.g., in EU) | Transmitting too frequently can violate regulation | Limit transmission interval; stagger data         |
| Buffer overflows or crashes     | Sending >256-byte frame may crash LoRa driver      | Split into max 230–240-byte chunks                |
| SPI errors                      | Incorrect wiring or timing                         | Use shielded cables, double-check connections     |

---

## Future Improvements

* Use CRC or hash checks for data integrity
* Add retry queue for failed transmissions
* Implement compression (e.g., zlib)
* Add GUI interface to view/send images
* Switch to raw LoRa (non-LoRaWAN) to use full 256-byte payload easily

---

## References

* [pySX127x GitHub](https://github.com/mayeranalytics/pySX127x)
* [Ra-01SH Datasheet](https://docs.ai-thinker.com/_media/lora/docs/ra-01sh_specification_v1.1.pdf)
* [LoRaWAN Image Transfer Example](https://github.com/jeroennijhof/LoRaWAN-image-transfer)

---




