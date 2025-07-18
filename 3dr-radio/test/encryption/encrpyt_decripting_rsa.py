from rsa.key import newkeys
from rsa.pkcs1 import encrypt, decrypt

# Generate a public/private key pair
print("Generating RSA key pair...")
(public_key, private_key) = newkeys(512)  # 512-bit key size

# data
data = "long string to be encrypted "
print("Original Message:", data)

# data to bytes
message_bytes = data.encode("utf-8")

# encrypt with public key
encrypted_message = encrypt(message_bytes, public_key)
print("Encrypted Message (bytes):", encrypted_message)

# decript with private key
decrypted_bytes = decrypt(encrypted_message, private_key)

# decode to string
decrypted_message = decrypted_bytes.decode("utf-8")
print("Decrypted Message:", decrypted_message)
