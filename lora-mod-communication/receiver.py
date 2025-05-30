import spidev
import RPi.GPIO as GPIO
import time

NSS = 8
RESET = 22
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

def read_fifo(length):
    GPIO.output(NSS, GPIO.LOW)
    data = spi.xfer2([0x00] + [0x00]*length)[1:]
    GPIO.output(NSS, GPIO.HIGH)
    return data

def set_mode(mode):
    write_register(0x01, mode)

reset()
write_register(0x01, 0x80) 
write_register(0x06, 0xD9)
write_register(0x07, 0x06)
write_register(0x08, 0x66)
write_register(0x09, 0x8F)
write_register(0x0B, 0x0B)
write_register(0x1D, 0x72)
write_register(0x1E, 0x74)
write_register(0x0F, 0x00) 
write_register(0x0D, 0x00) 
write_register(0x40, 0x00) 
write_register(0x1F, 0x00)  
set_mode(0x85) 

print("Listening...")
try:
    while True:
        if GPIO.input(DIO0) == 1:
            irq_flags = read_register(0x12)
            write_register(0x12, 0xFF)  
            if irq_flags & 0x40:
                current_addr = read_register(0x10)
                bytes_recv = read_register(0x13)
                write_register(0x0D, current_addr)
                payload = read_fifo(bytes_recv)
                print("Received:", bytes(payload).decode('utf-8', 'ignore'))
        time.sleep(0.1)
except KeyboardInterrupt:
    print("Exiting...")
    spi.close()
    GPIO.cleanup()
