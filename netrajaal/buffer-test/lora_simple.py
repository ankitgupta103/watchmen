from machine import Pin, UART
import time

CFG_HEADER_PERSISTENT = 0xC0
CFG_HEADER_VOLATILE = 0xC2
RESPONSE_SUCCESS = 0xC1

FREQ_RANGE_400MHZ_START = 410
FREQ_RANGE_900MHZ_START = 850

UART_CONFIG_BAUD = 9600
UART_NORMAL_BAUD = 115200
UART_TIMEOUT_MS = 2000

MODE_SWITCH_DELAY_MS = 100
UART_INIT_DELAY_MS = 500
UART_STABILIZE_DELAY_MS = 30
TX_DELAY_MS = 150
RX_DELAY_MS = 250
CFG_WRITE_DELAY_MS = 300
CFG_RESPONSE_WAIT_MS = 200
CFG_RETRY_ATTEMPTS = 3
CFG_RETRY_DELAY_MS = 500

SX126X_UART_115200 = 0xE0
SX126X_PACKAGE_240 = 0x00
SX126X_Power_22dBm = 0x00

air_speed_dic = {1200: 0x01, 2400: 0x02, 4800: 0x03, 9600: 0x04, 19200: 0x05, 38400: 0x06, 62500: 0x07}
power_dic = {22: 0x00, 17: 0x01, 13: 0x02, 10: 0x03}

ser = None
M0 = None
M1 = None
my_addr = 0
my_freq = 868
offset_freq = 0

def configure_lora(uart_num=1, freq=868, addr=0, power=22, air_speed=2400, net_id=0, buffer_size=240, crypt=0, permanent=True, skip_config=False, m0_pin="P6", m1_pin="P7"):
    global ser, M0, M1, my_addr, my_freq, offset_freq
    
    my_addr = addr
    my_freq = freq
    
    M0 = Pin(m0_pin, Pin.OUT)
    M1 = Pin(m1_pin, Pin.OUT)
    
    if skip_config or permanent:
        M0.value(0)
        M1.value(0)
        time.sleep_ms(MODE_SWITCH_DELAY_MS)
        
        ser = UART(uart_num, UART_NORMAL_BAUD, timeout=UART_TIMEOUT_MS)
        time.sleep_ms(500)
        
        if freq > FREQ_RANGE_900MHZ_START:
            offset_freq = freq - FREQ_RANGE_900MHZ_START
        elif freq > FREQ_RANGE_400MHZ_START:
            offset_freq = freq - FREQ_RANGE_400MHZ_START
        
        pending = []
        for _ in range(50):
            if ser.any():
                time.sleep_ms(100)
                r_buff = ser.readline()
                if r_buff and len(r_buff) > 0:
                    if r_buff[-1] == 0x0A:
                        r_buff = r_buff[:-1]
                    if len(r_buff) >= 4:
                        pending.append(r_buff[3:])
            else:
                time.sleep_ms(50)
                if _ > 10:
                    break
        
        print(f"LoRa initialized (using saved config): addr={addr}, freq={freq}")
        if pending:
            print(f"Found {len(pending)} pending message(s) in buffer")
            return pending
        return []
    
    M0.value(0)
    M1.value(1)
    time.sleep_ms(MODE_SWITCH_DELAY_MS)
    
    ser = UART(uart_num, UART_CONFIG_BAUD, timeout=UART_TIMEOUT_MS)
    time.sleep_ms(UART_INIT_DELAY_MS)
    
    if freq > FREQ_RANGE_900MHZ_START:
        offset_freq = freq - FREQ_RANGE_900MHZ_START
    elif freq > FREQ_RANGE_400MHZ_START:
        offset_freq = freq - FREQ_RANGE_400MHZ_START
    else:
        raise ValueError(f"Invalid frequency: {freq}")
    
    air_speed_val = air_speed_dic.get(air_speed, 0x02)
    power_val = power_dic.get(power, 0x00)
    
    cfg_header = CFG_HEADER_PERSISTENT if permanent else CFG_HEADER_VOLATILE
    high_addr = (addr >> 8) & 0xFF
    low_addr = addr & 0xFF
    h_crypt = (crypt >> 8) & 0xFF
    l_crypt = crypt & 0xFF
    
    cfg_reg = [
        cfg_header, 0x00, 0x09,
        high_addr, low_addr, net_id & 0xFF,
        SX126X_UART_115200 + air_speed_val,
        SX126X_PACKAGE_240 + power_val + 0x20,
        offset_freq, 0x43, h_crypt, l_crypt
    ]
    
    while ser.any():
        ser.read()
    
    for attempt in range(CFG_RETRY_ATTEMPTS):
        ser.write(bytes(cfg_reg))
        time.sleep_ms(CFG_WRITE_DELAY_MS)
        
        if ser.any():
            time.sleep_ms(CFG_RESPONSE_WAIT_MS)
            r_buff = ser.read()
            if r_buff and len(r_buff) > 0 and r_buff[0] == RESPONSE_SUCCESS:
                break
        time.sleep_ms(CFG_RETRY_DELAY_MS)
    
    ser.deinit()
    time.sleep_ms(300)
    
    M0.value(0)
    M1.value(1)
    time.sleep_ms(UART_INIT_DELAY_MS)
    
    ser = UART(uart_num, UART_NORMAL_BAUD, timeout=UART_TIMEOUT_MS)
    time.sleep_ms(UART_STABILIZE_DELAY_MS)
    
    M0.value(0)
    M1.value(0)
    time.sleep_ms(MODE_SWITCH_DELAY_MS)
    
    print(f"LoRa configured: addr={addr}, freq={freq}, permanent={permanent}")
    return []

def send_message(target_addr, message):
    if isinstance(message, str):
        message = message.encode('utf-8')
    
    target_offset = my_freq - (FREQ_RANGE_900MHZ_START if my_freq > FREQ_RANGE_900MHZ_START else FREQ_RANGE_400MHZ_START)
    
    data = (
        bytes([target_addr >> 8]) +
        bytes([target_addr & 0xFF]) +
        bytes([target_offset]) +
        bytes([my_addr >> 8]) +
        bytes([my_addr & 0xFF]) +
        bytes([offset_freq]) +
        message +
        b"\n"
    )
    
    ser.write(data)
    time.sleep_ms(TX_DELAY_MS)

def receive_message():
    if ser.any():
        time.sleep_ms(RX_DELAY_MS)
        r_buff = ser.readline()
        if r_buff and len(r_buff) > 0 and r_buff[-1] == 0x0A:
            r_buff = r_buff[:-1]
        if r_buff and len(r_buff) >= 4:
            return r_buff[3:]
    return None

def main1():
    ADDR = 1
    TARGET_ADDR = 2
    PERMANENT = True
    
    configure_lora(addr=ADDR, permanent=PERMANENT, skip_config=True)
    
    print("Starting send loop...")
    counter = 0
    while True:
        send_message(TARGET_ADDR, f"Hello from {ADDR} - {counter}")
        print(f"TX: Hello from {ADDR} - {counter}")
        counter += 1
        time.sleep_ms(2000)

def main2():
    ADDR = 2
    PERMANENT = True
    
    pending = configure_lora(addr=ADDR, permanent=PERMANENT, skip_config=True)
    
    if pending:
        print("Reading pending messages from buffer:")
        for msg in pending:
            try:
                print(f"  Buffer: {msg.decode('utf-8')}")
            except:
                print(f"  Buffer: {msg}")
    
    print("Starting receive loop...")
    while True:
        msg = receive_message()
        if msg:
            try:
                print(f"RX: {msg.decode('utf-8')}")
            except:
                print(f"RX: {msg}")
        time.sleep_ms(100)

if __name__ == "__main__":
    main2()

