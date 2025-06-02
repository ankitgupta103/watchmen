import spidev
import lgpio  # Import lgpio
import time
import sys # To cleanly exit the script

# Define GPIO BCM numbers for your LoRa module
NSS_PIN = 8     # Changed back to BCM 8 (SPI CE0)
RESET_PIN = 22
DIO0_PIN = 27   # DIO0 is used for TxDone interrupt

# On Raspberry Pi 5, the main GPIO chip is typically 0
GPIO_CHIP_NUMBER = 0

# --- SPI Setup ---
spi = spidev.SpiDev()
# Open SPI bus 0, device 0 (CE0, which is BCM 8).
# spidev will automatically control this pin for transactions.
try:
    spi.open(0, 0) # Note the '0' here for CE0
    spi.max_speed_hz = 1000000
except FileNotFoundError:
    print("Error: SPI device not found. Ensure SPI is enabled in raspi-config.")
    sys.exit(1)
except Exception as e:
    print(f"Error opening SPI device: {e}")
    sys.exit(1)

# --- lgpio Setup ---
h = None # Initialize handle for lgpio chip

# --- Core LoRa Functions ---
def set_gpio_output(pin, state):
    """Helper to set a GPIO pin (high/low)."""
    lgpio.gpio_write(h, pin, state)

def get_gpio_input(pin):
    """Helper to read a GPIO pin state."""
    return lgpio.gpio_read(h, pin)

def reset_lora():
    """Resets the LoRa module."""
    print("Resetting LoRa module...")
    set_gpio_output(RESET_PIN, lgpio.LOW)
    time.sleep(0.1)
    set_gpio_output(RESET_PIN, lgpio.HIGH)
    time.sleep(0.1)
    print("LoRa module reset.")

def write_register(reg, val):
    """Writes a value to a LoRa register."""
    # NSS control removed, spidev handles it
    spi.xfer2([reg | 0x80, val])

def read_register(reg):
    """Reads a value from a LoRa register."""
    # NSS control removed, spidev handles it
    val = spi.xfer2([reg & 0x7F, 0x00])[1]
    return val

def write_fifo(data_bytes):
    """Writes data to the LoRa FIFO buffer."""
    # NSS control removed, spidev handles it
    spi.xfer2([0x80] + list(data_bytes))

def set_lora_mode(mode):
    """Sets the LoRa module operating mode."""
    write_register(0x01, mode) # REG_OP_MODE

def send_message(msg):
    """Prepares and sends a LoRa message."""
    print(f"Preparing to send: '{msg}'")

    # 1. Put module in STANDBY mode for configuration
    set_lora_mode(0x81) # LoRaWAN mode, STANDBY state (0x80 | 0x01)
    time.sleep(0.01) # Small delay for mode change

    # 2. Set FIFO pointers
    write_register(0x0E, 0x00) # REG_FIFO_TX_BASE_ADDR (start of FIFO)
    write_register(0x0D, 0x00) # REG_FIFO_ADDR_PTR (current position in FIFO)

    # 3. Write message to FIFO
    msg_bytes = msg.encode('utf-8')
    write_fifo(msg_bytes)
    write_register(0x22, len(msg_bytes)) # REG_PAYLOAD_LENGTH (LoRa payload length)

    # 4. Switch to TX mode
    print("Switching to TX mode...")
    set_lora_mode(0x83) # LoRaWAN mode, TX state (0x80 | 0x03)

    # 5. Wait for TxDone interrupt (DIO0 goes high)
    print("Sending...")
    # Timeout for transmission in case DIO0 doesn't go high
    start_time = time.time()
    TX_TIMEOUT_SECONDS = 5 # Adjust as needed for your SF/BW
    while get_gpio_input(DIO0_PIN) == lgpio.LOW:
        if time.time() - start_time > TX_TIMEOUT_SECONDS:
            print("TX Timeout: DIO0 did not go high in time.")
            break
        time.sleep(0.01) # Small delay to prevent busy-waiting

    # 6. Clear TxDone interrupt flag
    irq_flags = read_register(0x12) # REG_IRQ_FLAGS
    if irq_flags & 0x08: # Check if TxDone flag (0x08) is set
        write_register(0x12, 0xFF) # Clear all IRQ flags (especially TxDone)
        print("Sent successfully!")
    else:
        print(f"Transmission finished, but TxDone flag not set. IRQ Flags: {hex(irq_flags)}")

    # 7. Go back to STANDBY mode after transmit
    set_lora_mode(0x81) # LoRaWAN mode, STANDBY state

# --- Main Program Logic ---
try:
    # Open the GPIO chip
    h = lgpio.gpiochip_open(GPIO_CHIP_NUMBER)
    print(f"GPIO chip {GPIO_CHIP_NUMBER} opened successfully.")

    # Claim GPIO pins for control
    # No longer claiming NSS_PIN
    lgpio.gpio_claim_output(h, RESET_PIN)
    lgpio.gpio_claim_input(h, DIO0_PIN)

    # Initialize LoRa module
    reset_lora()

    # LoRa Module Configuration (Common for TX/RX)
    write_register(0x01, 0x80)  # LoRaWAN mode, SLEEP state (for configuration)
    # Set frequency (e.g., 868 MHz)
    write_register(0x06, 0xD9)  # Freq MSB (868 MHz example)
    write_register(0x07, 0x06)  # Freq Mid
    write_register(0x08, 0x66)  # Freq LSB
    write_register(0x09, 0x8F)  # PA_CONFIG: Output power +17dBm (max), PA_BOOST pin
    write_register(0x0B, 0x0B)  # OCP: Over Current Protection, 100mA
    write_register(0x1D, 0x72)  # RegModemConfig1: BW=125kHz, CR=4/5, Implicit Header OFF
    write_register(0x1E, 0x74)  # RegModemConfig2: SF=7, RxPayloadCrcOn (0x04)
    write_register(0x40, 0x00)  # DIO Mapping 1 (DIO0=TxDone)


    print("\n--- LoRa Register Readback (Transmitter) ---")
    print(f"REG_OP_MODE (0x01): {hex(read_register(0x01))}")
    print(f"REG_FRF_MSB (0x06): {hex(read_register(0x06))}")
    print(f"REG_FRF_MID (0x07): {hex(read_register(0x07))}")
    print(f"REG_FRF_LSB (0x08): {hex(read_register(0x08))}")
    print(f"REG_PA_CONFIG (0x09): {hex(read_register(0x09))}")
    print(f"REG_OCP (0x0B): {hex(read_register(0x0B))}")
    print(f"REG_MODEM_CONFIG1 (0x1D): {hex(read_register(0x1D))}")
    print(f"REG_MODEM_CONFIG2 (0x1E): {hex(read_register(0x1E))}")
    print(f"REG_DIO_MAPPING1 (0x40): {hex(read_register(0x40))}")
    print("---------------------------------------------")
    time.sleep(1) # Give it a moment

    print(f"REG_VERSION (0x42): {hex(read_register(0x42))}")

    print("LoRa transmitter configured. Starting message loop...")

    message_counter = 0
    while True:
        message_counter += 1
        msg_to_send = f"Hello from Pi-A ({message_counter})"
        send_message(msg_to_send)
        time.sleep(5) # Wait 5 seconds before sending next message

except OSError as e:
    print(f"Error: A system or GPIO error occurred: {e}")
    print("This often means a GPIO pin is busy or permissions are incorrect.")
    print("Ensure you're running with 'sudo' and no other script is using these pins.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    # --- Cleanup ---
    if spi:
        spi.close()
        print("SPI closed.")
    if h:
        lgpio.gpiochip_close(h) # Release all claimed GPIO pins
        print("GPIO chip closed and pins released.")
    print("Program finished.")
