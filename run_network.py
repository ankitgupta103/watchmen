import time
import os
import threading
import constants
import device_info
import json
import layout
import central
import glob
from device import Device
from central import CommandCentral

def start_n_units(dirname, n):
    devices = []
    for i in range(n):
        c=chr(i+65)
        devid=f"{c}{c}{c}"
        device = Device(devid, dirname)
        devices.append(device)
    return devices

def main():
    dirname = f"/tmp/network_sim_{time.time_ns()}"
    num_units = 25

    devices = start_n_units(dirname, num_units)

    listen_threads = []
    for i in range(num_units):
        listen_threads.append(devices[i].keep_listening())

    cc  = central.CommandCentral("ZZZ", dirname)

    for j in range(5):
        for device in devices:
            device.send_scan(time.time_ns())
            device.send_hb(time.time_ns())
            time.sleep(0.001)
        cc.send_spath()
        print(f"{j} rounds of Scan done.")
        time.sleep(15)
        cc.listen_once()

    print("Waiting for 15 secs")
    time.sleep(15)
    print("Listening on command center now")
    cc.listen_once()

    #for i in range(num_units):
    #    listen_threads[i].join()

if __name__=="__main__":
    main()
