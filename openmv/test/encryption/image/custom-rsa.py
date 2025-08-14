import rsa

# Modular exponentiation (used in custom encrypt/decrypt)
def mod_exp(base, exp, mod):
    result = 1
    base %= mod
    while exp > 0:
        if exp % 2 == 1:
            result = (result * base) % mod
        exp = exp >> 1
        base = (base * base) % mod
    return result

# Custom encryption using integer math
def encrypt_int(message_int, e, n):
    return mod_exp(message_int, e, n)

# Custom decryption using integer math
def decrypt_int(cipher_int, d, n):
    return mod_exp(cipher_int, d, n)

# Generate new RSA keys
(public_key, private_key) = rsa.newkeys(2048)
print(f"Public Key: {public_key}")
print(f"Private Key: {private_key}")
n = public_key.n
e = public_key.e
d = private_key.d

# Define a message
original_msg = b'testing RSA compatibility'
msg_int = int.from_bytes(original_msg, 'big')

print(f"Original Message: {original_msg.decode()}")
print(f"Integer format of message: {msg_int}")

# Encrypt with PEM (rsa.encrypt)
cipher_pem = rsa.encrypt(original_msg, public_key)

# Decrypt PEM ciphertext using rsa.decrypt
decrypted_pem = rsa.decrypt(cipher_pem, private_key)
print("\n--- PEM Key Path ---")
print(f"PEM Decrypted: {decrypted_pem.decode()}")

# Encrypt using custom modular exponentiation
cipher_custom = encrypt_int(msg_int, e, n)

# Decrypt custom cipher using rsa private key
# Convert int -> bytes for rsa.decrypt to work (manually mimic `rsa.encrypt`)
cipher_custom_bytes = cipher_custom.to_bytes((cipher_custom.bit_length() + 7) // 8, byteorder='big')
try:
    decrypted_custom_via_pem = rsa.decrypt(cipher_custom_bytes, private_key)
    print("\n--- Custom Encryption + PEM Decryption ---")
    print(f"Decrypted: {decrypted_custom_via_pem.decode()}")
except:
    print("  Decryption failed — likely due to padding mismatch.")

# Step 7: Decrypt with custom logic
decrypted_custom_int = decrypt_int(cipher_custom, d, n)
decrypted_custom_bytes = decrypted_custom_int.to_bytes((decrypted_custom_int.bit_length() + 7) // 8, 'big')
print("\n--- Custom Path ---")
print(f"Custom Decrypted: {decrypted_custom_bytes.decode()}")

# Step 8: Compare
if original_msg == decrypted_custom_bytes == decrypted_pem:
    print("\n  SUCCESS: All encryption/decryption methods match!")
else:
    print("\n  ERROR: Mismatch between methods.")
