from machine import RTC
import sensor
import time


rtc = RTC()
def get_human_ts():
    # Input: None; Output: str formatted as mm:ss
    _,_,_,_,h,m,s,_ = rtc.datetime()
    t=f"{m}:{s}"
    return t

log_entries_buffer = []

def log(msg):
    # Input: msg: str; Output: None (side effects: buffer append and console log)
    t = get_human_ts()
    log_entry = f"{t} : {msg}"
    log_entries_buffer.append(log_entry)
    print(log_entry)
    

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

def append_distribution(dd, i):
    if i in dd:
        dd[i] += 1
    else:
        dd[i] = 1

def det_distribution(ll):
    dd = {}
    for x in ll:
        for i in [0,1,2,4,8,16,32,64,128]:
            if x >= i:
                append_distribution(dd, i)
    return dd

def get_difference(dd, n):
    cum_delta = 0
    for x in dd:
        if x< 4:
            continue
        num_more = float(dd[x]/n)
        delta = x * num_more
        cum_delta += delta
        log(f"{x} : {num_more} : {delta} : {cum_delta}")
    log(cum_delta)
    return cum_delta

def get_diff():
    img1 = sensor.snapshot()
    log(len(img1.bytearray()))
    time.sleep(1)
    img2 = sensor.snapshot()
    log(len(img2.bytearray()))
    idiff = []
    for i in range(len(img1.bytearray())):
        p1 = int(img1.bytearray()[i])
        p2 = int(img2.bytearray()[i])
        dd = p2-p1
        idiff.append(abs(dd))
    dd = det_distribution(idiff)
    log(dd)
    dm = get_difference(dd, len(idiff))
    log(f"FINAL DIFF = {dm}")

while True:
    get_diff()
