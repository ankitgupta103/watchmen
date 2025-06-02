import spidev
import RPi.GPIO as GPIO
import time

NSS = 24
RESET = 15
DIO0 = 25

spi = spidev.SpiDev()
spi.open(0, 0) 
spi.max_speed_hz = 5000000


GPIO.setmode(GPIO.BCM)
GPIO.setup(NSS, GPIO.OUT)
GPIO.setup(RESET, GPIO.OUT)
GPIO.setup(DIO0, GPIO.IN)

def reset():
    GPIO.output(RESET, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(RESET, GPIO.HIGH)
    time.sleep(0.1)

def write_register(reg, val):
    GPIO.output(NSS, GPIO.LOW)
    spi.xfer2([reg | 0x80, val])
    GPIO.output(NSS, GPIO.HIGH)

def read_register(reg):
    GPIO.output(NSS, GPIO.LOW)
    val = spi.xfer2([reg & 0x7F, 0x00])[1]
    GPIO.output(NSS, GPIO.HIGH)
    return val

def set_mode(mode):
    write_register(0x01, mode) 

def send_message(msg):
    set_mode(0x01)  
    write_register(0x0E, 0x00)  
    write_register(0x0D, 0x00) 

    for b in msg.encode():
        write_register(0x00, b)

    write_register(0x22, len(msg)) 
    set_mode(0x03)  # TX mode

    print("Sending:", msg)
    while GPIO.input(DIO0) == 0:
        time.sleep(0.01)
    print("Sent")

reset()

write_register(0x01, 0x80)  # Sleep + LoRa
write_register(0x06, 0xD9)  # freq MSB (868 MHz)
write_register(0x07, 0x06)  # freq MID
write_register(0x08, 0x66)  # freq LSB
write_register(0x09, 0x8F)  # PA config (max power)
write_register(0x0B, 0x0B)  # Overcurrent protection
write_register(0x1D, 0x72)  # BW=125kHz, CR=4/5
write_register(0x1E, 0x74)  # SF=7, CRC on

try:
    while True:
        send_message("Hello from Pi-A")
        time.sleep(5)
except KeyboardInterrupt:
    print("Exiting...")
    spi.close()
    GPIO.cleanup()
