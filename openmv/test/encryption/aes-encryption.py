import ucryptolib
import os

# --------- CONFIG ---------
KEY = b"ThisIsA16ByteKey"  # 16 bytes = AES-128
IV = os.urandom(16)        # Random IV (16 bytes)

# A long plaintext string
LONG_STRING = (
    b"OpenMV is a powerful microcontroller board for computer vision applications. "
    b"It uses Python for scripting and provides access to image processing, machine "
    b"learning, and more. This string is long enough to span multiple AES blocks."
)

# --------- PAD HELPERS ---------
def pad(data):
    pad_len = 16 - len(data) % 16
    return data + bytes([pad_len]) * pad_len

def unpad(data):
    return data[:-data[-1]]

# --------- ENCRYPT ---------
def encrypt(plaintext, key, iv):
    aes = ucryptolib.aes(key, 2, iv)  # 2 = CBC mode
    return aes.encrypt(pad(plaintext))

# --------- DECRYPT ---------
def decrypt(ciphertext, key, iv):
    aes = ucryptolib.aes(key, 2, iv)
    return unpad(aes.decrypt(ciphertext))

# --------- MAIN ---------
ciphertext = encrypt(LONG_STRING, KEY, IV)
print("Encrypted (hex):", ciphertext.hex())

plaintext = decrypt(ciphertext, KEY, IV)
print("Decrypted:", plaintext.decode())
