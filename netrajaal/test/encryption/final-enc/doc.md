# Encryption API - Quick Reference

## Imports
```python
import os, time as utime, random
from rsa.key import newkeys, PublicKey, PrivateKey
from rsa.pkcs1 import encrypt, decrypt, sign, verify
import rsa
# import ucryptolib  # For AES
```

## Key Functions
- `load_rsa()` → Returns (public_key, private_key) - pre-configured keys
- `setup_aes()` → Returns 32-byte AES key

## Encryption APIs
- `encrypt_rsa(msg_bytes, public_key)` → encrypted_data (max 117 bytes)
- `decrypt_rsa(encrypted_data, private_key)` → original_bytes
- `encrypt_hybrid(msg_bytes, public_key)` → encrypted_data (for large files)  
- `decrypt_hybrid(encrypted_data, private_key)` → original_bytes
- `encrypt_aes(msg_bytes, aes_key)` → (iv, encrypted_data)
- `decrypt_aes(encrypted_data, iv, aes_key)` → original_bytes

## Usage
```python
pub, priv = load_rsa()
encrypted = encrypt_hybrid("Hello".encode(), pub)  # Use hybrid for most cases
decrypted = decrypt_hybrid(encrypted, priv).decode()
```