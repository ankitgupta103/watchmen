import serial
import pynmea2

def annotate_nmea_data(sentence):
    try:
        msg = pynmea2.parse(sentence.decode('ascii', errors='ignore').strip())
        msg_type = msg.sentence_type
        
        print(f"\n--- {msg_type} Message ---")
        print(f"Raw: {sentence.decode('ascii', errors='ignore').strip()}")
        
        if msg_type == 'GGA':
            print("GPS Fix Data:")
            print(f"  Time: {msg.timestamp} (UTC time of fix)")
            print(f"  Latitude: {msg.latitude} {msg.lat_dir} (decimal degrees)")
            print(f"  Longitude: {msg.longitude} {msg.lon_dir} (decimal degrees)")
            print(f"  Fix Quality: {msg.gps_qual} (0=invalid, 1=GPS, 2=DGPS)")
            print(f"  Satellites: {msg.num_sats} (number of satellites used)")
            print(f"  Altitude: {msg.altitude} {msg.altitude_units} (above sea level)")
            
        elif msg_type == 'RMC':
            print("Recommended Minimum Course:")
            print(f"  Time: {msg.timestamp} (UTC time)")
            print(f"  Status: {msg.status} (A=active, V=void)")
            print(f"  Latitude: {msg.latitude} {msg.lat_dir}")
            print(f"  Longitude: {msg.longitude} {msg.lon_dir}")
            print(f"  Speed: {msg.spd_over_grnd} knots (speed over ground)")
            print(f"  Course: {msg.true_course} degrees (true course)")
            print(f"  Date: {msg.datestamp} (DDMMYY)")
            
        elif msg_type == 'GLL':
            print("Geographic Position:")
            print(f"  Latitude: {msg.latitude} {msg.lat_dir}")
            print(f"  Longitude: {msg.longitude} {msg.lon_dir}")
            print(f"  Time: {msg.timestamp} (UTC time)")
            print(f"  Status: {msg.status} (A=valid, V=invalid)")
            
        elif msg_type == 'VTG':
            print("Track and Ground Speed:")
            print(f"  True Course: {msg.true_track} degrees")
            print(f"  Speed (knots): {msg.spd_over_grnd_kts} knots")
            print(f"  Speed (km/h): {msg.spd_over_grnd_kmph} km/h")
            
        elif msg_type == 'GSA':
            print("GPS DOP and Active Satellites:")
            print(f"  Mode: {msg.mode} (M=manual, A=automatic)")
            print(f"  Fix Type: {msg.mode_fix_type} (1=no fix, 2=2D, 3=3D)")
            print(f"  Satellites Used: {[getattr(msg, f'sv_id{i:02d}') for i in range(1,13) if getattr(msg, f'sv_id{i:02d}')]}")
            print(f"  PDOP: {msg.pdop} (position dilution of precision)")
            print(f"  HDOP: {msg.hdop} (horizontal dilution of precision)")
            print(f"  VDOP: {msg.vdop} (vertical dilution of precision)")
            
        elif msg_type == 'GSV':
            print("Satellites in View:")
            print(f"  Total Messages: {msg.num_messages}")
            print(f"  Message Number: {msg.msg_num}")
            print(f"  Satellites in View: {msg.num_sv_in_view}")
            print("  Satellite Details:")
            for i in range(1, 5):
                prn = getattr(msg, f'sv_prn_{i:02d}', None)
                if prn:
                    elevation = getattr(msg, f'elevation_{i:02d}', 'N/A')
                    azimuth = getattr(msg, f'azimuth_{i:02d}', 'N/A')
                    snr = getattr(msg, f'snr_{i:02d}', 'N/A')
                    print(f"    Satellite {prn}: Elevation={elevation}°, Azimuth={azimuth}°, SNR={snr}dB")
        
        else:
            print(f"Other NMEA sentence type: {msg_type}")
            print(f"  Content: {str(msg)}")
            
    except Exception as e:
        print(f"Error parsing: {e}")
        print(f"Raw data: {sentence.decode('ascii', errors='ignore').strip()}")

def main():
    port = "/dev/ttyAMA0"
    baudrate = 9600
    
    try:
        ser = serial.Serial(port, baudrate=baudrate, timeout=1)
        print(f"Connected to GPS on {port}")
        print("Reading GPS data... Press Ctrl+C to stop\n")
        
        while True:
            data = ser.readline()
            if data:
                annotate_nmea_data(data)
                
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'ser' in locals():
            ser.close()
            print("GPS connection closed")

if __name__ == "__main__":
    main()