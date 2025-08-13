from machine import UART
import time

ser = UART(1, 9600, timeout=1000)
print("GPS NMEA Parser")

while True:
    if ser.any():
        data = ser.readline()
        if data:
            try:
                sentence = data.decode('utf-8').strip()
                parts = sentence.split(',')
                msg_type = parts[0]
                
                if 'RMC' in msg_type:
                    status = "Valid" if parts[2] == 'A' else "No Fix"                            # status gps fix
                    lat = parts[3] if parts[3] else "No data"                                    # latitude 
                    lon = parts[5] if parts[5] else "No data"                                    # longitude
                    speed = parts[7] if parts[7] else "0"
                    print(f"Position: {status} | Lat: {lat} | Lon: {lon} | Speed: {speed} knots")
                
                elif 'GGA' in msg_type:
                    fix = ["No fix", "GPS", "DGPS"][int(parts[6])] if parts[6].isdigit() else "No fix"      # fix status
                    sats = parts[7] if parts[7] else "0"                                                    # satellite connected
                    alt = parts[9] if parts[9] else "0"                                                     # altitude
                    print(f"Fix: {fix} | Satellites: {sats} | Altitude: {alt}m")
                
                elif 'GSV' in msg_type:
                    system = "GPS" if 'GP' in msg_type else "GLONASS"
                    total_sats = parts[3] if parts[3] else "0"
                    print(f"{system}: {total_sats} satellites visible")
                
                elif 'VTG' in msg_type:
                    course = parts[1] if parts[1] else "0"
                    speed_kmh = parts[7] if parts[7] else "0"
                    print(f"Course: {course}° | Speed: {speed_kmh} km/h")
                
                elif 'GSA' in msg_type:
                    fix_type = ["No fix", "2D", "3D"][int(parts[2])-1] if parts[2].isdigit() and int(parts[2]) <= 3 else "No fix"
                    print(f"Fix type: {fix_type}")
                
            except:
                pass
    
    time.sleep(0.01)
