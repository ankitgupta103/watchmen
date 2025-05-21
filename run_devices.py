import time
from device import Device
from central import CommandCentral
from ipc_communicator import IPCCommunicator

def start_n_units(n, ncomm):
    devices = []
    for i in range(n):
        c=chr(i+65)
        devid=f"{c}{c}{c}"
        device = Device(devid, ncomm)
        devices.append(device)
    return devices

def main():
    num_units = 25
    ncomm = IPCCommunicator()
    devices = start_n_units(num_units, ncomm)
    cc  = CommandCentral("ZZZ", ncomm)
    ncomm.add_dev(cc.devid, cc)
    for d in devices:
        ncomm.add_dev(d.devid, d)

    for j in range(5):
        for device in devices:
            device.check_event()
            device.send_scan(time.time_ns())
            device.send_hb(time.time_ns())
            time.sleep(0.001)
        cc.send_spath()
        print(f"{j} rounds of Scan done.")
        time.sleep(3)

    cc.console_output()
    #for i in range(num_units):
    #    listen_threads[i].join()

if __name__=="__main__":
    main()
