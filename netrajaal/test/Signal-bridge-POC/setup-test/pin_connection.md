# SPI Pin Connection Guide
## OpenMV RT1062 (Master) ↔ ESP32 (Slave)

### Pin Connections

| Signal | OpenMV RT1062 | ESP32 | Description |
|--------|---------------|-------|-------------|
| **MOSI** | P0  | GPIO 23 | Master Out Slave In - Data from OpenMV to ESP32 |
| **MISO** | P1  | GPIO 19 | Master In Slave Out - Data from ESP32 to OpenMV |
| **SCK** | P2   | GPIO 18 | Serial Clock - Clock signal from OpenMV |
| **CS/SS** | P3 | GPIO 5 | Chip Select - Slave select signal from OpenMV |

### Connection Diagram

```
OpenMV RT1062 (Master)          ESP32 (Slave)
─────────────────────          ──────────────
    P0 (MOSI)  ──────────────>  GPIO 23 (MOSI)
    P1 (MISO)   <──────────────  GPIO 19 (MISO)
    P2 (SCK)   ──────────────>  GPIO 18 (SCK)
    P3 (CS)     ──────────────>  GPIO 5 (SS)
```

### SPI Configuration

**OpenMV RT1062 (Master):**
- SPI Bus: SPI1
- Baudrate: 1,000,000 Hz (1 MHz)
- Mode: 0 (CPOL=0, CPHA=0)
- Buffer Size: 32 bytes
- CS Pin: P3 (manually controlled)

**ESP32 (Slave):**
- SPI Host: SPI2_HOST
- DMA Channel: 2
- Mode: 0 (CPOL=0, CPHA=0)
- Buffer Size: 32 bytes
- Queue Size: 3

### Notes

1. **Ground Connection**: Ensure both devices share a common ground (GND).

2. **Power**: Both devices should be powered independently. Do not connect VCC between devices.

3. **CS Pin**: The CS (Chip Select) pin on OpenMV is manually controlled in software (P3). It goes LOW before each transaction and HIGH after.

4. **SPI Mode**: Both devices use SPI Mode 0:
   - CPOL = 0 (Clock idle low)
   - CPHA = 0 (Data sampled on leading edge)

5. **Default Pins**: 
   - OpenMV RT1062 uses SPI1 default pins (P0, P1, P2)
   - CS pin P3 is custom (default would be P10 for SPI0, but SPI1 doesn't have a default CS)

### Physical Connections

1. Connect OpenMV P0 → ESP32 GPIO 23 (MOSI)
2. Connect OpenMV P1 → ESP32 GPIO 19 (MISO)
3. Connect OpenMV P2 → ESP32 GPIO 18 (SCK)
4. Connect OpenMV P3 → ESP32 GPIO 5 (SS/CS)
5. Connect GND of OpenMV → GND of ESP32

### Verification

After connections:
1. Flash ESP32 with the compiled firmware
2. Run the OpenMV Python script
3. Check serial output on both devices for communication confirmation

### Troubleshooting

- **No communication**: Verify all 4 SPI lines + GND are connected
- **Wrong data**: Check that MOSI/MISO are not swapped
- **Timing issues**: Verify both use SPI Mode 0
- **CS issues**: Ensure CS pin is properly controlled (LOW during transaction)
