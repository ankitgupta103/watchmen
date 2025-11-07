import ucryptolib
import os

import time
from rsa.key import newkeys
from rsa.pkcs1 import encrypt, decrypt, sign, verify

# Generate AES-256 key (32 bytes) and IV (16 bytes)
key = os.urandom(32)
iv = os.urandom(16)

# Load the image file
with open("image.png", "rb") as f:
    data = f.read()

# PKCS7 padding
def pad(data):
    pad_len = 16 - (len(data) % 16)
    return data + bytes([pad_len] * pad_len)

padded_data = pad(data)

# AES-CBC Encryption
aes = ucryptolib.aes(key, 2, iv)  # mode 2 = CBC
encrypted_data = aes.encrypt(padded_data)

# Save encrypted image (IV + encrypted data)
with open("encrypted_image.bin", "wb") as f:
    f.write(iv + encrypted_data)

# Save AES key to transfer to PC
with open("aes_key.bin", "wb") as f:
    f.write(key)

print("AES encryption done. Files saved:")
print("- encrypted_image.bin")
print("- aes_key.bin")


# Load AES key from file
with open("aes_key.bin", "rb") as f:
    aes_key = f.read()

# RSA Key Generation
print("\nGenerating RSA Keys...")
start_key = time.time()
(public_key, private_key) = newkeys(2048)
keygen_time = time.time() - start_key
print(f"RSA Key Generation Time: {keygen_time:.3f} seconds")

# Encrypt the AES key with RSA
print("\nEncrypting AES key using RSA...")
start_enc = time.time()
rsa_encrypted_key = encrypt(aes_key, public_key)
enc_time = time.time() - start_enc
print(f"RSA Encryption Time: {enc_time:.3f} seconds")

# Decrypt the AES key using RSA
print("Decrypting AES key using RSA...")
start_dec = time.time()
decrypted_aes_key = decrypt(rsa_encrypted_key, private_key)
dec_time = time.time() - start_dec
print(f"RSA Decryption Time: {dec_time:.3f} seconds")

# Confirm decryption success
assert decrypted_aes_key == aes_key, "AES key mismatch!"
print("AES key verified!")

# Load encrypted image (IV + encrypted data)
with open("encrypted_image.bin", "rb") as f:
    iv = f.read(16)
    encrypted_image = f.read()

# Use PyCryptodome to decrypt AES data
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
except ImportError:
    print("PyCryptodome not found. Please install it with: pip install pycryptodome")
    exit(1)

cipher = AES.new(decrypted_aes_key, AES.MODE_CBC, iv)
decrypted_image = unpad(cipher.decrypt(encrypted_image), AES.block_size)

# Save the decrypted image
with open("decrypted_image.jpg", "wb") as f:
    f.write(decrypted_image)

print("\nImage decryption complete. Saved as 'decrypted_image.jpg'.")

# Test signature (optional)
print("\nTesting Signature:")
message = b"legit data"
hash_method = "SHA-256"
signature = sign(message, private_key, hash_method)

if verify(message, signature, public_key) == hash_method:
    print("Signature verified successfully!")
else:
    print("Signature verification failed!")
