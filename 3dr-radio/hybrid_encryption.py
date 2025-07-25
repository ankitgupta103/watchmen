import ucryptolib
import os

import utime
from rsa.key import newkeys
from rsa.pkcs1 import encrypt, decrypt, sign, verify

import random

aes_key = None

public_key = None
private_key = None

def setup_aes():
    aes_key = os.urandom(32)
    return aes_key

setup_aes()

def setup_rsa():
    global private_key
    global public_key
    print("\nGenerating RSA Keys...")
    (public_key, private_key) = newkeys(1024)

def pad(data):
    pad_len = 16 - (len(data) % 16)
    return data + bytes([pad_len] * pad_len)

def unpad(data):
    num_bytes_to_remove = 0 - int(data[-1])
    return data[:num_bytes_to_remove]

def encrypt_aes(msgstr):
    global aes_key
    iv = os.urandom(16)
    aes = ucryptolib.aes(aes_key, 2, iv)  # mode 2 = CBC
    msg = msgstr.encode()
    padded_data = pad(msg)
    encrypted_data = aes.encrypt(padded_data)
    return (iv, encrypted_data)

def decrypt_aes(encrypted_msg, iv, aes_key):
    aes = ucryptolib.aes(aes_key, 2, iv)  # mode 2 = CBC
    decrypted_msg = unpad(aes.decrypt(encrypted_msg))
    return decrypted_msg.decode()

def encrypt_rsa(msgstr):
    return encrypt(msg.encode(), public_key)
def decrypt_rsa(msg):
    return decrypt(msg, private_key)

def get_rand(n):
    rstr = ""
    for i in range(n):
        rstr += chr(65+random.randint(0,25))
    return rstr

def test_encryption():
    clock_start = utime.ticks_ms()
    t0 = utime.ticks_diff(utime.ticks_ms(), clock_start)
    setup_rsa()
    t1 = utime.ticks_diff(utime.ticks_ms(), clock_start)
    print(f"Setup key in time {t1-t0} mili seconds")
    print(private_key)
    print(public_key)
    lenstr = 1
    for i in range(1,15):
        t2 = utime.ticks_diff(utime.ticks_ms(), clock_start)
        teststr = get_rand(lenstr)
        t3 = utime.ticks_diff(utime.ticks_ms(), clock_start)
        teststr_enc = encrypt_rsa(teststr)
        t4 = utime.ticks_diff(utime.ticks_ms(), clock_start)
        teststr_decrypt = decrypt_rsa(teststr_enc)
        t5 = utime.ticks_diff(utime.ticks_ms(), clock_start)
        print(f"Encrypting {len(teststr)} to {len(teststr_enc)}, creation time = {t3-t2}, enc time = {t4-t3}, decrypt time = {t5-t4}")
        if teststr != teststr_decrypt:
            print(f"Strings DONT match {teststr} != {teststr_decrypt}")
        lenstr = lenstr*2

test_encryption()
