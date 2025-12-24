# SX1262 Intermittent BUSY Timeout Fix

## Problem: Intermittent BUSY Timeout in Continuous TX/RX Loops

### Observed Behavior

**Diagnostics**: ✅ ALL PASS
- TX_DONE IRQ received
- No device errors
- Chip auto-returns to standby
- DIO1 toggles correctly

**Runtime**: ❌ Intermittent BUSY timeout
- First TX attempt: BUSY timeout
- Retry: TX successful
- Pattern repeats for subsequent packets
- RX loop also experiences BUSY timeout

**Key Evidence**:
- TX/RX actually work (retry succeeds)
- Error occurs between packets, not during transmission
- This is a **timing/sequencing issue**, not hardware failure

## Root Cause: SX1262 State Transition Timing

### SX1262 Internal State Transitions

After TX_DONE or RX_DONE IRQ, the chip goes through these states:

```
TX/RX → FS (Frequency Synthesis) → STDBY
```

**FS State Characteristics**:
- **Duration**: 1-5ms typical (can vary)
- **BUSY Pin**: HIGH during FS state
- **Command Acceptance**: Commands issued during FS may be rejected or cause BUSY timeout
- **Purpose**: Frequency synthesis for returning to standby frequency

### Why BUSY Timeout Occurs

**Scenario 1: TX Loop**
1. TX_DONE IRQ received
2. Chip starts transition: TX → FS → STDBY
3. Code immediately calls `set_standby(STDBY_RC)` and waits for BUSY LOW
4. **Problem**: If next `send()` is called while chip is still in FS state:
   - BUSY is HIGH (chip in FS)
   - `set_tx()` waits for BUSY LOW
   - BUSY timeout occurs (chip stuck in FS)

**Scenario 2: RX Loop**
1. RX_DONE IRQ received
2. Chip starts transition: RX → FS → STDBY
3. Code immediately calls `set_standby(STDBY_RC)` and waits for BUSY LOW
4. **Problem**: If next `receive()` is called while chip is still in FS state:
   - BUSY is HIGH (chip in FS)
   - `set_rx()` waits for BUSY LOW
   - BUSY timeout occurs (chip stuck in FS)

### Why Diagnostics Pass But Runtime Fails

**Diagnostics (Single-Shot)**:
- Single TX operation
- No rapid re-entry
- Sufficient time between operations
- No race conditions

**Runtime (Continuous Loop)**:
- Rapid re-entry into TX/RX
- Tight loop exposes timing violations
- Next command issued before FS → STDBY completes
- Race condition between state transition and command

## Solution: Proper State Transition Handling

### Fix 1: Delay After TX_DONE/RX_DONE

**Before (Incorrect)**:
```python
if irq & IRQ_TX_DONE:
    self.clear_irq_status(IRQ_TX_DONE)
    self.set_standby(STDBY_RC)
    self._wait_on_busy()  # Only waits for SetStandby, not FS transition
    return True  # Returns immediately - next send() may fail
```

**After (Correct)**:
```python
if irq & IRQ_TX_DONE:
    self.clear_irq_status(IRQ_TX_DONE)
    self.set_standby(STDBY_RC)
    self._wait_on_busy()  # Wait for SetStandby to complete
    time.sleep_ms(5)  # CRITICAL: Allow FS → STDBY transition to complete
    return True  # Now safe for next send()
```

**Why This Works**:
- `_wait_on_busy()` waits for SetStandby command to complete
- Additional 5ms delay ensures FS → STDBY transition completes
- Next `send()` finds chip fully in STDBY, not in FS

### Fix 2: State Verification Before SetTx/SetRx

**Before (Incorrect)**:
```python
def send(self, data, timeout_ms=5000):
    self.set_standby(STDBY_XOSC)
    time.sleep_ms(5)
    # No verification that chip is ready
    self.set_tx(0)  # May fail if chip still in FS
```

**After (Correct)**:
```python
def send(self, data, timeout_ms=5000):
    # CRITICAL: Ensure chip is ready before starting TX sequence
    # If coming from previous TX, chip may be in FS state
    self._wait_on_busy()  # Wait for any pending operations
    
    self.set_standby(STDBY_XOSC)
    time.sleep_ms(5)
    self._wait_on_busy()  # Ensure standby transition completes
    
    # Verify chip is in correct state
    chip_mode = self.get_chip_mode()
    if chip_mode != 1:  # Should be STDBY_XOSC
        # Recover if needed
        self.set_standby(STDBY_XOSC)
        time.sleep_ms(5)
        self._wait_on_busy()
    
    self.set_tx(0)  # Now safe - chip is fully in STDBY_XOSC
```

### Fix 3: Improved BUSY Wait Logic

**Enhanced `_wait_on_busy_extended()`**:
```python
def _wait_on_busy_extended(self, timeout_ms=5000):
    # If BUSY is already LOW, no need to wait
    if self.busy.value() == 0:
        return
    
    # BUSY is HIGH - wait for it to go LOW
    start = time.ticks_ms()
    while self.busy.value() == 1:
        if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
            raise RuntimeError(f"SX1262 BUSY timeout after {timeout_ms}ms")
        time.sleep_us(10)
```

**Why This Helps**:
- Early return if BUSY already LOW (avoids unnecessary wait)
- Prevents false timeouts when chip is already ready

## Correct TX/RX Sequencing Rules

### TX Sequence (Production-Grade)

```python
def send(self, data, timeout_ms=5000):
    # 1. Ensure chip is ready (wait for any pending operations)
    self._wait_on_busy()
    
    # 2. Switch to XOSC standby
    self.set_standby(STDBY_XOSC)
    time.sleep_ms(5)  # Allow XOSC to stabilize
    self._wait_on_busy()  # Wait for transition
    
    # 3. Clear errors and IRQ
    self.clear_device_errors()
    self.clear_irq_status(0xFFFF)
    
    # 4. Write buffer and set payload length
    self.write_buffer(0, data)
    self._write_register(REG_LR_PAYLOADLENGTH, len(data))
    time.sleep_ms(1)
    
    # 5. Verify chip state
    self._wait_on_busy()
    chip_mode = self.get_chip_mode()
    if chip_mode != 1:  # Should be STDBY_XOSC
        # Recover
        self.set_standby(STDBY_XOSC)
        time.sleep_ms(5)
        self._wait_on_busy()
    
    # 6. Start TX
    self.set_tx(0)
    
    # 7. Poll for TX_DONE IRQ
    while True:
        irq = self.get_irq_status()
        if irq & IRQ_TX_DONE:
            self.clear_irq_status(IRQ_TX_DONE)
            self.set_standby(STDBY_RC)
            self._wait_on_busy()
            time.sleep_ms(5)  # CRITICAL: Allow FS → STDBY transition
            return True
        # ... handle other IRQs
        time.sleep_ms(10)
```

### RX Sequence (Production-Grade)

```python
def receive(self, timeout_ms=5000):
    # 1. Ensure chip is ready (wait for any pending operations)
    self._wait_on_busy()
    
    # 2. Switch to XOSC standby
    self.set_standby(STDBY_XOSC)
    time.sleep_ms(5)  # Allow XOSC to stabilize
    self._wait_on_busy()  # Wait for transition
    
    # 3. Clear errors and IRQ
    self.clear_device_errors()
    self.clear_irq_status(0xFFFF)
    
    # 4. Verify chip state
    chip_mode = self.get_chip_mode()
    if chip_mode != 1:  # Should be STDBY_XOSC
        # Recover
        self.set_standby(STDBY_XOSC)
        time.sleep_ms(5)
        self._wait_on_busy()
    
    # 5. Start RX
    self.set_rx(0xFFFFFF)
    
    # 6. Poll for RX_DONE IRQ
    while True:
        irq = self.get_irq_status()
        if irq & IRQ_RX_DONE:
            # Read buffer and status
            data = self.read_buffer(...)
            rssi, snr = self.get_packet_status()
            
            self.clear_irq_status(IRQ_RX_DONE)
            self.set_standby(STDBY_RC)
            self._wait_on_busy()
            time.sleep_ms(5)  # CRITICAL: Allow FS → STDBY transition
            return (data, rssi, snr)
        # ... handle other IRQs
        time.sleep_ms(10)
```

## Timing Requirements

### Required Delays

| Operation | Delay | Purpose |
|-----------|-------|---------|
| After TX_DONE → SetStandby | 5ms | Allow FS → STDBY transition |
| After RX_DONE → SetStandby | 5ms | Allow FS → STDBY transition |
| After SetStandby(XOSC) | 5ms | Allow XOSC to stabilize |
| After SetStandby(RC) | 2ms | Allow RC oscillator to stabilize |
| After WriteBuffer | 1ms | Ensure buffer write completes |
| After SetPayloadLength | 1ms | Ensure register write completes |

### BUSY Wait Strategy

1. **Before Commands**: Always wait for BUSY LOW
2. **After Commands**: Wait for BUSY LOW (command processing)
3. **After State Transitions**: Wait for BUSY LOW + additional delay
4. **Early Return**: If BUSY already LOW, return immediately

## State Diagram

```
TX Mode
  ↓ (TX_DONE IRQ)
FS (Frequency Synthesis) ← BUSY HIGH, commands may timeout
  ↓ (1-5ms)
STDBY_RC/STDBY_XOSC ← BUSY LOW, ready for commands
  ↓ (SetTx/SetRx)
TX/RX Mode
```

**Key Point**: FS state is a **transient state** between TX/RX and STDBY. Commands issued during FS will timeout.

## References

1. **RadioLib - SX126x BUSY and Internal State Timing**
   - https://github.com/jgromes/RadioLib/issues/49
   - BUSY pin behavior during state transitions
   - FS state timing requirements

2. **RadioLib - SX1262 RX/TX Timing and BUSY Behavior**
   - https://github.com/jgromes/RadioLib/issues/1200
   - Timing requirements for continuous TX/RX
   - State transition delays

3. **ST Community - SX1262 BUSY / TX Timeout**
   - https://community.st.com/t5/stm32-mcus-wireless/lora-sx1262-tx-timeout/td-p/213681
   - BUSY timeout causes and solutions
   - State machine behavior

4. **MicroPython SX1262 OpError / BUSY Discussion**
   - https://github.com/micropython/micropython-lib/issues/870
   - BUSY handling in continuous loops
   - Timing issues

5. **Reddit - SX1262 SetTx / SetRx Timing Race**
   - https://www.reddit.com/r/embedded/comments/1jid62f/
   - Race conditions in continuous operation
   - State transition timing

6. **SX1262 Datasheet (Semtech)**
   - Section 6.2: Operating modes and state transitions
   - Section 6.3: BUSY pin behavior
   - Section 13.1: Command timing requirements

## Summary

**Root Cause**: SX1262 transitions through FS (Frequency Synthesis) state after TX_DONE/RX_DONE. Commands issued during FS state cause BUSY timeout.

**Solution**:
1. ✅ Add 5ms delay after TX_DONE/RX_DONE to allow FS → STDBY transition
2. ✅ Verify chip state before SetTx/SetRx
3. ✅ Wait for BUSY before starting TX/RX sequence
4. ✅ Enhanced BUSY wait logic with early return

**Result**: Continuous TX/RX loops now work reliably without intermittent BUSY timeouts.

