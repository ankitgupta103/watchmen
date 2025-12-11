# spi_slave_simple.py  (run on the OpenMV Cam)
import time
import rpc
import sensor

# optional camera init if you want to produce data based on images
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)

# Create the SPI slave RPC interface.
# Use the cs_pin name that matches your wiring (e.g. "P3").
# If your firmware doesn't have rpc_spi_slave() this will raise an AttributeError.
try:
    iface = rpc.rpc_spi_slave(cs_pin="P3", clk_polarity=1, clk_phase=0)
except Exception as e:
    raise RuntimeError("rpc_spi_slave not available on this firmware: " + str(e))

# Example: a very small RPC callback that reads 1 command byte and writes a 4-byte response.
def on_cmd(in_bytes):
    # in_bytes is a bytes object received from master
    # Parse a single command byte (or more)
    if len(in_bytes) < 1:
        cmd = 0
    else:
        cmd = in_bytes[0]

    # Example behavior: echo cmd and 3 status bytes
    # (you can compute these from sensor, math, etc)
    resp = bytes([cmd, 0xAA, 0x55, 0x01])
    return resp  # rpc will send this back to master

# Register the callback name; the master will invoke it by name.
# When the master calls the registered RPC function it will send bytes and get our return bytes.
iface.register_callback("do_cmd", on_cmd)

print("SPI RPC slave ready. waiting for master...")

# main loop: let the RPC interface handle incoming requests
while True:
    iface.loop()     # processes incoming SPI/RPC requests
    time.sleep_ms(10)
