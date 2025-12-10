import binascii
import machine
import utime

def get_dev_id():
    uid = binascii.hexlify(machine.unique_id())
    print(uid)
    if uid == b'e076465dd7194025':
        return 219
    elif uid == b'e076465dd7091027':
        return 221
    elif uid == b'e076465dd7193a09':
        return 222
    elif uid == b'e076465dd7090d1c':
        return 223
    elif uid == b'e076465dd7091843':
        return 225

correction_map = {
        221 : 383599390,
        }

def get_correction(devid):
    if devid not in correction_map:
        print(f"==== ERROR ---- unknown devid {devid} ======")
        return -1
    return correction_map[devid]

def get_ts_sec(devid):
    ts = utime.time() + get_correction(devid)
    return ts

def get_ts_human(devid):
    return utime.localtime(get_ts_sec(devid))

def main():
    devid = get_dev_id()
    print(f"At device id {devid}, epoch time = {get_ts_sec(devid)}, which is {get_ts_human(devid)} in IST")

main()
