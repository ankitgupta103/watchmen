import time
from machine import UART

# Configuration
UART_ID = 1              # UART port on OpenMV
BAUDRATE = 115200        # EC200U module baud rate
TZ_OFFSET = 5.5          # Timezone offset (IST = UTC+5:30)

uart = UART(UART_ID, BAUDRATE, timeout=2000)


def send_at(cmd, wait_ms=1000):
    """Send AT command to module and return response."""
    uart.write((cmd + "\r\n").encode())
    end = time.ticks_ms() + wait_ms
    resp = b""
    while time.ticks_diff(end, time.ticks_ms()) > 0:
        if uart.any():
            resp += uart.read()
        time.sleep_ms(10)
    return resp


def utc_to_local(dd, mo, yy, hh, mm, ss):
    """Convert UTC time to local time using timezone offset."""
    # Convert to integers
    dd, mo = int(dd), int(mo)
    # Add timezone offset to UTC time (in seconds)
    secs = int(hh) * 3600 + int(mm) * 60 + int(ss) + int(TZ_OFFSET * 3600)
    # Handle day rollover (next/previous day)
    if secs >= 86400:
        secs -= 86400
        dd += 1
    elif secs < 0:
        secs += 86400
        dd -= 1
    
    # Convert back to hours, minutes, seconds
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return "%02d/%02d/20%s %02d:%02d:%02d" % (dd, mo, yy, h, m, s)


def parse_gps(resp):
    """Parse AT+QGPSLOC? response: extracts lat, lon, and time from +QGPSLOC: response."""
    try:
        text = resp.decode("ascii")
    except:
        return None, None, None
    
    # Check for errors or missing GPS data
    if "+CME ERROR" in text or "+QGPSLOC:" not in text:
        return None, None, None
    
    for line in text.split("\n"):
        if not line.startswith("+QGPSLOC:"):
            continue
        
        # Format: +QGPSLOC: hhmmss.sss,ddmm.mmmmN/S,dddmm.mmmmE/W,...,ddmmyy
        parts = line.split(":")[1].strip().split(",")
        if len(parts) < 10:
            continue
        
        # Extract UTC time (hhmmss.sss) and date (ddmmyy)
        utc, lat_f, lon_f, date = parts[0], parts[1], parts[2], parts[9]
        hh, mm, ss = utc[0:2], utc[2:4], utc[4:6]
        dd, mo, yy = date[0:2], date[2:4], date[4:6]
        timestr = utc_to_local(dd, mo, yy, hh, mm, ss)
        
        # Convert NMEA format to decimal degrees (e.g., 2825.1513N -> 28.419188)
        def to_deg(s, is_lat):
            d = int(s[0:2 if is_lat else 3])      # degrees
            m = float(s[2 if is_lat else 3:])     # minutes
            return d + m / 60.0
        
        lat = to_deg(lat_f[:-1], True)
        lon = to_deg(lon_f[:-1], False)
        # Handle hemisphere (S/W = negative)
        if lat_f[-1] == "S":
            lat = -lat
        if lon_f[-1] == "W":
            lon = -lon
        
        return lat, lon, timestr
    
    return None, None, None


def main():
    print("EC200U GPS Reader")
    time.sleep_ms(2000)  # Wait for module to initialize
    
    # AT - Test AT command communication
    if b"OK" not in send_at("AT", 500):
        print("No AT response!")
        return
    
    # ATE0 - Disable echo (cleaner output)
    send_at("ATE0", 500)
    
    # AT+QGPS=1 - Enable GPS/GNSS on EC200U module
    if b"OK" not in send_at("AT+QGPS=1", 3000):
        print("GPS enable failed!")
        return
    
    print("Waiting for GPS fix...")
    while True:
        # AT+QGPSLOC? - Query current GPS location (returns lat, lon, time, etc.)
        resp = send_at("AT+QGPSLOC?", 3000)
        # Print raw GPS response
        try:
            print("RAW GPS RESP:", resp.decode("ascii").strip())
        except:
            print("RAW GPS RESP:", resp)
        
        lat, lon, t = parse_gps(resp)
        if lat:
            print("GPS: %s, lat=%.6f, lon=%.6f" % (t, lat, lon))
        else:
            print("No fix...")
        time.sleep(5)  # Query every 5 seconds


if __name__ == "__main__":
    main()
