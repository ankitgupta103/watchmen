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

def load_rsa_pub():
    # --- PUBLIC KEY ---
    n_pub = 134757328335095073264107487580236751075497529325796582413778089501277032934474732458456051033549436336663731983176518897577428529619416759550357638328534147420836000895848725276125919429970241050547236918537990787197869670219106130399791082068749626382827068666665788771701212727840387879898818585324380393767
    e_pub = 65537
    return PublicKey(n_pub, e_pub)

def load_rsa_prv():
    # --- PRIVATE KEY ---
    n_pvt = 134757328335095073264107487580236751075497529325796582413778089501277032934474732458456051033549436336663731983176518897577428529619416759550357638328534147420836000895848725276125919429970241050547236918537990787197869670219106130399791082068749626382827068666665788771701212727840387879898818585324380393767
    e_pvt = 65537
    d_pvt = 129581867215125677359416114062384913144908285367223104867728080326692991982095574096035832218964637959268022484700004896857188243841122483282169385195600397749104751582544242676968813573435276435780296838193793364689250761289975699268807322831617942170637411240074770791871778711210551609564279704871862852033
    p_pvt = 53473502994337956307730497488750698087352716591628935084418147346112279308966922112008552876214706995044264539806129783878996654353064960856832850151888740416109183
    q_pvt = 2520076688249951711240023758723869637205488920845314634534736836435350884630668391442225601384713321448756530503563282483747207121171065283298649
    return PrivateKey(n_pvt, e_pvt, d_pvt, p_pvt, q_pvt)

def load_rsa():
    pubkey = load_rsa_pub()
    privkey = load_rsa_prv()
    return pubkey, privkey

def load_rsa_pem( pub_path='public.pem', priv_path='private.pem'):
    pubkey = load_rsa_pub()
    privkey = load_rsa_prv()
    with open(pub_path, 'w') as pub_file:
        pub_file.write(pubkey.save_pkcs1().decode())

    with open(priv_path, 'w') as priv_file:
        priv_file.write(privkey.save_pkcs1().decode())
    

def setup_rsa():
    print("\nGeneration RSA Keys...")
    (pubkey, privkey) = newkeys(1024)
    # Print components for use in custom encryption
    print(f"\t----- PUBLIC KEY -----")
    print(f"\tn_pub = {pubkey.n}")
    print(f"\te_pub = {pubkey.e}")

    print(f"\t#----- PRIVATE KEY -----")
    print(f"\tn_pvt = {privkey.n}")
    print(f"\te_pvt = {privkey.e}")
    print(f"\td_pvt = {privkey.d}")
    print(f"\tp_pvt = {privkey.p}")
    print(f"\tq_pvt = {privkey.q}")

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
    aes_key = decrypt_rsa(msg[:128], private_key)
    iv = decrypt_rsa(msg[128:256], private_key)
    msg_decrypt = decrypt_aes(msg[256:], iv, aes_key)
    return msg_decrypt

# Debugging only
def get_rand(n):
    rstr = ""
    for i in range(n):
        rstr += chr(65+random.randint(0,25))
    return rstr

# Debugging only
def test_encryption(n2, enctype):
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
    lenstr = 1
    for i in range(1,n2):
        t2 = utime.ticks_diff(utime.ticks_ms(), clock_start)
        teststr = get_rand(lenstr)
        t3 = utime.ticks_diff(utime.ticks_ms(), clock_start)
        if enctype == "RSA":
            teststr_enc = encrypt_rsa(teststr.encode(), public_key)
            # cipher_bytes = teststr_enc.to_bytes((get_bit_length(teststr_enc) + 7) // 8, 'big')
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

