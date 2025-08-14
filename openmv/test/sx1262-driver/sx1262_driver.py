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
    
    print("✅ LoRa ready!\n")

# === SEND FUNCTION ===
def send(message):
    """Send a message (string or bytes)"""
    # Convert to bytes if string
    if isinstance(message, str):
        data = message.encode('utf-8')
    else:
        data = message
    
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
    
    print(f"📡 Sent: {len(data)} bytes")

# === RECEIVE FUNCTION ===
def receive():
    """Receive a message - returns message data or None"""
    try:
        # Set to RX mode
        send_command([0x82, 0x00, 0x00, 0x00])
        
        # Small delay to receive
        time.sleep_ms(50)
        
        # Get RX buffer status
        wait_ready()
        cs.off()
        spi.write(bytearray([0x13, 0x00]))
        response = bytearray(3)
        spi.readinto(response)
        cs.on()
        
        payload_length = response[1]
        rx_start_pointer = response[2]
        
        if payload_length > 0:
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
def transmitter_example():
    """Example: Send 240-byte messages every 5 seconds"""
    init_lora(freq=868, speed="fast", power=22)
    
    counter = 0
    while True:
        counter += 1
        # Create 240-byte message
        message = f"Data packet #{counter:03d}: " + "X" * 220
        message = message[:240]  # Ensure exactly 240 bytes
        
        send(message)
        time.sleep(5)

def receiver_example():
    """Example: Continuously receive messages"""
    init_lora(freq=868, speed="fast", power=22)
    start_continuous_receive()
    
    while True:
        message = receive()
        if message:
            print(f"Message: {message[:50]}..." if len(message) > 50 else f"Message: {message}")
        time.sleep_ms(100)

# === MAIN PROGRAM ===
if __name__ == "__main__":
    try:
        # CHOOSE ONE:
        
        # For TRANSMITTER:
        transmitter_example()
        
        # For RECEIVER (comment above, uncomment below):
        # receiver_example()
        
        # Or use send() and receive() functions directly:
        # init_lora()
        # send("Hello World!")
        # message = receive()
        
    except KeyboardInterrupt:
        print("⏹️ Stopped")
    except Exception as e:
        print(f"❌ Error: {e}")