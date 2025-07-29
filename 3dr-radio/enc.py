import ucryptolib
import os

import time as utime
from rsa.key import newkeys, PublicKey, PrivateKey
from rsa.pkcs1 import encrypt, decrypt, sign, verify
import rsa

import random

def setup_aes():
    aes_key = os.urandom(32)
    return aes_key

def load_rsa():
    # manual key serialization/deserialization using raw key parameters.
    # Serialization: Taking a cryptographic key and converting it into a storable format (e.g., PEM, DER, or just the raw numbers like n, e, d, p, q).
    # Deserialization: Rebuilding the cryptographic key in code using stored components.

    # what we are doing:
    # PEM/DER ➝ Extract values (n, e, d, p, q) ➝ Manually hardcode into load_rsa() ➝ Rebuild key object

    # --- PUBLIC KEY ---
    n_pub = 152441823908404557362214767557350589106013792741806289657208298089556167965536667429082623995020787516515209504946658319024466865429022908659957690675940073330305701700193571633549408473735301772752128854570423969428341585699860853370683657725906897061760716981268723043741844470889741734251686755070173695469
    e_pub = 65537

    # ----- PRIVATE KEY -----
    n_pvt = 152441823908404557362214767557350589106013792741806289657208298089556167965536667429082623995020787516515209504946658319024466865429022908659957690675940073330305701700193571633549408473735301772752128854570423969428341585699860853370683657725906897061760716981268723043741844470889741734251686755070173695469
    e_pvt = 65537
    d_pvt = 133852095103668771127891859546328633445314306473095242966935494660474383715714901921152320029807150428580309305615994826865174569649406034436078279362544782912816406599121774843534998697852083103271878516538711789463629422695069574790920239295925246845687143110016595954642049484306193016625322307765875584833
    p_pvt = 54137872518586066428065259475575123095352601899560449314382010149743102607270875775315111936095659046201999800652032431793987923941632868241235084462348925335790257
    q_pvt = 2815807434177798053330341292205540643956644077257934425226716226041811227539080727183852892408367011268284606225071873703614458322710358024312317

    pubkey = PublicKey(n_pub, e_pub)
    privkey = PrivateKey(n_pvt, e_pvt, d_pvt, p_pvt, q_pvt)

    return pubkey, privkey


def setup_rsa():
    print("\nGeneration RSA Keys...")
    (pubkey, privkey) = newkeys(1024)

    # Save keys in PEM format
    #with open("public.pem", "wb") as f:
    #    f.write(pubkey.save_pkcs1(format='PEM'))

    #with open("private.pem", "wb") as f:
    #    f.write(privkey.save_pkcs1(format='PEM'))

    # Print components for use in custom encryption
    print("----- PUBLIC KEY -----")
    print(f"n_pub = {pubkey.n}")
    print(f"e_pub = {pubkey.e}")

    print("\n----- PRIVATE KEY -----")
    print(f"n_pvt = {privkey.n}")
    print(f"e_pvt = {privkey.e}")
    print(f"d_pvt = {privkey.d}")
    print(f"p_pvt = {privkey.p}")
    print(f"q_pvt = {privkey.q}")

def pad(data):
    pad_len = 16 - (len(data) % 16)
    return data + bytes([pad_len] * pad_len)

def unpad(data):
    num_bytes_to_remove = 0 - int(data[-1])
    return data[:num_bytes_to_remove]

def encrypt_aes(msg, aes_key):
    iv = os.urandom(16)
    aes = ucryptolib.aes(aes_key, 2, iv)  # mode 2 = CBC
    padded_data = pad(msg)
    encrypted_data = aes.encrypt(padded_data)
    return (iv, encrypted_data)

def decrypt_aes(encrypted_msg, iv, aes_key):
    aes = ucryptolib.aes(aes_key, 2, iv)  # mode 2 = CBC
    decrypted_msg = unpad(aes.decrypt(encrypted_msg))
    return decrypted_msg

def encrypt_rsa(msgstr, public_key): # Max 117 bytes
    return encrypt(msgstr, public_key)

def decrypt_rsa(msgstr, private_key):
    return decrypt(msgstr, private_key)

def encrypt_hybrid(msg, public_key):
    # AES key 32 bytes, IV 16bytes, Message encrypted.
    aes_key = os.urandom(32)
    (iv, msg_aes) = encrypt_aes(msg, aes_key)
    iv_rsa = encrypt_rsa(iv, public_key)
    aes_key_rsa = encrypt_rsa(aes_key, public_key)
    return aes_key_rsa + iv_rsa + msg_aes

def decrypt_hybrid(msg, private_key):
    aes_key = decrypt_rsa(msg[:256], private_key)
    iv = decrypt_rsa(msg[256:512], private_key)
    msg_decrypt = decrypt_aes(msg[512:], iv, aes_key)
    return msg_decrypt

# Debugging only
def get_rand(n):
    rstr = ""
    for i in range(n):
        rstr += chr(65+random.randint(0,25))
    return rstr

# Debugging only
def test_encryption(n1,n2, enctype):
    clock_start = utime.ticks_ms()
    t0 = utime.ticks_diff(utime.ticks_ms(), clock_start)
    if enctype == "RSA" or enctype == "HYBRID":
        # public_key, private_key = setup_rsa()
        public_key, private_key = load_rsa()
    elif enctype == "AES":
        aes_key = setup_aes()
    else:
        print("WRONG INPUT")
        return
    t1 = utime.ticks_diff(utime.ticks_ms(), clock_start)
    print(f"Setup key in time {t1-t0} mili seconds")
    lenstr = n1
    laststr = ""
    for i in range(n1, n2):
        t2 = utime.ticks_diff(utime.ticks_ms(), clock_start)
        teststr = get_rand(lenstr)
        t3 = utime.ticks_diff(utime.ticks_ms(), clock_start)
        if enctype == "RSA":
            teststr_enc = encrypt_rsa(teststr.encode(), public_key)
        elif enctype == "AES":
            iv, teststr_enc = encrypt_aes(teststr.encode(), aes_key)
        elif enctype == "HYBRID":
            teststr_enc = encrypt_hybrid(teststr.encode(), public_key)
        else:
            return
        t4 = utime.ticks_diff(utime.ticks_ms(), clock_start)
        if enctype == "RSA":
            teststr_decrypt = decrypt_rsa(teststr_enc, private_key)
        elif enctype == "AES":
            teststr_decrypt = decrypt_aes(teststr_enc, iv, aes_key)
        elif enctype == "HYBRID":
            teststr_decrypt = decrypt_hybrid(teststr_enc, private_key)
        else:
            return
        t5 = utime.ticks_diff(utime.ticks_ms(), clock_start)
        print(f"{enctype} : Encrypting {len(teststr)} to {len(teststr_enc)}, creation time = {t3-t2}, enc time = {t4-t3}, decrypt time = {t5-t4}")
        if teststr.encode() != teststr_decrypt:
            print(f"Strings DONT match {teststr} != {teststr_decrypt}")
        lenstr = lenstr*2

test_encryption(1024, 10, "HYBRID")
test_encryption(1024, 10, "AES")
