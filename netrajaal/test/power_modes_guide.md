# OpenMV RT1062 Power Modes Guide

## Power Modes Overview

The OpenMV RT1062 offers several power modes to optimize energy consumption:

### 1. **Active Mode** (Normal Operation)
- **Power Consumption**: ~130mA at 5V (~650mW)
- **State**: Full CPU and peripheral operation
- **Use Case**: Normal camera/image processing operations
- **Wake-up**: N/A (already awake)

### 2. **Idle Mode**
- **Power Consumption**: Moderate reduction (~50-80mA)
- **State**: CPU halts, peripherals remain active
- **RAM**: Maintained
- **Wake-up**: Immediate (via interrupt or timer)
- **Use Case**: Short pauses, waiting for events
- **Limitation**: Doesn't significantly reduce power

### 3. **Light Sleep Mode** (`machine.lightsleep()`)
- **Power Consumption**: ~10-30mA (significant reduction)
- **State**: CPU and most peripherals stopped
- **RAM**: **Maintained** (all variables preserved)
- **Wake-up Sources**: 
  - RTC alarm
  - External interrupts (GPIO pins)
  - Timer interrupts
- **Wake-up Time**: Very fast (< 1ms)
- **Code Continuity**: Execution resumes after `lightsleep()` call
- **Use Case**: Periodic wake-ups, maintaining state between operations
- **Best For**: Applications needing to preserve RAM state

### 4. **Deep Sleep Mode** (`machine.deepsleep()`)
- **Power Consumption**: **< 30µA** when powered via battery connector (lowest power)
- **State**: Most components shut down, only RTC and essential circuits active
- **RAM**: **Lost** (all variables cleared)
- **Wake-up Sources**:
  - RTC alarm
  - External interrupts (GPIO pins)
  - Reset button
- **Wake-up Time**: Module resets (~100-200ms)
- **Code Continuity**: Module resets, code starts from beginning
- **Use Case**: Long-term battery operation, minimal power consumption
- **Best For**: Very low power applications, external interrupt wake-up

## Key Differences: Light Sleep vs Deep Sleep

| Feature | Light Sleep | Deep Sleep |
|---------|-------------|------------|
| **Power Consumption** | ~10-30mA | **< 30µA** |
| **RAM State** | ✅ Preserved | ❌ Lost (reset) |
| **Wake-up Time** | < 1ms | ~100-200ms (reset) |
| **Code Continuity** | ✅ Continues after sleep | ❌ Restarts from beginning |
| **State Variables** | ✅ Maintained | ❌ Need to be saved/restored |
| **Best For** | Periodic tasks, state preservation | **Ultra-low power, external triggers** |

## Power Consumption Comparison

```
Active Mode:     ~130mA  (650mW)  ████████████████████████████████████████
Idle Mode:       ~60mA   (300mW)  ████████████████
Light Sleep:     ~20mA   (100mW)  ██████
Deep Sleep:      < 30µA  (< 0.15mW) ▏ (barely visible!)
```

## Optimal Strategy for Very Low Power + External Interrupt Wake-up

### **Recommended: Deep Sleep Mode**

**Why Deep Sleep?**
1. **Lowest Power**: < 30µA (1000x lower than light sleep!)
2. **External Interrupt Support**: GPIO pins can wake the module
3. **Battery Life**: Can run for months/years on battery
4. **Perfect for**: Sensor monitoring, event-triggered applications

### Implementation Strategy

1. **Power Source**: Use battery connector for lowest power in deep sleep
2. **External Interrupt**: Configure GPIO pin as wake-up source
3. **State Management**: Save critical data to flash before sleep
4. **Wake-up Handling**: Check wake-up reason on boot
5. **Re-enter Sleep**: After processing, immediately re-enter deep sleep

### Wake-up Sources Available

- **External Interrupt (GPIO)**: Pin state change (rising/falling edge)
- **RTC Alarm**: Time-based wake-up
- **Reset Button**: Manual wake-up

## Other Considerations

### Power Source Impact
- **USB Power**: Higher power consumption even in sleep (~1-5mA)
- **Battery Connector**: Lowest power consumption (< 30µA in deep sleep)
- **For minimal power**: Always use battery connector

### Peripheral Management
- Disable unused peripherals before sleep
- Turn off LEDs
- Disable camera sensor
- Disable WiFi/Bluetooth if present

### State Preservation in Deep Sleep
Since deep sleep loses RAM:
- Save critical data to flash memory
- Use `pyb.Flash()` or file system
- Restore state on wake-up
- Use RTC to track time across resets

