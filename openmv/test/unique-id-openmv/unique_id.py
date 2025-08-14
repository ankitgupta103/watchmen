# import omv
# import machine

# def get_unique_id():
#     # uid_str = omv.board_id()
#     uid_str=machine.unique_id()
#     print(f"{uid_str}")
#     # uid_bytes = uid_str.encode('latin1')  # Convert the raw string to bytes
#     # uid_hex = ''.join('{:02X}'.format(b) for b in uid_bytes)
#     # return uid_hex

# print("Unique ID:", get_unique_id())


#  for d : Unique ID: 354434363736453035443436373645303544343637364530
#  for c : Unique ID: 354434363736453035443436373645303544343637364530


# 5D4676E05D4676E05D4676E0


import binascii
import machine
unique_id = binascii.hexlify(machine.unique_id())
print(f"{unique_id}")


# D: b'e076465dd7091027'
# C: b'e076465dd7194211'