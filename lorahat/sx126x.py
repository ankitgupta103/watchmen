
# This file is used for LoRa and Raspberry pi4B related issues 

import RPi.GPIO as GPIO
import serial
import time

class sx126x:

    M0 = 22
    M1 = 27
    # if the header is 0xC0, then the LoRa register settings dont lost when it poweroff, and 0xC2 will be lost. 
    # cfg_reg = [0xC0,0x00,0x09,0x00,0x00,0x00,0x62,0x00,0x17,0x43,0x00,0x00]
    cfg_reg = [0xC2,0x00,0x09,0x00,0x00,0x00,0x62,0x00,0x12,0x43,0x00,0x00]
    get_reg = bytes(12)
    rssi = False
    addr = 65535
    serial_n = ""
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

    def __init__(self,serial_num,freq,addr,power,rssi,air_speed=2400,\
                 net_id=0,buffer_size = 240,crypt=0,\
                 relay=False,lbt=False,wor=False):
        self.rssi = rssi
        self.addr = addr
        self.freq = freq
        self.serial_n = serial_num
        self.power = power

        self.target_baud = 115200   # <- CHANGE TO YOUR TARGET BAUD


        # Initial the GPIO for M0 and M1 Pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.M0,GPIO.OUT)
        GPIO.setup(self.M1,GPIO.OUT)
        GPIO.output(self.M0,GPIO.LOW)
        GPIO.output(self.M1,GPIO.HIGH)

        # The hardware UART of Pi3B+,Pi4B is /dev/ttyS0
        print("[INFO ] Opening serial at 9600 to configure")
        self.ser = serial.Serial(serial_num, 9600)
        self.ser.flushInput()

        self.set(freq,addr,power,rssi,air_speed,net_id,buffer_size,crypt,relay,lbt,wor)

        print("[INFO ] Reopening serial at 115200")
        self.ser.close()
        time.sleep(0.2)
        # self.ser = serial.Serial(serial_num, self.target_baud)
        # self.ser.flushInput()
        
        # # calling get_settings() to read the current settings @115200 baud
        # time.sleep(0.2)
        # self.get_settings()


        # Keep M1 HIGH (config mode) here
        GPIO.output(self.M0, GPIO.LOW)
        GPIO.output(self.M1, GPIO.HIGH)
        self.ser = serial.Serial(serial_num, self.target_baud)
        self.ser.flushInput()
        time.sleep(0.3)

        self.get_settings()

        # Now move to normal mode
        GPIO.output(self.M1, GPIO.LOW)
        GPIO.output(self.M0, GPIO.LOW)
        time.sleep(0.1)

    def set(self,freq,addr,power,rssi,air_speed=2400,\
            net_id=0,buffer_size = 240,crypt=0,\
            relay=False,lbt=False,wor=False):
        self.send_to = addr
        self.addr = addr
        # We should pull up the M1 pin when sets the module
        GPIO.output(self.M0,GPIO.LOW)
        GPIO.output(self.M1,GPIO.HIGH)
        time.sleep(0.1)

        low_addr = addr & 0xff
        high_addr = addr >> 8 & 0xff
        net_id_temp = net_id & 0xff
        if freq > 850:
            freq_temp = freq - 850
            self.start_freq = 850
            self.offset_freq = freq_temp
        elif freq >410:
            freq_temp = freq - 410
            self.start_freq  = 410
            self.offset_freq = freq_temp
        
        air_speed_temp = self.lora_air_speed_dic.get(air_speed,None)
        # if air_speed_temp != None
        
        buffer_size_temp = self.lora_buffer_size_dic.get(buffer_size,None)
        # if air_speed_temp != None:
        
        power_temp = self.lora_power_dic.get(power,None)
        #if power_temp != None:

        if rssi:
            # enable print rssi value 
            rssi_temp = 0x80
        else:
            # disable print rssi value
            rssi_temp = 0x00        

        # get crypt
        l_crypt = crypt & 0xff
        h_crypt = crypt >> 8 & 0xff
        
        if relay==False:
            self.cfg_reg[3] = high_addr
            self.cfg_reg[4] = low_addr
            self.cfg_reg[5] = net_id_temp
            self.cfg_reg[6] = self.SX126X_UART_BAUDRATE_115200 + air_speed_temp
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
            self.cfg_reg[6] = self.SX126X_UART_BAUDRATE_115200 + air_speed_temp
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
        self.ser.flushInput()

        for i in range(2):
            self.ser.write(bytes(self.cfg_reg))
            r_buff = 0
            time.sleep(0.2)
            if self.ser.inWaiting() > 0:
                time.sleep(0.1)
                r_buff = self.ser.read(self.ser.inWaiting())
                if r_buff[0] == 0xC1:
                    pass
                    # print("parameters setting is :",end='')
                    # for i in self.cfg_reg:
                        # print(hex(i),end=' ')
                        
                    # print('\r\n')
                    # print("parameters return is  :",end='')
                    # for i in r_buff:
                        # print(hex(i),end=' ')
                    # print('\r\n')
                else:
                    pass
                    #print("parameters setting fail :",r_buff)
                break
            else:
                print("setting fail,setting again")
                self.ser.flushInput()
                time.sleep(0.2)
                print('\x1b[1A',end='\r')
                if i == 1:
                    print("setting fail,Press Esc to Exit and run again")
                    # time.sleep(2)
                    # print('\x1b[1A',end='\r')

        GPIO.output(self.M0,GPIO.LOW)
        GPIO.output(self.M1,GPIO.LOW)
        time.sleep(0.1)

    def describe_config(self):
        print("[LoRa Configuration Register Breakdown]")
        cfg = self.cfg_reg
        if len(cfg) != 12:
            print("Invalid configuration length.")
            return

        baud_lookup = {
            0x00: 1200, 0x20: 2400, 0x40: 4800, 0x60: 9600,
            0x80: 19200, 0xA0: 38400, 0xC0: 57600, 0xE0: 115200
        }
        air_lookup = {
            0x00: 300, 0x01: 1200, 0x02: 2400, 0x03: 4800,
            0x04: 9600, 0x05: 19200, 0x06: 38400, 0x07: 62500
        }
        buf_lookup = {
            0x00: 240, 0x40: 128, 0x80: 64, 0xC0: 32
        }
        power_lookup = { 0x00: 22, 0x01: 17, 0x02: 13, 0x03: 10 }

        reg3 = cfg[6]
        reg4 = cfg[7]
        reg5 = cfg[8]
        reg6 = cfg[9]

        baud = baud_lookup.get(reg3 & 0xE0, "Unknown")
        air_speed = air_lookup.get(reg3 & 0x07, "Unknown")
        buffer = buf_lookup.get(reg4 & 0xC0, "Unknown")
        power = power_lookup.get(reg4 & 0x03, "Unknown")
        noise_enable = bool(reg4 & 0x20)
        rssi_byte_enable = bool(reg6 & 0x80)
        relay_enable = bool(reg6 & 0x20)

        print(f"Address         : {cfg[3] << 8 | cfg[4]}")
        print(f"Network ID      : {cfg[5]}")
        print(f"UART Baudrate   : {baud} bps")
        print(f"Air Speed       : {air_speed} bps")
        print(f"Buffer Size     : {buffer} bytes")
        print(f"Power           : {power} dBm")
        print(f"RSSI Enabled    : {'Yes' if rssi_byte_enable else 'No'}")
        print(f"Noise Enabled   : {'Yes' if noise_enable else 'No'}")
        print(f"Relay Enabled   : {'Yes' if relay_enable else 'No'}")
        print(f"Frequency (MHz) : {self.start_freq + self.offset_freq}.125")
        print(f"Encrypt Key     : 0x{cfg[10]:02X}{cfg[11]:02X}")


    # def get_settings(self):
    #     # the pin M1 of lora HAT must be high when enter setting mode and get parameters
    #     GPIO.output(M1,GPIO.HIGH)
    #     time.sleep(0.1)
        
    #     # send command to get setting parameters
    #     self.ser.write(bytes([0xC1,0x00,0x09]))
    #     if self.ser.inWaiting() > 0:
    #         time.sleep(0.1)
    #         self.get_reg = self.ser.read(self.ser.inWaiting())
        
    #     # check the return characters from hat and print the setting parameters
    #     if self.get_reg[0] == 0xC1 and self.get_reg[2] == 0x09:
    #         fre_temp = self.get_reg[8]
    #         addr_temp = self.get_reg[3] + self.get_reg[4]
    #         air_speed_temp = self.get_reg[6] & 0x03
    #         power_temp = self.get_reg[7] & 0x03
            
    #         print("Frequence is {0}.125MHz.",fre_temp)
    #         print("Node address is {0}.",addr_temp)
    #         print("Air speed is {0} bps"+ lora_air_speed_dic.get(None,air_speed_temp))
    #         print("Power is {0} dBm" + lora_power_dic.get(None,power_temp))
    #         GPIO.output(M1,GPIO.LOW)

    def get_settings(self):
        # Set module in configuration mode: M1 = HIGH, M0 = LOW
        GPIO.output(self.M0, GPIO.LOW)
        GPIO.output(self.M1, GPIO.HIGH)
        time.sleep(0.2)

        print("[INFO ] Sending get_settings command: C1 00 09 at", self.ser.baudrate)
        self.ser.reset_input_buffer()
        self.ser.write(bytes([0xC1, 0x00, 0x09]))
        time.sleep(0.5)

        if self.ser.in_waiting > 0:
            self.get_reg = self.ser.read(self.ser.in_waiting)
            reg = self.get_reg
            print("[DEBUG] Raw get_settings response:", reg)

            if len(reg) >= 12 and reg[0] == 0xC1 and reg[2] == 0x09:
                high_addr = reg[3]
                low_addr = reg[4]
                addr = (high_addr << 8) | low_addr
                net_id = reg[5]
                baud_air = reg[6]
                buffer_power = reg[7]
                freq = reg[8] + self.start_freq
                rssi_en = reg[9] & 0x80

                uart_baud_raw = baud_air & 0xE0
                air_speed_raw = baud_air & 0x07
                power_raw = buffer_power & 0x03
                buffer_raw = buffer_power & 0xC0

                air_speed = next((k for k, v in self.lora_air_speed_dic.items() if v == air_speed_raw), "Unknown")
                power = next((k for k, v in self.lora_power_dic.items() if v == power_raw), "Unknown")
                buffer_size = next((k for k, v in self.lora_buffer_size_dic.items() if v == buffer_raw), "Unknown")
                uart_baud = {
                    0x00: 1200,
                    0x20: 2400,
                    0x40: 4800,
                    0x60: 9600,
                    0x80: 19200,
                    0xA0: 38400,
                    0xC0: 57600,
                    0xE0: 115200
                }.get(uart_baud_raw, "Unknown")

                print(f"[LoRa Config] Address     : {addr}")
                print(f"[LoRa Config] Network ID  : {net_id}")
                print(f"[LoRa Config] Frequency   : {freq}.125 MHz")
                print(f"[LoRa Config] UART Baud   : {uart_baud} bps")
                print(f"[LoRa Config] Air Speed   : {air_speed} bps")
                print(f"[LoRa Config] Power       : {power} dBm")
                print(f"[LoRa Config] Buffer Size : {buffer_size} bytes")
                print(f"[LoRa Config] RSSI Enable : {'Yes' if rssi_en else 'No'}")
            else:
                print("[LoRa Config] Failed to parse settings response:", reg)
        else:
            print("[LoRa Config] No data returned from device.")

        GPIO.output(self.M1, GPIO.LOW)


#
# the data format like as following
# "node address,frequence,payload"
# "20,868,Hello World"
    def send(self,data):
        GPIO.output(self.M1,GPIO.LOW)
        GPIO.output(self.M0,GPIO.LOW)
        time.sleep(0.1)

        self.ser.write(data)
        # if self.rssi == True:
            # self.get_channel_rssi()
        time.sleep(0.1)


    def receive(self):
        if self.ser.inWaiting() > 0:
            time.sleep(0.5)
            r_buff = self.ser.read(self.ser.inWaiting())

            print("receive message from node address with frequence\033[1;32m %d,%d.125MHz\033[0m"%((r_buff[0]<<8)+r_buff[1],r_buff[2]+self.start_freq),end='\r\n',flush = True)
            print("message is "+str(r_buff[3:-1]),end='\r\n')
            
            # print the rssi
            if self.rssi:
                # print('\x1b[3A',end='\r')
                print("the packet rssi value: -{0}dBm".format(256-r_buff[-1:][0]))
                self.get_channel_rssi()
            else:
                pass
                #print('\x1b[2A',end='\r')

    def get_channel_rssi(self):
        GPIO.output(self.M1,GPIO.LOW)
        GPIO.output(self.M0,GPIO.LOW)
        time.sleep(0.1)
        self.ser.flushInput()
        self.ser.write(bytes([0xC0,0xC1,0xC2,0xC3,0x00,0x02]))
        time.sleep(0.5)
        re_temp = bytes(5)
        if self.ser.inWaiting() > 0:
            time.sleep(0.1)
            re_temp = self.ser.read(self.ser.inWaiting())
        if re_temp[0] == 0xC1 and re_temp[1] == 0x00 and re_temp[2] == 0x02:
            noise_rssi = format(256-re_temp[3])
            return noise_rssi
            #print("the current noise rssi value: -{0}dBm".format(256-re_temp[3]))
            # print("the last receive packet rssi value: -{0}dBm".format(256-re_temp[4]))
        else:
            # pass
            print("receive rssi value fail")
            # print("receive rssi value fail: ",re_temp)
