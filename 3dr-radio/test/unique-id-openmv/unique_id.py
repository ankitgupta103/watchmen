import omv.board

def get_unique_id():
    uid = omv.board.UID()  # Returns bytes
    uid_str = ''.join('{:02X}'.format(b) for b in uid)
    return uid_str

print("Unique ID:", get_unique_id())
