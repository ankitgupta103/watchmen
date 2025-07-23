import omv

def get_unique_id():
    uid_str = omv.board_id()  # Returns a string like '\x4d\x00\x3d\x00\x1b...'
    uid_bytes = uid_str.encode('latin1')  # Convert the raw string to bytes
    uid_hex = ''.join('{:02X}'.format(b) for b in uid_bytes)
    return uid_hex

print("Unique ID:", get_unique_id())
