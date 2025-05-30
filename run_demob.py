import time
from device import Device
from central import CommandCentral
from esp32_comm import EspComm

def get_serial_id():
    f=open("/proc/cpuinfo", "r")
    lines = f.readlines()
    for line in lines:
        l = line.strip()
        if l.find("Serial") >= 0:
            parts = l.split(":")
            if len(parts) != 2:
                return None
            d = parts[1].strip()
            return d
    return None

def get_device_id():
    did=get_serial_id()
    shortmap = {}
    shortmap["2b46c5c95aea7306"] = "CC"
    shortmap["9eccfdf8c851a5ef"] = "D01"
    if did not in shortmap:
        return None
    return shortmap[did]

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


