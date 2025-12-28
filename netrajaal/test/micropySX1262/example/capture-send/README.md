# Image Capture and Send Example

This example demonstrates capturing an image on one OpenMV RT1062 and sending it to another OpenMV RT1062 via SX1262 LoRa module with reliable ACK protocol.

## Features

- **Fast Transmission**: Uses highest data rate settings (SF5, BW500kHz, CR5)
- **Reliable Protocol**: Every packet requires ACK, with automatic retransmission on failure
- **Error Handling**: Detects corrupted packets (CRC errors) and retries up to 5 times
- **Image Display**: Received image is displayed in OpenMV IDE

## Hardware Setup

- 2x OpenMV RT1062 boards
- 2x Waveshare Core1262-868M modules
- Pin connections (both boards):
  - P0: MOSI
  - P1: MISO
  - P2: SCLK
  - P3: CS (Chip Select)
  - P6: RESET
  - P7: BUSY
  - P13: DIO1 (IRQ)

## Usage

1. **On Receiver (first device)**:
   ```python
   import rx_receive
   ```
   This will start listening for incoming images and display them when received.

2. **On Transmitter (second device)**:
   ```python
   import tx_capture
   ```
   This will capture an image and transmit it to the receiver.

## Protocol

- **Header Packet**: Contains image width, height, and size (9 bytes total)
- **Data Packets**: Each packet contains 1-byte sequence number + up to 254 bytes of image data
- **ACK**: Receiver sends 1-byte ACK (sequence number) after each successful packet
- **Retry**: Transmitter retries up to 5 times if no ACK received within timeout

## Configuration

Both scripts use the same LoRa configuration for fastest speed:
- Frequency: 868.0 MHz
- Spreading Factor: 5
- Bandwidth: 500 kHz
- Coding Rate: 5 (4/5)
- Preamble Length: 8
- TX Power: 14 dBm

## Image Format

- Format: RGB565 (uncompressed)
- Default Size: QVGA (320x240 pixels)
- Size: ~153,600 bytes

## Notes

- Ensure receiver is running before starting transmitter
- Both devices must use identical LoRa configuration
- Maximum packet size is 255 bytes (254 bytes payload + 1 byte sequence)
- Image will be displayed on receiver's OpenMV IDE frame buffer

