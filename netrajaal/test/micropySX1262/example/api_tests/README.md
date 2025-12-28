# API Test Examples

This directory contains comprehensive test examples for all SX1262 API methods. Each example demonstrates specific functionality and can be run independently.

## Test Files

### 01_initialization.py
Tests the SX1262 constructor and `begin()` method with various configurations:
- Basic initialization
- Custom SPI settings
- Different frequency bands
- Different spreading factors
- Different bandwidths
- Different TX power levels

**Usage**: Run this to verify your hardware setup and basic configuration.

### 02_transmission.py
Tests the `send()` method with different data types and sizes:
- String data
- Bytes and bytearray
- Small packets (1 byte)
- Medium packets (100 bytes)
- Large packets (254 bytes - max)
- Structured data (JSON)
- Binary data
- Continuous transmission

**Usage**: Run this to test transmission functionality. Requires a receiver to verify.

### 03_reception.py
Tests the `recv()` method with various parameters:
- Blocking receive (no timeout)
- Receive with timeout
- Receive with expected length
- Continuous reception loop
- RSSI and SNR information

**Usage**: Run this to test reception functionality. Requires a transmitter sending data.

### 04_configuration.py
Tests all configuration methods:
- `setFrequency()` - Change frequency
- `setOutputPower()` - Change TX power
- `setSpreadingFactor()` - Change SF
- `setBandwidth()` - Change BW
- `setCodingRate()` - Change CR
- `setPreambleLength()` - Change preamble
- `setSyncWord()` - Change sync word
- Combined configuration changes

**Usage**: Run this to test dynamic configuration changes.

### 05_status_info.py
Tests status and information methods:
- `getRSSI()` - Get received signal strength
- `getSNR()` - Get signal-to-noise ratio
- `getTimeOnAir()` - Calculate time on air for different packet sizes
- `getTimeOnAir()` with different SF and BW configurations

**Usage**: Run this to understand signal quality metrics and transmission timing.

### 06_power_management.py
Tests power management methods:
- `sleep()` with retainConfig=True (warm sleep)
- `sleep()` with retainConfig=False (cold sleep)
- `standby()` - Standby mode
- Wake up from sleep
- Periodic transmission with sleep
- Power consumption comparison
- Sleep/wake timing

**Usage**: Run this to test power-saving features for battery-powered applications.

### 07_blocking_modes.py
Tests blocking and non-blocking modes:
- Blocking mode (default)
- Non-blocking mode without callback
- Non-blocking mode with callback
- Switching between modes
- Event handling

**Usage**: Run this to understand blocking vs non-blocking operation modes.

**Understanding Blocking vs Non-Blocking Modes**:

**Blocking Mode** (Default):
- When you call `send()` or `recv()`, your program **waits** until the operation completes
- `send()` blocks until the packet is fully transmitted
- `recv()` blocks until a packet is received or timeout occurs
- Simple to use - your code waits for completion before continuing
- Best for: Simple applications where you can wait for operations to complete

**Non-Blocking Mode**:
- When you call `send()` or `recv()`, your program **returns immediately** without waiting
- `send()` starts transmission and returns right away (transmission continues in background)
- `recv()` returns immediately (you need to check status to see if data was received)
- Allows your program to do other tasks while radio operations happen in background
- Can use callbacks to be notified when operations complete
- Best for: Applications that need to do other tasks while radio is working

**How to Know When Non-Blocking Operations Complete**:

**Method 1: Using Callbacks (Recommended)**:
- Set up a callback function when enabling non-blocking mode
- The callback is automatically called when TX_DONE or RX_DONE events occur
- Example:
  ```python
  def my_callback(events):
      if events & SX1262.TX_DONE:
          print("Transmission complete - ready for next TX")
      if events & SX1262.RX_DONE:
          print("Packet received - ready to read data")
  
  sx.setBlockingCallback(blocking=False, callback=my_callback)
  sx.send(b"Hello")  # Returns immediately, callback called when done
  ```

**Method 2: Polling DIO1 Pin (P13)**:
- DIO1 pin goes HIGH when TX_DONE or RX_DONE event occurs
- Check the pin status in your main loop
- When pin is HIGH, operation is complete
- Example:
  ```python
  from machine import Pin
  irq_pin = Pin('P13', Pin.IN)
  
  sx.setBlockingCallback(blocking=False)
  sx.send(b"Hello")  # Returns immediately
  
  # Do other tasks in your main loop...
  while True:
      # Check if operation completed
      if irq_pin.value():
          # Operation complete - ready for next TX/RX
          print("Ready for next operation")
          break
      # Continue doing other tasks
      time.sleep(0.1)
  ```

**Important Notes**:
- After TX_DONE: You can immediately send another packet
- After RX_DONE: Call `recv()` to read the received data, then you can receive again
- Always check the status code returned by `send()` or `recv()` to ensure operation started successfully
- In non-blocking mode, the radio automatically starts receiving after TX_DONE (if configured)

