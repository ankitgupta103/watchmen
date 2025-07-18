import os
import time
from rsa.key import newkeys
from rsa.pkcs1 import encrypt as rsa_encrypt, decrypt as rsa_decrypt, sign, verify
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# Load Image
image_path = "image.jpg"
with open(image_path, "rb") as f:
    image_data = f.read()

print(f"Original Image Size: {len(image_data)} bytes")

# AES-256 CBC Encryption
aes_key = os.urandom(32)  # 256-bit key
iv = os.urandom(16)       # 128-bit IV

cipher_aes = AES.new(aes_key, AES.MODE_CBC, iv)


start_aes = time.time()
encrypted_image = cipher_aes.encrypt(pad(image_data, AES.block_size))
end_aes = time.time()
print(f"AES Encryption Time: {end_aes - start_aes:.3f} seconds")
print(f"Encrypted Image Size: {len(encrypted_image)} bytes")

# Save Encrypted Image (with IV prepended)
with open("encrypted_image.bin", "wb") as f:
    f.write(iv + encrypted_image)

# RSA Key Generation and AES Key Encryption
try:
    print("\nTesting RSA KeyGen + AES Key Encryption/Decryption:")
    start_key = time.time()
    (public_key, private_key) = newkeys(256)
    end_key = time.time()
    print(f"RSA Key Generation Time: {end_key - start_key:.3f} seconds")

    # Encrypt AES key using RSA
    start_enc = time.time()
    rsa_encrypted_aes_key = rsa_encrypt(aes_key, public_key)
    end_enc = time.time()
    print(f"RSA Encryption of AES Key Time: {end_enc - start_enc:.3f} seconds")

    # Decrypt AES key
    start_dec = time.time()
    decrypted_aes_key = rsa_decrypt(rsa_encrypted_aes_key, private_key)
    end_dec = time.time()
    print(f"RSA Decryption of AES Key Time: {end_dec - start_dec:.3f} seconds")

    assert decrypted_aes_key == aes_key, "AES key mismatch after RSA decrypt!"

except Exception as test_error:
    print("Error during RSA operations:")
    print(test_error)
    exit()

# === Step 4: Decrypt the AES-Encrypted Image ===
with open("encrypted_image.bin", "rb") as f:
    iv2 = f.read(16)
    encrypted_data = f.read()

cipher_aes_dec = AES.new(decrypted_aes_key, AES.MODE_CBC, iv2)
decrypted_image = unpad(cipher_aes_dec.decrypt(encrypted_data), AES.block_size)

# Save Decrypted Image
with open("decrypted_image.jpg", "wb") as f:
    f.write(decrypted_image)

print("Decrypted image saved as decrypted_image.jpg")

# === Step 5: Optional RSA Sign/Verify of the Original Image Data ===
print("\nTesting RSA Signature/Verification:")
message_str = b"legit data"
hash_method = "SHA-256"

signature = sign(message_str, private_key, hash_method)

if verify(message_str, signature, public_key) == hash_method:
    print("Signature verified successfully!")
else:
    print("Signature verification failed!")

# === Final Confirmation ===
if decrypted_image == image_data:
    print("\n✅ Success: Decrypted image matches the original!")
else:
    print("\n❌ Failure: Decrypted image does not match the original.")
