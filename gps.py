import serial
import pynmea2

class Gps:
    def __init__(self):
        self.lat = None
        self.lng = None
        self.setup()

    def setup(self):
        port = "/dev/ttyAMA0"
        baudrate = 9600
        try:
            ser = serial.Serial(port, baudrate=baudrate, timeout=1)
            print(f"Connected to GPS on {port}")
            for i in range(100):
                data = ser.readline()
                if data:
                    gps = self.parse_gps(data)
                    if gps is not None:
                        (self.lat, self.lng) = gps
                        return
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if 'ser' in locals():
                ser.close()
                print("GPS connection closed")

    def parse_gps(self, sentence):
        try:
            msg = pynmea2.parse(sentence.decode('ascii', errors='ignore').strip())
            msg_type = msg.sentence_type
            print(f"Getting GPS")
            if msg_type == 'GLL':
                print("Geographic Position:")
                lat = print("{:.1f}".format(msg.latitude))
                lng = print("{:.1f}".format(msg.longitude))
                return (lat, lng)
        except Exception as e:
            print(f"Error parsing: {e}")
            print(f"Raw data: {sentence.decode('ascii', errors='ignore').strip()}")
        return None

    def get_lat_lng(self):
        if self.lat == None or self.lng == None:
            return None
        return (self.lat, self.lng)

def main():
    gps = Gps()
    print(gps.get_lat_lng())

if __name__ == "__main__":
    main()
