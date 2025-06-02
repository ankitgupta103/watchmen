import spidev
import lgpio  # Import lgpio instead of RPi.GPIO
import time

# Define GPIO BCM numbers for your LoRa module
NSS_PIN = 8     # Corresponds to SPI CE0 (Chip Select)
RESET_PIN = 22
DIO0_PIN = 25

# On Raspberry Pi 5, the main GPIO chip is typically 0
GPIO_CHIP_NUMBER = 0

# --- SPI Setup ---
# spidev often works directly as it uses the Linux SPI driver,
# but we need to ensure the NSS (CS) pin is handled by lgpio if
# spidev's automatic CE handling conflicts or is not desired.
# For manual NSS control as in your original code, spidev.open(0, 0) is fine.
spi = spidev.SpiDev()
# Open SPI bus 0, device 0 (CE0).
# Since you're manually controlling NSS_PIN=8, this means spidev won't toggle it automatically.
# This is usually the desired behavior when you want full control of CS.
spi.open(0, 0)
spi.max_speed_hz = 5000000

# --- lgpio Setup ---
# Open the GPIO chip
h = None # Initialize handle to None
try:
    h = lgpio.gpiochip_open(GPIO_CHIP_NUMBER)

    # Claim GPIO pins as output or input
    # Note: lgpio.gpio_claim_output and lgpio.gpio_claim_input handle the "setup"
    lgpio.gpio_claim_output(h, NSS_PIN)
    lgpio.gpio_claim_output(h, RESET_PIN)
    lgpio.gpio_claim_input(h, DIO0_PIN)

    # --- GPIO Control Functions (adapted for lgpio) ---
    def set_gpio_output(pin, state):
        """Helper to set a GPIO pin (high/low)."""
        lgpio.gpio_write(h, pin, state)

    def get_gpio_input(pin):
        """Helper to read a GPIO pin state."""
        return lgpio.gpio_read(h, pin)

    def reset_lora():
        """Resets the LoRa module."""
        set_gpio_output(RESET_PIN, lgpio.LOW) # Use lgpio.LOW/HIGH for clarity
        time.sleep(0.1)
        set_gpio_output(RESET_PIN, lgpio.HIGH)
        time.sleep(0.1)

    def write_register(reg, val):
        """Writes a value to a LoRa register."""
        set_gpio_output(NSS_PIN, lgpio.LOW)
        spi.xfer2([reg | 0x80, val])
        set_gpio_output(NSS_PIN, lgpio.HIGH)

    def read_register(reg):
        """Reads a value from a LoRa register."""
        set_gpio_output(NSS_PIN, lgpio.LOW)
        val = spi.xfer2([reg & 0x7F, 0x00])[1]
        set_gpio_output(NSS_PIN, lgpio.HIGH)
        return val

    def read_fifo(length):
        """Reads data from the LoRa FIFO buffer."""
        set_gpio_output(NSS_PIN, lgpio.LOW)
        # 0x00 is the FIFO read address (RegFifo)
        data = spi.xfer2([0x00] + [0x00] * length)[1:]
        set_gpio_output(NSS_PIN, lgpio.HIGH)
        return data

    def set_lora_mode(mode):
        """Sets the LoRa module operating mode."""
        write_register(0x01, mode) # REG_OP_MODE

    # --- LoRa Initialization Sequence ---
    reset_lora()
    write_register(0x01, 0x80)  # LoRaWAN mode, SLEEP state (long range mode enable)
    write_register(0x06, 0xD9)  # Freq MSB (868 MHz example, adjust if needed)
    write_register(0x07, 0x06)  # Freq Mid
    write_register(0x08, 0x66)  # Freq LSB
    write_register(0x09, 0x8F)  # PA_CONFIG: Output power +17dBm (max), PA_BOOST pin
    write_register(0x0B, 0x0B)  # OCP: Over Current Protection, 100mA
    write_register(0x1D, 0x72)  # BW = 125kHz, Coding Rate 4/5, Implicit Header OFF
    write_register(0x1E, 0x74)  # Spreading Factor = 12, CRC enabled
    write_register(0x0F, 0x00)  # FIFO TX Base Address
    write_register(0x0D, 0x00)  # FIFO RX Base Address
    write_register(0x40, 0x00)  # DIO Mapping 1 (DIO0=RxDone)
    write_register(0x1F, 0x00)  # Preamble Length MSB
    set_lora_mode(0x85)         # LoRaWAN mode, RX_CONTINUOUS

    print("Listening for LoRa packets...")

    # --- Main Loop ---
    while True:
        # Check DIO0 for interrupt (RxDone in this mapping)
        if get_gpio_input(DIO0_PIN) == lgpio.HIGH: # Check if DIO0 is high
            irq_flags = read_register(0x12) # REG_IRQ_FLAGS
            write_register(0x12, 0xFF)      # Clear all IRQ flags

            if irq_flags & 0x40: # Check if RxDone flag (0x40) is set
                current_addr = read_register(0x10) # REG_FIFO_RX_CURRENT_ADDR
                bytes_recv = read_register(0x13)   # REG_RX_NB_BYTES
                write_register(0x0D, current_addr) # Set FIFO_RX_BASE_ADDR to current received packet start

                payload = read_fifo(bytes_recv)
                try:
                    # Attempt to decode, handle errors gracefully
                    decoded_payload = bytes(payload).decode('utf-8')
                    print(f"Received: {decoded_payload} (RSSI: {read_register(0x1A) - 157})") # Example RSSI calculation
                except UnicodeDecodeError:
                    print(f"Received (undecodable): {payload.hex()} (RSSI: {read_register(0x1A) - 157})")
            else:
                # Handle other IRQ flags if necessary (e.g., RxTimeout, CrcError)
                if irq_flags & 0x20: # RxTimeout
                    print("RX Timeout")
                if irq_flags & 0x02: # CRC Error
                    print("CRC Error")
        time.sleep(0.01) # Small delay to prevent busy-waiting

except KeyboardInterrupt:
    print("\nExiting program...")
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
