import binascii
import machine
print(f"{binascii.hexlify(machine.unique_id())}")