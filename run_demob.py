import time
import socket
from device import Device
from central import CommandCentral
from esp32_comm import EspComm

get_hostname():
    return socket.gethostname()

# Expect : central, rpi2, rpi3, rpi4, rpi5
def get_device_id():
    hn = get_hostname()
    if hn == "central":
        return "CC"
    return hn

def run_unit():
    devid = get_device_id()
    ncomm = EspComm(devid)
    if devid == "CC":
        cc  = CommandCentral("CC", None, ncomm)
        ncomm.add_node(cc)
        ncomm.keep_reading()
        for j in range(2):
            time.sleep(5)
            cc.send_spath()
            time.sleep(10)
            cc.console_output()
            print(f"{j} rounds of Scan done.")
        time.sleep(500)
    else:
        device = Device(devid, None, ncomm)
        ncomm.add_node(device)
        ncomm.keep_reading()
        for j in range(1):
            device.check_event()
            device.send_scan(time.time_ns())
            device.send_hb(time.time_ns())
            time.sleep(8)
            print(f"{j} rounds of Scan done.")

def main():
    run_unit()

if __name__=="__main__":
    main()


