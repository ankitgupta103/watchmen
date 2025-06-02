# ==================== Transmitter: sx1262_tx.py ====================
import RPi.GPIO as GPIO
import spidev
import time

RESET_PIN = 22
BUSY_PIN = 5
DIO1_PIN = 25
TX_POWER = 0x0F

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000000
spi.mode = 0

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(RESET_PIN, GPIO.OUT)
GPIO.setup(BUSY_PIN, GPIO.IN)
GPIO.setup(DIO1_PIN, GPIO.IN)

def wait_busy():
    while GPIO.input(BUSY_PIN) == 1:
        time.sleep(0.001)

def spi_cmd(cmd, args=[]):
    wait_busy()
    spi.xfer2([cmd] + args)
    wait_busy()

def clear_irq():
    spi_cmd(0x02, [0xFF, 0xFF])

def read_irq():
    spi_cmd(0x12, [0x00])
    result = spi.readbytes(3)
    return result[1] << 8 | result[2]

def reset_module():
    GPIO.output(RESET_PIN, GPIO.LOW)
    time.sleep(0.01)
    GPIO.output(RESET_PIN, GPIO.HIGH)
    time.sleep(0.05)
    wait_busy()

def configure_radio():
    spi_cmd(0x80, [0x00])
    spi_cmd(0x8A, [0x01])
    freq = int((868000000 * (1 << 25)) / 32000000)
    spi_cmd(0x86, [(freq >> 24) & 0xFF, (freq >> 16) & 0xFF, (freq >> 8) & 0xFF, freq & 0xFF])
    spi_cmd(0x8E, [TX_POWER, 0x04])
    spi_cmd(0x8B, [0x07, 0x04, 0x01])
    spi_cmd(0x8C, [0x00, 0x08, 0x00, 0xFF, 0x01, 0x00])
    spi_cmd(0x08, [0x00, 0x08, 0x00, 0x00])

def write_payload(data):
    spi_cmd(0x0E, [0x00] + list(data))
    spi_cmd(0x0D, [0x00, 0x00])

def transmit(message):
    print(f"\n📡 Transmitting: '{message}'")
    clear_irq()
    write_payload(message.encode('utf-8'))
    spi_cmd(0x83, [0x00, 0x00, 0x00])
    start = time.time()
    while GPIO.input(DIO1_PIN) == 0:
        if time.time() - start > 5:
            print("Timeout: DIO1 not high")
            return
        time.sleep(0.01)
    print("✅ TxDone")
    clear_irq()

try:
    reset_module()
    configure_radio()
    count = 1
    while True:
        transmit(f"MSG #{count} from TX")
        count += 1
        time.sleep(5)
except KeyboardInterrupt:
    pass
finally:
    spi.close()
    GPIO.cleanup()


# ==================== Receiver: sx1262_rx.py ====================
import RPi.GPIO as GPIO
import spidev
import time
import sys

RESET_PIN = 22
BUSY_PIN = 5
DIO1_PIN = 25

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(RESET_PIN, GPIO.OUT)
GPIO.setup(BUSY_PIN, GPIO.IN)
GPIO.setup(DIO1_PIN, GPIO.IN)

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000000
spi.mode = 0

def wait_busy():
    while GPIO.input(BUSY_PIN) == 1:
        time.sleep(0.001)

def spi_cmd(cmd, args=[]):
    wait_busy()
    spi.xfer2([cmd] + args)
    wait_busy()

def clear_irq():
    spi_cmd(0x02, [0xFF, 0xFF])

def read_irq():
    spi_cmd(0x12, [0x00])
    result = spi.readbytes(3)
    return result[1] << 8 | result[2]

def reset_module():
    GPIO.output(RESET_PIN, GPIO.LOW)
    time.sleep(0.01)
    GPIO.output(RESET_PIN, GPIO.HIGH)
    time.sleep(0.05)
    wait_busy()

def configure_rx():
    spi_cmd(0x80, [0x00])
    spi_cmd(0x8A, [0x01])
    freq = int((868000000 * (1 << 25)) / 32000000)
    spi_cmd(0x86, [(freq >> 24) & 0xFF, (freq >> 16) & 0xFF, (freq >> 8) & 0xFF, freq & 0xFF])
    spi_cmd(0x8B, [0x07, 0x04, 0x01])
    spi_cmd(0x8C, [0x00, 0x08, 0x00, 0xFF, 0x01, 0x00])
    spi_cmd(0x08, [0x00, 0x40, 0x00, 0x40])
    clear_irq()

def receive():
    while True:
        clear_irq()
        spi_cmd(0x82, [0x00, 0x00, 0x00])
        start = time.time()
        while GPIO.input(DIO1_PIN) == 0:
            if time.time() - start > 20:
                print("⏳ Timeout waiting for packet")
                break
            time.sleep(0.01)
        irq = read_irq()
        if irq & 0x40:
            spi_cmd(0x13, [0x00])
            status = spi.readbytes(3)
            length = status[1]
            offset = status[2]
            spi_cmd(0x1E, [offset, 0x00])
            payload = spi.readbytes(length + 1)[1:]
            try:
                msg = bytes(payload).decode('utf-8')
                print(f"Received: '{msg}'")
            except:
                print(f"Could not decode payload: {payload}")

try:
    reset_module()
    configure_rx()
    receive()
except KeyboardInterrupt:
    pass
finally:
    spi.close()
    GPIO.cleanup()



# -------

# | SX1262 Label | Function | Pi BCM | Pi Pin | Notes                      |
# | ------------ | -------- | ------ | ------ | -------------------------- |
# | VCC          | Power    | —      | 1      | 3.3V              |
# | GND          | Ground   | —      | 6      | Ground                     |
# | MISO         | SPI      | 9      | 21     | SPI MISO                   |
# | MOSI         | SPI      | 10     | 19     | SPI MOSI                   |
# | SCK          | SPI      | 11     | 23     | SPI Clock                  |
# | NSS          | SPI CS   | 8      | 24     | CE0                        |
# | RST          | Reset    | 22     | 15     | Active LOW                 |
# | DIO0         | DIO1     | 25     | 22     | Interrupt                  |
# | DIO3         | BUSY     | 5      | 29     | Must read before/after SPI |

