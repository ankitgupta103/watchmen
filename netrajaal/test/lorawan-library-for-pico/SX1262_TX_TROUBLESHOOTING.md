# SX1262 TX Failure Troubleshooting Guide

## Root Cause Analysis: Error 0x0020 and TX Mode Entry Failure

### Error Code 0x0020 Meaning

**Device Error 0x0020** (bit 5 set) in SX1262 indicates:
- **Command execution failure** - A command was rejected or failed to execute
- **Invalid command state** - Command issued when chip is not ready
- **Missing prerequisites** - Required configuration steps were skipped or failed

**From SX1262 Datasheet Section 15.1:**
- Error 0x0020 = Command execution error
- Occurs when SetTx() is called but prerequisites are not met
- Chip rejects the command and stays in current mode (STDBY_XOSC)

### Why Chip Stays in STDBY_XOSC (Mode 1) Instead of TX (Mode 3)

**Observed Behavior:**
- SetTx() command is sent
- Chip mode = 1 (STDBY_XOSC) after command
- BUSY = LOW (command rejected immediately, not processing)
- Error 0x0020 set
- IRQ = 0x0000 (no TX_DONE because TX never started)

**Root Causes:**

1. **CalibrateImage Failure During Configure()**
   - CalibrateImage times out (BUSY timeout)
   - Chip left in partially configured state
   - Subsequent SetTx() commands are rejected
   - **Reference**: RadioLib GitHub issues - CalibrateImage critical for frequency lock

2. **Missing or Incorrect Frequency Calibration**
   - CalibrateImage not completed successfully
   - Chip cannot lock to target frequency
   - SetTx() waits for frequency lock, which never happens
   - **Reference**: ST Community - TX timeout when frequency not calibrated

3. **Incorrect Command Sequence**
   - Frequency must be set BEFORE CalibrateImage
   - CalibrateImage must complete BEFORE SetTx
   - All parameters must be set in correct order
   - **Reference**: LoRaMac-node reference implementation

4. **Chip State Validation Missing**
   - No verification that chip is ready before SetTx
   - No check for device errors before SetTx
   - Chip might be in error state from previous failed operation
   - **Reference**: MicroPython GitHub - OpError 0x20 requires state validation

### Why DIO1 Toggles But TX Fails

**Explanation:**
- DIO1 toggles because IRQ is configured (SetDioIrqParams was called)
- DIO1 reflects IRQ configuration, NOT actual TX completion
- Chip attempts to enter TX mode but fails internally
- DIO1 can toggle for other events (timeout, errors) not just TX_DONE
- **Internal State**: Chip is in "TX pending" state - received SetTx() but cannot complete transition

**From SX1262 Datasheet:**
- DIO1 is a general-purpose interrupt output
- Can be configured for multiple events (TX_DONE, RX_DONE, TIMEOUT, etc.)
- Toggle does NOT guarantee TX completion
- Must read IRQ status register to determine actual event

## Known-Good TX Sequence (MANDATORY ORDER)

### Complete Initialization Sequence

```
1. Hardware Reset
   - Pull RESET low for >100us
   - Release RESET (high)
   - Wait 10ms for chip stabilization
   - Wait for BUSY to go LOW

2. Wakeup
   - Send GET_STATUS command (wakes chip from sleep)
   - Wait for BUSY LOW

3. Set Standby (RC)
   - SET_STANDBY [0x00] (RC mode for initialization)
   - Wait for BUSY LOW

4. Set Regulator Mode
   - SET_REGULATOR_MODE [0x01] (DC-DC enabled)
   - Wait for BUSY LOW

5. Configure TCXO (DIO3) - REQUIRED
   - SET_DIO3_AS_TCXO_CTRL [voltage, delay_msb, delay_lsb]
   - Voltage: 0x01 = 1.7V (typical for 868MHz)
   - Delay: 5ms = 0x0140 (5 * 64 = 320 = 0x0140)
   - Wait for BUSY LOW
   - Delay 5ms for TCXO to stabilize

6. Configure RF Switch (DIO2) - REQUIRED
   - SET_DIO2_AS_RF_SWITCH_CTRL [0x01] (enable)
   - Wait for BUSY LOW

7. Set RF Frequency - MUST BE BEFORE CALIBRATION
   - SET_RF_FREQUENCY [freq_bytes]
   - Frequency: 868000000 Hz for EU868
   - Wait for BUSY LOW

8. Calibrate (General)
   - CALIBRATE [0x7F] (calibrate all: RC64K, RC13M, PLL, ADC, Image)
   - Wait for BUSY LOW (can take 1-2 seconds)
   - Delay 10ms

9. CalibrateImage (Frequency Band) - REQUIRED
   - CALIBRATE_IMAGE [freq1_msb, freq1_lsb, freq2_msb, freq2_lsb]
   - For 868MHz: calibrate at 863MHz and 870MHz
   - Wait for BUSY LOW (can take 2-3 seconds)
   - Delay 10ms
   - If timeout, clear errors and continue (some modules may not require)

10. Clear Device Errors
    - CLEAR_DEVICE_ERRORS [0x00, 0x00]
    - Wait for BUSY LOW

11. Set Packet Type
    - SET_PACKET_TYPE [0x01] (LoRa)
    - Wait for BUSY LOW

12. Set Modulation Parameters
    - SET_MODULATION_PARAMS [sf, bw, cr, ldro]
    - SF7, BW125, CR4/5, LDRO=0
    - Wait for BUSY LOW

13. Set Packet Parameters
    - SET_PACKET_PARAMS [preamble_msb, preamble_lsb, header_type, payload_len, crc, iq]
    - Preamble: 12, Header: 0 (explicit), Payload: 0 (variable), CRC: 1, IQ: 0
    - Wait for BUSY LOW

14. Set Buffer Base Address
    - SET_BUFFER_BASE_ADDRESS [0x00, 0x00] (TX base, RX base)
    - Wait for BUSY LOW

15. Set PA Config
    - SET_PA_CONFIG [paDutyCycle, hpMax, deviceSel, paLut]
    - For 14dBm: [0x04, 0x00, 0x01, 0x01]
    - For higher power: [0x04, 0x07, 0x00, 0x01]
    - Wait for BUSY LOW

16. Set TX Parameters
    - SET_TX_PARAMS [power_reg, ramp_time]
    - Power reg: 0x04 for 14dBm (non-linear mapping)
    - Ramp time: 0x04 = 40us
    - Wait for BUSY LOW

17. Set DIO IRQ Parameters
    - SET_DIO_IRQ_PARAMS [irq_mask, dio1_mask, dio2_mask, dio3_mask]
    - IRQ mask: TX_DONE | RX_DONE | TIMEOUT | CRC_ERROR
    - DIO1 mask: TX_DONE | RX_DONE
    - Wait for BUSY LOW
```

### TX Operation Sequence

```
1. Switch to XOSC Standby - REQUIRED
   - SET_STANDBY [0x01] (XOSC mode)
   - Wait for BUSY LOW
   - Delay 5ms for XOSC to stabilize

2. Clear Device Errors
   - CLEAR_DEVICE_ERRORS [0x00, 0x00]
   - Wait for BUSY LOW

3. Clear IRQ Status
   - CLEAR_IRQ_STATUS [0xFF, 0xFF] (clear all)
   - Wait for BUSY LOW

4. Write Buffer
   - WRITE_BUFFER [offset, data...]
   - Offset: 0x00
   - Data: payload bytes
   - Wait for BUSY LOW

5. Set Payload Length
   - WRITE_REGISTER [0x0702, payload_length]
   - For variable length, must set explicitly
   - Wait for BUSY LOW
   - Delay 1ms

6. Verify Chip State
   - GET_STATUS - verify chip mode = STDBY_XOSC (1)
   - GET_DEVICE_ERRORS - verify errors = 0x0000
   - If errors present, clear and retry

7. Start TX
   - SET_TX [timeout_msb, timeout_mid, timeout_lsb]
   - Timeout: 0x000000 = no timeout
   - Wait for BUSY LOW (extended timeout: 5000ms)
   - Delay 10ms for mode transition

8. Verify TX Mode Entry
   - GET_STATUS - verify chip mode = TX (3)
   - If not TX mode, read errors and abort

9. Poll IRQ Status
   - GET_IRQ_STATUS - check for TX_DONE (0x0001)
   - Poll every 10ms
   - Timeout after 5 seconds

10. On TX_DONE
    - CLEAR_IRQ_STATUS [0x01, 0x00] (clear TX_DONE)
    - SET_STANDBY [0x00] (return to RC for power saving)
    - Wait for BUSY LOW
```

## Critical Steps That Cause Failure If Skipped

### Steps That Cause Error 0x0020 If Skipped:

1. **TCXO Configuration (DIO3)** - SetTx() rejected, error 0x0020
2. **RF Switch Configuration (DIO2)** - SetTx() rejected, error 0x0020
3. **CalibrateImage** - SetTx() times out, chip cannot lock frequency
4. **XOSC Standby Before TX** - SetTx() may timeout or fail
5. **Frequency Set Before CalibrateImage** - CalibrateImage fails
6. **Payload Length Set** - TX may not start or transmit empty packet
7. **Device Errors Cleared** - Stale errors prevent command execution

### Steps That Cause BUSY Timeout If Skipped:

1. **Extended BUSY Timeout for SetTx** - Normal 1000ms timeout too short
2. **Extended BUSY Timeout for CalibrateImage** - Calibration takes 2-3 seconds
3. **XOSC Stabilization Delay** - Need 5ms after switching to XOSC
4. **TCXO Wakeup Time** - Need delay after TCXO config

## Practical Fix Checklist

### Hardware Verification

- [ ] **TCXO Present?** - Check if module has external TCXO
  - Waveshare Core1262-868M: YES, has TCXO
  - DIO3 must be connected and configured
  - Voltage: 1.7V typical for 868MHz

- [ ] **DIO3 Wired?** - Verify DIO3 pin connection
  - Not used in current implementation (TCXO auto-controlled)
  - But DIO3 must be configured via SetDio3AsTcxoCtrl

- [ ] **RF Switch Present?** - Check if module has RF switch
  - Waveshare Core1262-868M: YES, has RF switch
  - DIO2 must be configured via SetDio2AsRfSwitchCtrl

- [ ] **DIO2 Wired?** - Verify DIO2 pin connection
  - Not directly connected in current setup
  - But DIO2 must be configured for RF switch control

### Software Configuration

- [ ] **TCXO Configured?** - SetDio3AsTcxoCtrl called
  - Voltage: 0x01 (1.7V)
  - Wakeup time: 5ms (0x0140 in SX1262 time base)

- [ ] **RF Switch Configured?** - SetDio2AsRfSwitchCtrl called
  - Enable: 0x01 (true)

- [ ] **Standby Mode Correct?** - XOSC before TX
  - Use STDBY_RC for initialization
  - Switch to STDBY_XOSC before SetTx()
  - Return to STDBY_RC after TX for power saving

- [ ] **CalibrateImage Called?** - After frequency set
  - Must be called after SetRfFrequency
  - Must complete before SetTx
  - Use extended timeout (3000ms)

- [ ] **Frequency Set Before Calibration?** - Correct order
  - SetRfFrequency BEFORE CalibrateImage
  - CalibrateImage requires frequency to be set

- [ ] **PA Config Valid?** - Correct for SX1262
  - For 14dBm: [0x04, 0x00, 0x01, 0x01]
  - For higher power: [0x04, 0x07, 0x00, 0x01]
  - Device select: 0x01 (SX1262)

- [ ] **Power Register Correct?** - Non-linear mapping
  - 14dBm = 0x04 (not 0x08)
  - Use power_map dictionary

- [ ] **Delays Added?** - Required timing
  - 5ms after XOSC standby switch
  - 10ms after CalibrateImage
  - 1ms after payload length set
  - 10ms after SetTx for mode transition

- [ ] **BUSY Timeouts Extended?** - For long operations
  - SetTx: 5000ms
  - SetRx: 3000ms
  - CalibrateImage: 3000ms
  - Calibrate: 2000ms

- [ ] **Device Errors Cleared?** - Before critical operations
  - After CalibrateImage
  - Before SetTx
  - After any error condition

## Minimal TX-Only Example (MicroPython)

```python
from machine import SPI, Pin
import time
from sx1262 import SX1262, SF_7, BW_125, CR_4_5

# Initialize SPI and pins
spi = SPI(1, baudrate=2000000, polarity=0, phase=0, bits=8, firstbit=SPI.MSB)
cs = Pin("P3", Pin.OUT, value=1)
busy = Pin("P7", Pin.IN)
reset = Pin("P13", Pin.OUT, value=1)
dio1 = Pin("P6", Pin.IN)

# Initialize radio
radio = SX1262(spi, cs, busy, reset, dio1, freq=868000000)

# Configure (includes all required steps)
radio.configure(
    frequency=868000000,
    sf=SF_7,
    bw=BW_125,
    cr=CR_4_5,
    tx_power=14,
    preamble_length=12,
    payload_length=0
)

# Send packet
message = "HELLO_OPENMV"
success = radio.send(message, timeout_ms=5000)

if success:
    print("TX successful")
else:
    print("TX failed")
    # Read errors for debugging
    errors = radio.get_device_errors()
    print(f"Device errors: 0x{errors:04X}")
```

## References

1. **ST Community - SX1262 TX Timeout**
   - https://community.st.com/t5/stm32-mcus-wireless/lora-sx1262-tx-timeout/td-p/213681
   - Issue: TX timeout, BUSY stuck
   - Solution: TCXO configuration required, XOSC standby before TX

2. **MicroPython GitHub - SX1262 OpError 0x20**
   - https://github.com/micropython/micropython-lib/issues/870
   - Issue: Error 0x0020 after SetTx
   - Solution: CalibrateImage required, device errors must be cleared

3. **MicroPython Discussion - TCXO Config**
   - https://github.com/orgs/micropython/discussions/13619
   - Issue: 0x20 caused by missing TCXO config
   - Solution: SetDio3AsTcxoCtrl must be called

4. **RadioLib - SX1262 BUSY & IRQ Behavior**
   - https://github.com/jgromes/RadioLib/issues/49
   - Issue: BUSY timeout, IRQ not firing
   - Solution: Extended timeouts, proper IRQ configuration

5. **Reddit - SX1262 SetTx Never Works**
   - https://www.reddit.com/r/embedded/comments/1jid62f/
   - Issue: SetTx() never enters TX mode
   - Solution: TCXO/DIO3 configuration, XOSC standby, CalibrateImage

6. **SX1262 Datasheet (Semtech)**
   - Section 13.2: CalibrateImage command
   - Section 13.3: DIO3 as TCXO control
   - Section 13.4: DIO2 as RF switch control
   - Section 15.1: Command execution errors
   - Section 6.2: Standby modes (RC vs XOSC)

7. **LoRaMac-node Reference**
   - `src/boards/rp2040/sx126x-board.c`
   - `SX126xIoTcxoInit()` - TCXO initialization pattern
   - `SX126xIoRfSwitchInit()` - RF switch initialization
   - CalibrateImage called after frequency set

## Expected vs Actual Behavior

### Expected (Working):
```
[TX] Switching to XOSC standby...
[TX] Chip mode: 1 (STDBY_XOSC) ✓
[TX] Device errors: 0x0000 ✓
[TX] Writing buffer... ✓
[TX] Setting payload length... ✓
[TX] Starting TX...
[TX] BUSY: HIGH (processing)
[TX] BUSY: LOW (ready)
[TX] Chip mode: 3 (TX) ✓
[TX] Polling IRQ...
[TX] IRQ: 0x0001 (TX_DONE) ✓
[TX] ✓ TX successful
```

### Actual (Current Issue):
```
[TX] Switching to XOSC standby...
[TX] Chip mode: 1 (STDBY_XOSC) ✓
[TX] Device errors: 0x0020 ✗
[TX] Writing buffer... ✓
[TX] Setting payload length... ✓
[TX] Starting TX...
[TX] BUSY: LOW (command rejected)
[TX] Chip mode: 1 (STDBY_XOSC) ✗ (should be 3)
[TX] Polling IRQ...
[TX] IRQ: 0x0000 (no flags) ✗
[TX] ✗ TX failed - timeout
```

## Key Differences

1. **Device errors present** (0x0020) - indicates previous command failure
2. **BUSY stays LOW** - command rejected immediately, not processing
3. **Chip mode = 1** - stayed in STDBY_XOSC, didn't enter TX mode
4. **IRQ = 0x0000** - no TX_DONE because TX never started

## Solution Summary

The fixes implemented address:
1. ✅ Extended BUSY timeout for CalibrateImage (prevents configure() failure)
2. ✅ Extended BUSY timeout for SetTx (allows for TCXO + calibration)
3. ✅ XOSC standby before TX (stable reference)
4. ✅ Device error clearing before SetTx (removes stale errors)
5. ✅ Chip state validation before/after SetTx (detects failures early)
6. ✅ Proper command sequence (frequency before CalibrateImage)

After these fixes, the chip should:
- Complete CalibrateImage without timeout
- Enter TX mode successfully (chip_mode = 3)
- Set BUSY HIGH during TX processing
- Fire TX_DONE IRQ after transmission
- Clear error 0x0020

