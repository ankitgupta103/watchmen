try:
    from machine import Pin, UART
except ImportError:
    print("machine module not found. not running on openmv OpenMV.")
    raise

import time

class sx126x:

    # Define GPIO pins for OpenMV RT1062
    M0_PIN = 'P6'  # Change to your actual pin
    M1_PIN = 'P7'  # Change to your actual pin
    
    # if the header is 0xC0, then the LoRa register settings dont lost when it poweroff, and 0xC2 will be lost. 
    # cfg_reg = [0xC0,0x00,0x09,0x00,0x00,0x00,0x62,0x00,0x17,0x43,0x00,0x00]
    cfg_reg = [0xC2,0x00,0x09,0x00,0x00,0x00,0x62,0x00,0x12,0x43,0x00,0x00]
    get_reg = bytes(12)
    rssi = False
    addr = 65535
    uart_num = 1  # Default UART number for OpenMV
    addr_temp = 0

    #
    # start frequence of two lora module
    #
    # E22-400T22S           E22-900T22S
    # 410~493MHz      or    850~930MHz
    start_freq = 850

    #
    # offset between start and end frequence of two lora module
    #
    # E22-400T22S           E22-900T22S
    # 410~493MHz      or    850~930MHz
    offset_freq = 18

    # power = 22
    # air_speed =2400

    SX126X_UART_BAUDRATE_1200 = 0x00
    SX126X_UART_BAUDRATE_2400 = 0x20
    SX126X_UART_BAUDRATE_4800 = 0x40
    SX126X_UART_BAUDRATE_9600 = 0x60
    SX126X_UART_BAUDRATE_19200 = 0x80
    SX126X_UART_BAUDRATE_38400 = 0xA0
    SX126X_UART_BAUDRATE_57600 = 0xC0
    SX126X_UART_BAUDRATE_115200 = 0xE0

    SX126X_PACKAGE_SIZE_240_BYTE = 0x00
    SX126X_PACKAGE_SIZE_128_BYTE = 0x40
    SX126X_PACKAGE_SIZE_64_BYTE = 0x80
    SX126X_PACKAGE_SIZE_32_BYTE = 0xC0

    SX126X_Power_22dBm = 0x00
    SX126X_Power_17dBm = 0x01
    SX126X_Power_13dBm = 0x02
    SX126X_Power_10dBm = 0x03

    lora_air_speed_dic = {
        1200:0x01,
        2400:0x02,
        4800:0x03,
        9600:0x04,
        19200:0x05,
        38400:0x06,
        62500:0x07
    }

    lora_power_dic = {
        22:0x00,
        17:0x01,
        13:0x02,
        10:0x03
    }

    lora_buffer_size_dic = {
        240:SX126X_PACKAGE_SIZE_240_BYTE,
        128:SX126X_PACKAGE_SIZE_128_BYTE,
        64:SX126X_PACKAGE_SIZE_64_BYTE,
        32:SX126X_PACKAGE_SIZE_32_BYTE
    }

    def __init__(self, uart_num=1, freq=868, addr=0, power=22, rssi=True, air_speed=2400,\
                 net_id=0, buffer_size=240, crypt=0,\
                 relay=False, lbt=False, wor=False, m0_pin='P6', m1_pin='P7'):
        self.rssi = rssi
        self.addr = addr
        self.freq = freq
        self.uart_num = uart_num
        self.power = power
        self.config_success = False
        
        print(f"Initializing with UART {uart_num}, M0={m0_pin}, M1={m1_pin}")
        
        # Initialize GPIO pins for M0 and M1
        try:
            self.M0 = Pin(m0_pin, Pin.OUT)
            self.M1 = Pin(m1_pin, Pin.OUT)
            print("GPIO pins initialized successfully")
        except Exception as e:
            print(f"GPIO initialization failed: {e}")
            raise
            
        # Set initial pin states
        self.M0.value(0)  # LOW
        self.M1.value(1)  # HIGH
        print("M0=LOW, M1=HIGH (configuration mode)")

        # Initialize UART for OpenMV
        try:
            self.ser = UART(uart_num, 9600, timeout=2000)  # 2 second timeout
            print(f"UART {uart_num} initialized at 9600 baud")
        except Exception as e:
            print(f"UART initialization failed: {e}")
            raise
            
        # Give module time to initialize
        time.sleep_ms(500)
        
        self.set(freq, addr, power, rssi, air_speed, net_id, buffer_size, crypt, relay, lbt, wor)

    def set(self, freq, addr, power, rssi, air_speed=2400,\
            net_id=0, buffer_size=240, crypt=0,\
            relay=False, lbt=False, wor=False):
        self.send_to = addr
        self.addr = addr
        
        # We should pull up the M1 pin when sets the module
        self.M0.value(0)  # LOW
        self.M1.value(1)  # HIGH
        time.sleep_ms(100)

        low_addr = addr & 0xff
        high_addr = addr >> 8 & 0xff
        net_id_temp = net_id & 0xff
        
        if freq > 850:
            freq_temp = freq - 850
            self.start_freq = 850
            self.offset_freq = freq_temp
        elif freq > 410:
            freq_temp = freq - 410
            self.start_freq = 410
            self.offset_freq = freq_temp
        
        air_speed_temp = self.lora_air_speed_dic.get(air_speed, None)
        buffer_size_temp = self.lora_buffer_size_dic.get(buffer_size, None)
        power_temp = self.lora_power_dic.get(power, None)

        if rssi:
            # enable print rssi value 
            rssi_temp = 0x80
        else:
            # disable print rssi value
            rssi_temp = 0x00        

        # get crypt
        l_crypt = crypt & 0xff
        h_crypt = crypt >> 8 & 0xff
        
        if relay == False:
            self.cfg_reg[3] = high_addr
            self.cfg_reg[4] = low_addr
            self.cfg_reg[5] = net_id_temp
            self.cfg_reg[6] = self.SX126X_UART_BAUDRATE_9600 + air_speed_temp
            # 
            # it will enable to read noise rssi value when add 0x20 as follow
            # 
            self.cfg_reg[7] = buffer_size_temp + power_temp + 0x20
            self.cfg_reg[8] = freq_temp
            #
            # it will output a packet rssi value following received message
            # when enable eighth bit with 06H register(rssi_temp = 0x80)
            #
            self.cfg_reg[9] = 0x43 + rssi_temp
            self.cfg_reg[10] = h_crypt
            self.cfg_reg[11] = l_crypt
        else:
            self.cfg_reg[3] = 0x01
            self.cfg_reg[4] = 0x02
            self.cfg_reg[5] = 0x03
            self.cfg_reg[6] = self.SX126X_UART_BAUDRATE_9600 + air_speed_temp
            # 
            # it will enable to read noise rssi value when add 0x20 as follow
            # 
            self.cfg_reg[7] = buffer_size_temp + power_temp + 0x20
            self.cfg_reg[8] = freq_temp
            #
            # it will output a packet rssi value following received message
            # when enable eighth bit with 06H register(rssi_temp = 0x80)
            #
            self.cfg_reg[9] = 0x03 + rssi_temp
            self.cfg_reg[10] = h_crypt
            self.cfg_reg[11] = l_crypt

        # Clear input buffer
        while self.ser.any():
            self.ser.read()

        # Debug: Print configuration being sent
        print("Sending configuration:", [hex(x) for x in self.cfg_reg])

        for i in range(3):  # Try 3 times instead of 2
            print(f"Configuration attempt {i+1}")
            self.ser.write(bytes(self.cfg_reg))
            time.sleep_ms(300)  # Longer delay
            
            if self.ser.any():
                time.sleep_ms(200)  # Longer wait for response
                r_buff = self.ser.read()
                print(f"Received response: {[hex(x) for x in r_buff] if r_buff else 'None'}")
                
                if r_buff and len(r_buff) > 0 and r_buff[0] == 0xC1:
                    print("LoRa module configured successfully")
                    self.config_success = True
                    break
                else:
                    print(f"Configuration failed, unexpected response: {r_buff}")
            else:
                print("No response from module")
                
            # Clear input buffer before retry
            while self.ser.any():
                self.ser.read()
            time.sleep_ms(500)
            
            if i == 2:
                print("Configuration failed after 3 attempts. Check:")
                print("- UART connections (TX/RX swapped?)")
                print("- M0/M1 pin connections")
                print("- Power supply (3.3V)")
                print("- Baud rate compatibility")
                self.config_success = False

        self.M0.value(0)  # LOW
        self.M1.value(0)  # LOW
        time.sleep_ms(100)

    def get_settings(self):
        # the pin M1 of lora HAT must be high when enter setting mode and get parameters
        self.M1.value(1)  # HIGH
        time.sleep_ms(100)
        
        # send command to get setting parameters
        self.ser.write(bytes([0xC1, 0x00, 0x09]))
        time.sleep_ms(100)
        
        if self.ser.any():
            time.sleep_ms(100)
            self.get_reg = self.ser.read()
        
        # check the return characters from hat and print the setting parameters
        if self.get_reg and len(self.get_reg) >= 9 and self.get_reg[0] == 0xC1 and self.get_reg[2] == 0x09:
            fre_temp = self.get_reg[8]
            addr_temp = (self.get_reg[3] << 8) + self.get_reg[4]
            air_speed_temp = self.get_reg[6] & 0x03
            power_temp = self.get_reg[7] & 0x03
            
            print(f"Frequency is {fre_temp + self.start_freq}.125MHz")
            print(f"Node address is {addr_temp}")
            print(f"Air speed code is {air_speed_temp}")
            print(f"Power code is {power_temp}")
            
        self.M1.value(0)  # LOW

    def send(self, data):
        if not hasattr(self, 'config_success') or not self.config_success:
            print("Warning: Module not properly configured, send may fail")
            
        self.M1.value(0)  # LOW
        self.M0.value(0)  # LOW - Normal operation mode
        time.sleep_ms(100)
        
        print(f"Sending {len(data)} bytes: {[hex(x) for x in data[:10]]}{'...' if len(data) > 10 else ''}")
        self.ser.write(data)
        time.sleep_ms(100)

    def receive(self):
        if self.ser.any():
            time.sleep_ms(500)
            r_buff = self.ser.read()
            
            if r_buff and len(r_buff) >= 6:
                sender_addr = (r_buff[0] << 8) + r_buff[1]
                frequency = r_buff[2] + self.start_freq
                
                print(f"Received message from node address {sender_addr} at {frequency}.125MHz")
                
                # Extract message payload (skip first 3 bytes for address and freq)
                if len(r_buff) > 3:
                    if self.rssi and len(r_buff) > 4:
                        # Last byte is RSSI, message is everything in between
                        message = r_buff[3:-1]
                        rssi_val = r_buff[-1]
                        print(f"Message: {message}")
                        print(f"Packet RSSI: -{256-rssi_val}dBm")
                        self.get_channel_rssi()
                    else:
                        # No RSSI, message is from byte 3 to end
                        message = r_buff[3:]
                        print(f"Message: {message}")
            else:
                print(f"Received short or empty message: {r_buff}")

    def get_channel_rssi(self):
        self.M1.value(0)  # LOW
        self.M0.value(0)  # LOW
        time.sleep_ms(100)
        
        # Clear input buffer
        while self.ser.any():
            self.ser.read()
            
        self.ser.write(bytes([0xC0, 0xC1, 0xC2, 0xC3, 0x00, 0x02]))
        time.sleep_ms(500)
        
        if self.ser.any():
            time.sleep_ms(100)
            re_temp = self.ser.read()
            
            if re_temp and len(re_temp) >= 4 and re_temp[0] == 0xC1 and re_temp[1] == 0x00 and re_temp[2] == 0x02:
                print(f"Current noise RSSI: -{256-re_temp[3]}dBm")
            else:
                print("Failed to receive RSSI value")
        else:
            print("No RSSI response received")