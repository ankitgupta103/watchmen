# SX1262 Chip Mode Decoding Fix

## Problem: False TX Failure Report

### Observed Behavior (TX Actually Successful)

```
[Step 7] Starting TX...
Chip mode after TX: 1 (STDBY_XOSC)
✗ Chip did not enter TX mode (mode=1, BUSY=0)

[Step 8] Monitoring IRQ status...
✓ TX_DONE IRQ received after 31ms (4 polls)
✓ IRQ status: 0x0001
```

**Analysis**: TX is **SUCCESSFUL** - TX_DONE IRQ is definitive proof. The test incorrectly reports failure because it checks chip mode AFTER TX completion.

## Root Cause: Incorrect Chip Mode Decoding

### Wrong Decoding (Previous Implementation)

```python

chip_mode = (status >> 6) & 0x03  # WRONG
```

**Problem**: This reads bits [7:6], which are **Command Status** bits, not Chip Mode.

### Correct Decoding (SX1262 Datasheet)

**Status Byte Format** (from SX1262 datasheet):
- Bits [7:4]: Command Status
- Bits [3:1]: Chip Mode
- Bit [0]: Reserved

**Correct Decoding**:
```python
chip_mode = (status >> 1) & 0x07
```

### Valid Chip Modes

| Mode Value | Name | Description |
|------------|------|-------------|
| 0 | STDBY_RC | Standby with RC oscillator |
| 1 | STDBY_XOSC | Standby with crystal oscillator |
| 2 | FS | Frequency Synthesis |
| 3 | RX | Receive mode |
| 4 | TX | Transmit mode |

**Note**: TX mode = 4, NOT 3!

## Why "Chip Not in TX" Is NOT an Error

### SX1262 TX Behavior (From Semtech Datasheet)

1. **SetTx() Command**:
   - Chip enters TX mode (mode = 4)
   - Starts transmission
   - BUSY goes HIGH during TX

2. **During TX**:
   - Chip is in TX mode (mode = 4)
   - RF signal is transmitted
   - Duration depends on packet size and LoRa parameters

3. **After TX Completion**:
   - Chip **automatically** sets TX_DONE IRQ
   - Chip **automatically** returns to standby mode
   - BUSY goes LOW
   - Chip mode = 0 (STDBY_RC) or 1 (STDBY_XOSC)

**Key Point**: SX1262 does NOT stay in TX mode after transmission completes. Reading chip mode after TX_DONE will show STDBY, not TX. This is **expected behavior**, not an error.

### Why TX Completes Before Mode Check

For a short packet (12 bytes) with SF7, BW125:
- Packet transmission time: ~20-30ms
- Polling interval: 10ms
- TX may complete between SetTx() and first IRQ poll
- Chip mode check after TX_DONE will show STDBY

**This is normal and expected!**

## Correct TX Success Criteria

### ✅ TX is Successful If:

1. **SetTx() returns without BUSY timeout**
   - Command accepted by chip
   - No immediate rejection

2. **IRQ_TX_DONE is received**
   - **This is definitive proof of successful transmission**
   - Chip sets this flag automatically after TX completes

3. **No device errors**
   - Error register = 0x0000
   - No command execution failures

4. **DIO1 toggles (optional confirmation)**
   - IRQ configured correctly
   - Hardware connection verified

### ❌ Do NOT Require:

1. **Chip to remain in TX mode**
   - Chip automatically returns to STDBY after TX
   - Checking mode after TX_DONE will show STDBY

2. **BUSY to stay HIGH**
   - BUSY goes LOW when TX completes
   - LOW BUSY after TX_DONE is normal

3. **Chip mode = 4 (TX) after TX_DONE**
   - Chip is already back in STDBY
   - This check will always fail for completed TX

## Correct TX Flow (Production-Grade)

### Complete TX Sequence

```python
# 1. Switch to XOSC standby (required for stable TX)
radio.set_standby(STDBY_XOSC)
time.sleep_ms(5)  # Allow XOSC to stabilize

# 2. Clear device errors
radio.clear_device_errors()

# 3. Clear IRQ flags
radio.clear_irq_status(0xFFFF)

# 4. Write payload to FIFO
radio.write_buffer(0, payload)

# 5. Set payload length (for variable length packets)
radio._write_register(REG_LR_PAYLOADLENGTH, len(payload))
time.sleep_ms(1)

# 6. Verify chip ready
radio._wait_on_busy()
chip_mode = radio.get_chip_mode()
if chip_mode != 1:  # Should be STDBY_XOSC
    radio.set_standby(STDBY_XOSC)
    time.sleep_ms(5)

# 7. Start TX
radio.set_tx(0)  # No timeout

# 8. Poll for TX_DONE IRQ (DO NOT check chip mode)
start = time.ticks_ms()
while True:
    irq = radio.get_irq_status()
    
    if irq & IRQ_TX_DONE:
        # TX SUCCESSFUL - this is the only check needed
        radio.clear_irq_status(IRQ_TX_DONE)
        radio.set_standby(STDBY_RC)  # Return to RC for power saving
        return True
    
    if irq & IRQ_RX_TX_TIMEOUT:
        # TX timeout
        radio.clear_irq_status(IRQ_RX_TX_TIMEOUT)
        radio.set_standby(STDBY_RC)
        return False
    
    if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
        # Software timeout
        radio.set_standby(STDBY_RC)
        return False
    
    time.sleep_ms(10)
```

### Why Each Step Matters

1. **XOSC Standby**: Provides stable frequency reference for TX
2. **Clear Errors**: Removes stale error flags that prevent commands
3. **Clear IRQ**: Ensures clean IRQ state
4. **Write Buffer**: Loads payload into FIFO
5. **Set Payload Length**: Required for variable length packets
6. **Verify Ready**: Ensures chip is ready before SetTx
7. **SetTx**: Starts transmission
8. **Poll IRQ**: Waits for TX_DONE (definitive success indicator)

## Fixed Diagnostic Test Logic

### Before (Incorrect):

```python
# Check chip mode after SetTx
chip_mode_after = (status >> 6) & 0x03  # WRONG decoding
if chip_mode_after == 3:  # WRONG - TX mode is 4, not 3
    # Success
else:
    # Failure - WRONG! Chip may have already completed TX
```

### After (Correct):

```python
# Start TX
radio.set_tx(0)

# Check chip mode immediately (informational only)
chip_mode_immediate = radio.get_chip_mode()  # Correct decoding
print(f"Chip mode: {chip_mode_immediate}")

# Poll for TX_DONE IRQ (this is the success criteria)
while True:
    irq = radio.get_irq_status()
    if irq & IRQ_TX_DONE:
        # TX SUCCESSFUL - this is definitive proof
        print("✓ TX successful")
        return True
    time.sleep_ms(10)
```

## References

1. **SX1262 Datasheet (Semtech)**:
   - Section 6.2: Status byte format
   - Bits [3:1] = Chip Mode
   - TX mode = 4 (not 3)

2. **RadioLib GitHub**:
   - https://github.com/jgromes/RadioLib/issues/49
   - Status byte decoding explanation
   - TX_DONE is definitive proof of TX success

3. **RadioLib GitHub**:
   - https://github.com/jgromes/RadioLib/issues/1200
   - SX1262 TX behavior and mode transitions
   - Chip automatically returns to standby after TX

4. **MicroPython GitHub**:
   - https://github.com/micropython/micropython-lib/issues/870
   - SX1262 internal state discussion
   - TX_DONE IRQ is the success indicator

5. **ST Community**:
   - https://community.st.com/t5/stm32-mcus-wireless/lora-sx1262-tx-timeout/td-p/213681
   - SX1262 TX behavior and mode transitions

6. **Reddit**:
   - https://www.reddit.com/r/embedded/comments/1jid62f/
   - TX completes before polling detects TX state

## Summary

**TX is successful** when:
- ✅ TX_DONE IRQ is received
- ✅ No device errors
- ✅ SetTx() completed without timeout

**TX is NOT determined by**:
- ❌ Chip mode after TX_DONE (will be STDBY)
- ❌ BUSY pin state after TX_DONE (will be LOW)
- ❌ Chip mode persistence (chip doesn't stay in TX)

**Fix Applied**:
1. ✅ Correct chip mode decoding: `(status >> 1) & 0x07`
2. ✅ Added `get_chip_mode()` helper method
3. ✅ Fixed diagnostic test to check TX_DONE IRQ, not chip mode
4. ✅ Removed incorrect chip mode check after TX_DONE

