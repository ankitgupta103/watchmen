import machine
import time

# === PIN SETUP FOR SPI BUS 1 ===
cs = machine.Pin('P3', machine.Pin.OUT)      # SPI Chip Select (SS)
reset = machine.Pin('P6', machine.Pin.OUT)   # Reset
busy = machine.Pin('P7', machine.Pin.IN)     # Busy status

# SPI setup - Bus 1 (pins P0=MOSI, P1=MISO, P2=SCK are automatic)
spi = machine.SPI(1, baudrate=1000000)

cs.on()     # CS high = not selected
reset.on()  # Reset high = normal operation

# === BASIC FUNCTIONS ===
def wait_ready():
    """Wait until SX1262 is ready"""
    while busy.value():
        time.sleep_us(10)

def send_command(cmd_data):
    """Send command to SX1262"""
    wait_ready()
    cs.off()
    spi.write(bytearray(cmd_data))
    cs.on()

def reset_chip():
    """Reset the LoRa chip"""
    reset.off()
    time.sleep_us(100)
    reset.on()
    time.sleep_ms(10)

# === CONFIGURATION FUNCTIONS ===
def init_lora(freq=868, speed="fast", power=22):
    """Initialize LoRa - shows configuration details"""
    print("🚀 Starting LoRa on SPI Bus 1...")
    print("📍 Pins: P0=MOSI, P1=MISO, P2=SCK, P3=CS, P6=RESET, P7=BUSY")
    
    # Reset and basic setup
    reset_chip()
    send_command([0x80])  # Standby
    print("✓ Standby mode")
    
    send_command([0x8A, 0x01])  # LoRa mode
    print("✓ LoRa mode")
    
    # Set frequency
    freq_hz = freq * 1000000
    freq_val = int(freq_hz * (2**25) / 32000000)
    send_command([0x86, (freq_val >> 24) & 0xFF, (freq_val >> 16) & 0xFF, 
                  (freq_val >> 8) & 0xFF, freq_val & 0xFF])
    print(f"✓ Frequency: {freq}MHz")
    
    # Set speed/modulation
    if speed == "fast":
        sf, bw, cr = 7, 0, 1
        rate = "5.5 kbps"
    elif speed == "slow":
        sf, bw, cr = 12, 0, 1
        rate = "0.3 kbps"
    else:  # medium
        sf, bw, cr = 9, 0, 1
        rate = "1.8 kbps"
    
    send_command([0x8B, sf, bw, cr, 0x00])
    print(f"✓ Speed: {speed} ({rate})")
    
    # Set power
    if power > 22:
        power = 22
    send_command([0x8E, power, 0x00, 0x01, 0x01])
    power_mw = round(10 ** (power / 10), 1)
    print(f"✓ Power: {power}dBm ({power_mw}mW)")
    
    # Set sync word (important for matching)
    send_command([0x98, 0x34, 0x44])  # SetSyncWord - both modules must match
    print("✓ Sync word: 0x3444")
    
    # Set buffer base addresses
    send_command([0x8F, 0x00, 0x00])  # TX base=0, RX base=0
    print("✓ Buffer addresses set")
    
    print("✅ LoRa ready!\n")

# === SEND FUNCTION ===
def send(message):
    """Send a message (string or bytes)"""
    # Convert to bytes if string
    if isinstance(message, str):
        data = message.encode('utf-8')
    else:
        data = message
    
    # Clear IRQ status first
    send_command([0x02, 0xFF, 0xFF])  # ClearIrqStatus
    
    # Set buffer address
    send_command([0x8F, 0x00, 0x00])
    
    # Write data to buffer
    wait_ready()
    cs.off()
    spi.write(bytearray([0x0E, 0x00] + list(data)))
    cs.on()
    
    # Set packet parameters
    send_command([0x8C, 0x00, len(data), 0x00, 0x00, 0x00])
    
    # Start transmission
    send_command([0x83, 0x00, 0x00, 0x00])
    
    # Wait for TX done
    time.sleep_ms(100)  # Give time for transmission
    
    print(f"📡 Sent: {len(data)} bytes")

# === RECEIVE FUNCTION ===
def receive():
    """Receive a message - returns message data or None"""
    try:
        # Get RX buffer status (don't set RX mode here)
        wait_ready()
        cs.off()
        spi.write(bytearray([0x13, 0x00]))
        response = bytearray(3)
        spi.readinto(response)
        cs.on()
        
        payload_length = response[1]
        rx_start_pointer = response[2]
        
        if payload_length > 0:
            print(f"📨 Found message: {payload_length} bytes at position {rx_start_pointer}")
            
            # Read the actual data
            wait_ready()
            cs.off()
            spi.write(bytearray([0x1E, rx_start_pointer]))
            message_data = bytearray(payload_length)
            spi.readinto(message_data)
            cs.on()
            
            print(f"📨 Received: {len(message_data)} bytes")
            
            # Try to decode as text
            try:
                return message_data.decode('utf-8')
            except:
                return message_data  # Return as bytes if not text
        
        return None
        
    except Exception as e:
        print(f"❌ Receive error: {e}")
        return None

def start_continuous_receive():
    """Start continuous receive mode - call this once, then use receive()"""
    send_command([0x82, 0x00, 0x00, 0x00])  # Continuous RX mode
    print("📡 Continuous receive mode started")

# === SIMPLE USAGE EXAMPLES ===
def test_simple_send():
    """Simple test - send small message"""
    init_lora(freq=868, speed="fast", power=22)
    
    counter = 0
    while True:
        counter += 1
        message = f"Test #{counter}"
        send(message)
        print(f"Sent: {message}")
        time.sleep(2)

def test_simple_receive():
    """Simple test - receive any message"""
    init_lora(freq=868, speed="fast", power=22)
    
    print("📡 Waiting for messages... (send test_simple_send from other module)")
    
    while True:
        # Set RX mode
        send_command([0x82, 0x00, 0x00, 0x00])
        time.sleep_ms(500)  # Wait longer
        
        message = receive()
        if message:
            print(f"SUCCESS! Received: {message}")
        else:
            print(".", end="")  # Show we're checking
            
        time.sleep_ms(100)

def transmitter_example():
    """Example: Send 240-byte messages every 5 seconds"""
    init_lora(freq=868, speed="fast", power=22)
    
    counter = 0
    while True:
        counter += 1
        # Create exactly 240-byte message
        message = f"Data packet #{counter:03d}: " + "X" * 220
        message = message[:240]  # Ensure exactly 240 bytes
        
        send(message)
        time.sleep(5)

# === DIAGNOSTIC FUNCTIONS ===
def test_hardware_connections():
    """Test if hardware connections are working"""
    print("🔧 HARDWARE CONNECTION TEST")
    print("=" * 40)
    
    # Test reset pin
    print("1. Testing RESET pin (P6)...")
    reset.off()
    time.sleep_ms(10)
    reset.on()
    time.sleep_ms(100)
    print("   ✓ Reset pin toggled")
    
    # Test busy pin
    print("2. Testing BUSY pin (P7)...")
    busy_state = busy.value()
    print(f"   BUSY pin state: {busy_state} {'(HIGH - chip busy)' if busy_state else '(LOW - chip ready)'}")
    
    # Test CS pin
    print("3. Testing CS pin (P3)...")
    cs.off()
    time.sleep_ms(1)
    cs.on()
    print("   ✓ CS pin toggled")
    
    # Test basic SPI communication
    print("4. Testing SPI communication...")
    try:
        wait_ready()
        cs.off()
        # Try to read chip status
        spi.write(bytearray([0xC0, 0x00]))
        response = bytearray(2)
        spi.readinto(response)
        cs.on()
        
        print(f"   SPI Response: {[hex(b) for b in response]}")
        if response[0] == 0xC0:
            print("   ✓ SPI communication working!")
            status = response[1]
            print(f"   Chip status: 0x{status:02X}")
            return True
        else:
            print("   ❌ SPI response unexpected")
            return False
            
    except Exception as e:
        print(f"   ❌ SPI error: {e}")
        return False

def simple_transmitter():
    """Very simple transmitter for testing"""
    print("📡 SIMPLE TRANSMITTER TEST")
    
    # Test hardware first
    if not test_hardware_connections():
        print("❌ Hardware test failed - check connections!")
        return
    
    # Simple init
    print("\n🚀 Initializing...")
    reset_chip()
    send_command([0x80])  # Standby
    send_command([0x8A, 0x01])  # LoRa mode
    
    # Set frequency to 868MHz
    freq_val = int(868000000 * (2**25) / 32000000)
    send_command([0x86, (freq_val >> 24) & 0xFF, (freq_val >> 16) & 0xFF, 
                  (freq_val >> 8) & 0xFF, freq_val & 0xFF])
    
    # Simple modulation (SF7, 125kHz, 4/5)
    send_command([0x8B, 7, 0, 1, 0x00])
    
    # Power 14dBm
    send_command([0x8E, 14, 0x00, 0x01, 0x01])
    
    print("✓ Basic setup complete")
    
    # Send simple messages
    counter = 0
    while True:
        counter += 1
        message = f"Test{counter}"
        
        # Send message
        data = message.encode('utf-8')
        send_command([0x8F, 0x00, 0x00])  # Set buffer
        
        wait_ready()
        cs.off()
        spi.write(bytearray([0x0E, 0x00] + list(data)))
        cs.on()
        
        send_command([0x8C, 0x00, len(data), 0x00, 0x00, 0x00])  # Packet params
        send_command([0x83, 0x00, 0x00, 0x00])  # Start TX
        
        print(f"📡 Sent: {message} ({len(data)} bytes)")
        time.sleep(2)

def simple_receiver():
    """Very simple receiver for testing"""
    print("📡 SIMPLE RECEIVER TEST")
    
    # Test hardware first
    if not test_hardware_connections():
        print("❌ Hardware test failed - check connections!")
        return
    
    # Simple init (same as transmitter)
    print("\n🚀 Initializing...")
    reset_chip()
    send_command([0x80])  # Standby
    send_command([0x8A, 0x01])  # LoRa mode
    
    # Set frequency to 868MHz
    freq_val = int(868000000 * (2**25) / 32000000)
    send_command([0x86, (freq_val >> 24) & 0xFF, (freq_val >> 16) & 0xFF, 
                  (freq_val >> 8) & 0xFF, freq_val & 0xFF])
    
    # Simple modulation (SF7, 125kHz, 4/5)
    send_command([0x8B, 7, 0, 1, 0x00])
    
    # Power 14dBm
    send_command([0x8E, 14, 0x00, 0x01, 0x01])
    
    print("✓ Basic setup complete")
    print("📡 Listening for messages...")
    
    while True:
        # Set RX mode
        send_command([0x82, 0x00, 0x00, 0x00])  # Continuous RX
        
        # Wait and check buffer
        time.sleep(1)
        
        # Check buffer status
        wait_ready()
        cs.off()
        spi.write(bytearray([0x13, 0x00]))
        response = bytearray(3)
        spi.readinto(response)
        cs.on()
        
        payload_length = response[1]
        
        if payload_length > 0:
            print(f"📨 Found {payload_length} bytes!")
            
            # Read data
            wait_ready()
            cs.off()
            spi.write(bytearray([0x1E, 0x00]))
            data = bytearray(payload_length)
            spi.readinto(data)
            cs.on()
            
            try:
                message = data.decode('utf-8')
                print(f"✅ Received: {message}")
            except:
                print(f"✅ Received: {[hex(b) for b in data]}")
        else:
            print(".", end="")  # Show we're checking
    """Check if chip is responding properly"""
    wait_ready()
    cs.off()
    spi.write(bytearray([0xC0, 0x00]))  # GetStatus
    response = bytearray(2)
    spi.readinto(response)
    cs.on()
    
    status = response[1]
    chip_mode = (status >> 4) & 0x07
    cmd_status = (status >> 1) & 0x07
    
    modes = ["", "RFU", "STDBY_RC", "STDBY_XOSC", "FS", "RX", "TX", "RFU"]
    print(f"📊 Chip Status: 0x{status:02X} - Mode: {modes[chip_mode]} ({chip_mode})")
    
    return status

def receiver_example():
    """Example: Continuously receive messages"""
    init_lora(freq=868, speed="fast", power=22)
    
    print("📡 Starting receiver...")
    print("🔍 Testing chip communication first...")
    
    # Test chip communication
    check_chip_status()
    
    print("🔄 Checking for messages every 2 seconds...")
    
    while True:
        print("\n--- New receive cycle ---")
        
        # Check status before setting RX
        check_chip_status()
        
        # Clear any previous IRQ status
        send_command([0x02, 0xFF, 0xFF])  # ClearIrqStatus
        print("✓ IRQ cleared")
        
        # Set RX mode with timeout (2 seconds)
        send_command([0x82, 0x00, 0x1F, 0x40])  # SetRx with ~2 second timeout
        print("✓ RX mode set")
        
        # Check status after setting RX
        check_chip_status()
        
        # Wait for potential message or timeout
        time.sleep(2.5)
        
        # Check IRQ status
        wait_ready()
        cs.off()
        spi.write(bytearray([0x12, 0x00, 0x00]))
        irq_response = bytearray(3)
        spi.readinto(irq_response)
        cs.on()
        
        irq = (irq_response[1] << 8) | irq_response[2]
        print(f"📋 IRQ Status: 0x{irq:04X}")
        
        # Check final status
        final_status = check_chip_status()
        
        # Check if RX done (bit 1) or timeout (bit 9)
        if irq & 0x02:  # RX Done
            print("📨 RX Done detected!")
            message = receive()
            if message:
                print(f"SUCCESS! Message: {message[:50]}..." if len(message) > 50 else f"SUCCESS! Message: {message}")
        elif irq & 0x200:  # RX Timeout
            print("⏰ RX Timeout - no message received")
        elif irq == 0x0000:
            print("❓ No IRQ flags set - checking if chip is working...")
            # Try to get buffer status anyway
            message = receive()
            if message:
                print(f"Found message anyway: {message}")
        else:
            print(f"🔍 Other IRQ: 0x{irq:04X}")
            
        time.sleep(1)

# === MAIN PROGRAM ===
if __name__ == "__main__":
    try:
        # SIMPLE HARDWARE TEST - Try this first:
        test_hardware_connections()
        
        # SIMPLE COMMUNICATION TEST:
        # For TRANSMITTER: 
        # simple_transmitter()
        
        # For RECEIVER:
        # simple_receiver()
        
        # ORIGINAL EXAMPLES (use after simple test works):
        # For TRANSMITTER:
        transmitter_example()
        
        # For RECEIVER (comment above, uncomment below):
        # receiver_example()
        
    except KeyboardInterrupt:
        print("⏹️ Stopped")
    except Exception as e:
        print(f"❌ Error: {e}")