# import ucryptolib
import os

import time as utime 
# from rsa.key import newkeys
# from rsa.pkcs1 import encrypt, decrypt, sign, verify
# import rsa

import random

# # --- Your RSA Keys ---
# n = 17137440455843848950481875150631737022736154257065297701812475847978114399732264735927775853371799030685286724310264465564309364089427386220887191257573292508281307329069584113167081903408457599506928088154361712265501112905423351175920217555974170362922297976183581700680237046563837134255012986832036203123759951600299568186862408890553036610966636967628186560798496806787496514526440241699655625593229083632980910855617738004743818057471515437942887009896231377488967374719942108774184891163446147523843438432365782085999110091159141885308918643274317353722487770773019656768635161675703118510899416835513918095843
# e = 65537
# d = 12615187450009533620978944762377388180537105601776113600386640711872807314742567521481967293196449343689065526967973642556402896863851647061267082225904578337076996345214214052695721993166214809542895337852371516621520212855277762649799640745729311699016745064086310511404499379547113765777433297009134539523777624900684374282201690134310128956793708925693155974317133931947830198369788194144628762425198047535927171705756461275458808811907690456799727302086389080155967585204568108550975572684331157770719110820487517512655378445684085939335175115951599496571067753599254778933192794939648200859515974319007877278793

# ---------- Helper function to RSA encryption ------------
def mod_exp(base, exp, mod):
    """Modular exponentiation (base^exp) % mod"""
    result = 1
    base %= mod
    while exp > 0:
        if exp % 2 == 1:
            result = (result * base) % mod
        exp = exp >> 1
        base = (base * base) % mod
    return result

def get_bit_length(x):    # Convert the integer to bytes before using len()
    length = 0
    while x:
        x >>= 1
        length += 1
    return length


def setup_aes():
    aes_key = os.urandom(32)
    return aes_key

# def load_rsa():
#     private_bytes = b'-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEApj9jaQGz+zyT/xjrYzAdsEOdEF1ec7ruqtgNVAuylU6uJY/I\n+LeVSvaEY3Seu4L+x99SUkp+fq05Z1nMKqKaOpXgfvLudDrXzLOFITkl5Ecag19Q\nCyjQWxm0yB2x9t3mM+VjCDJ9+Lzp8ynzHFFD18EiwRb/IarYFfiYfGRfaMzQLNri\n6zKu1xT/e+/AMFX3U9D/V/qgo4/zvW+hyFQvB3snsHX6+3f/FIt/YrsnrHmAoO7e\nUmeFhbBPw67UJMuHJs8jOPbziro2LHbrPpp8hC/gHuiHK1ll2iop9mUXAg5uBSLD\neBZ7s1A2psNTS2wR0/nMTjETxnZ2fGiF2i1gqwIDAQABAoIBAEKhARyivBmjK8V/\nnUeBj0SHtLlMUoCbmPAL6zuV/Jruj8kqGWflXAZRSrn5kWyhka9Vh87HYG8wyeLs\nEHG9/YYhb3oxrvQSaU73XBH2r4MQJEYmuxPd5bO9V8EkdaD1Sj/eXZR5eBdqz3DP\njUn6H/CmzWEJ8HLz3+reWW7xY3PCi9DgZrOt40NCTzR7rLB4dnFv1hIQx9QE1fGr\n9yvPGzq2fekY3OrntQQM54pAsEZF5aLbyMHzw/CBdXG1nxs6uK8zMxn2owQBabF5\nmGi1pQoVBB5/igQudTqGTXC3W7RmSHBCPOePzXu5OXiOiJE1CN9fl5qxtMIuamwj\nbfkHWFECgYEA6NdTc7UQ30sQZnMnE06hbGdzvNV7yKBQ9+p4jCMRKAJSUer3abTL\nnvsMFZfkBpZPLXm6VbwApm2brhol393Rl+jxfEQ4ToRvaE6pVeJ4mxytqqFBUbUK\npWmaF8J9/Emej+/KLlVOAjT3fv6MBozzHzwZCeTIKZJNekKjlgDd2+0CgYEAtshv\n/RRxUCFbaiBwjlq5rgzqKL253oj18bjJgIH6HSpzvXfEzNk79fGYuBCBc/ECnmNn\npcpYY6mZzq3uE0g5vE66cfGM6KOddPhg+GF5DhqqyonC9jDji++QPzOuOFUe8cQS\n2F5nqapB0jViJ1b4GVJXoxB9cjnmKGQg9jL3C/cCgYEAmGfA/v6okY/fpz9+dzvD\nm2JHtnWCNXsCJJQ73XZil26VlXsYAP/PPDuU2Fl4bvtZzilcVxvczRL3kMkau2LE\n+wsFbdJ1jKdRCNRcMJQxX04xOnucdq/qzQTHUQAEWOuTNyG8lAFQM0+aJGzXGL6P\nsIU02m3+un9B6WHPE7NzhK0CgYA6T0kCmIHpiSqreXvOvfycHLyakKP57QFgwo1t\ntIlAwqk3mTysCOUK+a65kXJqtUkblCSdjCaUbKeHeo8HkbPxccAi12cXVBLIHPB6\nbEX9DN7NTBNpDIGaw6rlrqv2hpkfkWhdpAg35PuofqU4XZM6KL2SZJFQXk4hNogZ\nYnrTUwKBgEtMHa26G6zgit6V1dzrMTeiCn8aL/y4BFvB0WinoRDlJxmHzA3SCFxY\nuhXJ2icxTYZ695xadA/ot1DubGFi01q2jEMKHIOERJZcq8bG3QE6NDDmILJ7vxx+\nl+oGHyCnM/zJdSR7Rb1JOsJN1d8JET4R4r0ljh3fHiEN2UmocSWY\n-----END RSA PRIVATE KEY-----\n'
#     public_bytes = b'-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEApj9jaQGz+zyT/xjrYzAd\nsEOdEF1ec7ruqtgNVAuylU6uJY/I+LeVSvaEY3Seu4L+x99SUkp+fq05Z1nMKqKa\nOpXgfvLudDrXzLOFITkl5Ecag19QCyjQWxm0yB2x9t3mM+VjCDJ9+Lzp8ynzHFFD\n18EiwRb/IarYFfiYfGRfaMzQLNri6zKu1xT/e+/AMFX3U9D/V/qgo4/zvW+hyFQv\nB3snsHX6+3f/FIt/YrsnrHmAoO7eUmeFhbBPw67UJMuHJs8jOPbziro2LHbrPpp8\nhC/gHuiHK1ll2iop9mUXAg5uBSLDeBZ7s1A2psNTS2wR0/nMTjETxnZ2fGiF2i1g\nqwIDAQAB\n-----END PUBLIC KEY-----\n'

#     priv_key = rsa.PrivateKey.load_pkcs1(private_bytes)
#     #priv_key = serialization.load_pem_private_key(private_bytes)
#     print(priv_key)

# load_rsa()

def load_rsa():
    # RSA with PEM keys - not supported on openmv and does not have support int he present lib that we are using
    # (modulus n, public exponent e, and private exponent d)
    # PEM = a format that wraps data like
    # n, e, and d using ASN.1 DER encoding → then Base64-encoded → then wrapped in headers.

    # # Construct key from numbers
    # n = <your modulus n>
    # e = <your public exponent>
    # d = <your private exponent>

    # pub_key = rsa.PublicKey(n, e)
    # priv_key = rsa.PrivateKey(n, e, d, 0, 0)  # You can use dummy 0s if p, q not available


    # --- RSA Keys ---
    n = 17137440455843848950481875150631737022736154257065297701812475847978114399732264735927775853371799030685286724310264465564309364089427386220887191257573292508281307329069584113167081903408457599506928088154361712265501112905423351175920217555974170362922297976183581700680237046563837134255012986832036203123759951600299568186862408890553036610966636967628186560798496806787496514526440241699655625593229083632980910855617738004743818057471515437942887009896231377488967374719942108774184891163446147523843438432365782085999110091159141885308918643274317353722487770773019656768635161675703118510899416835513918095843
    e = 65537
    d = 12615187450009533620978944762377388180537105601776113600386640711872807314742567521481967293196449343689065526967973642556402896863851647061267082225904578337076996345214214052695721993166214809542895337852371516621520212855277762649799640745729311699016745064086310511404499379547113765777433297009134539523777624900684374282201690134310128956793708925693155974317133931947830198369788194144628762425198047535927171705756461275458808811907690456799727302086389080155967585204568108550975572684331157770719110820487517512655378445684085939335175115951599496571067753599254778933192794939648200859515974319007877278793
    return n, e, d

n, e, d = load_rsa()


def setup_rsa():
    print("\nGeneration RSA Keys...")
    (public_key, private_key) = newkeys(2048)
    print("Modulus n =", public_key.n)
    print("Public exponent e =", public_key.e)
    print("Private exponent d =", private_key.d)

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


def encrypt_rsa(msg: bytes, n, e) -> int:    
    m = int.from_bytes(msg, 'big')
    if m >= n:
        raise ValueError("Message too large for this key size (max: 256 bytes)")
    return mod_exp(m, e, n)


def decrypt_rsa(ciphertext: int, d, n) -> bytes:
    m = mod_exp(ciphertext, d, n)
    length = (get_bit_length(m) + 7) // 8
    return m.to_bytes(length, 'big')

def encrypt_hybrid(msg, public_key):
    # AES key 32 bytes, IV 16bytes, Message encrypted.
    aes_key = os.urandom(32)
    (iv, msg_aes) = encrypt_aes(msg, aes_key)
    iv_rsa = encrypt_rsa(iv, public_key)
    aes_key_rsa = encrypt_rsa(aes_key, public_key)
    print(f"{len(aes_key)} -> {len(aes_key_rsa)}")
    print(f"{len(iv)} -> {len(iv_rsa)}")
    print(f"{len(msg)} -> {len(msg_aes)}")
    return aes_key_rsa + iv_rsa + msg_aes

def decrypt_hybrid(msg, private_key):
    return ""

def get_rand(n):
    rstr = ""
    for i in range(n):
        rstr += chr(65+random.randint(0,25))
    return rstr

# Debugging only
def test_encryption(n2, enctype):
    # clock_start = utime.ticks_ms()
    # t0 = utime.ticks_diff(utime.ticks_ms(), clock_start)
    # if enctype == "RSA" or enctype == "HYBRID":
    #     # public_key, private_key = setup_rsa()
    # elif enctype == "AES":
    #     aes_key = setup_aes()
    # else:
    #     print("WRONG INPUT")
    #     return
    # t1 = utime.ticks_diff(utime.ticks_ms(), clock_start)
    # print(f"Setup key in time {t1-t0} mili seconds")
    lenstr = 1
    for i in range(1,n2):
        # t2 = utime.ticks_diff(utime.ticks_ms(), clock_start)
        teststr = get_rand(lenstr)
        print(f"size of str is {len(teststr)} and the string is: {teststr}")
        # t3 = utime.ticks_diff(utime.ticks_ms(), clock_start)
        if enctype == "RSA":
            teststr_enc = encrypt_rsa(teststr.encode(), n, e)
            cipher_bytes = teststr_enc.to_bytes((get_bit_length(teststr_enc) + 7) // 8, 'big')
            print(f"size of encrpyted payload {len(cipher_bytes)}")
        elif enctype == "AES":
            iv, teststr_enc = encrypt_aes(teststr.encode(), aes_key)
        elif enctype == "HYBRID":
            teststr_enc = encrypt_hybrid(teststr.encode(), public_key)
        else:
            return
        # t4 = utime.ticks_diff(utime.ticks_ms(), clock_start)
        if enctype == "RSA":
            teststr_decrypt = decrypt_rsa(teststr_enc, d, n)
            print(f"decripted_text: {teststr_decrypt}")
        elif enctype == "AES":
            teststr_decrypt = decrypt_aes(teststr_enc, iv, aes_key)
        elif enctype == "HYBRID":
            teststr_decrypt = decrypt_hybrid(teststr_enc, private_key)
        else:
            return
        # t5 = utime.ticks_diff(utime.ticks_ms(), clock_start)
        # print(f"Encrypting {len(teststr)} to {len(teststr_enc)}, creation time = {t3-t2}, enc time = {t4-t3}, decrypt time = {t5-t4} : {teststr_enc}")
        if teststr.encode() != teststr_decrypt:
            print(f"Strings DONT match {teststr} != {teststr_decrypt}")
        lenstr = lenstr*2

#test_encryption(7, "HYBRID")
#test_encryption(7, "AES")
test_encryption(7, "RSA")
