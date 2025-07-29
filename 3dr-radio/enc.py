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
    n_pub = 22788023319565546964263399487675758137134779014563887812402564676347235286203662278798252463309843749572558050377812950473772344470408068709507263466037392754644463132672018210761757646035765011468017486843485144747863589450319153919124613159609813779453925784301408357494466310743127724136265019125406089502804979612894073352852336424615933644290442180436989092950385571606262163549565571508511435133387552524942610987659097451406657739575129713411339017124178057747724924536107411786446815442728535005874007582828385800558657265363667954379266971760279451132325516903787018690388587823380840591503381436455329575087
    e_pub = 65537

    # --- PRIVATE KEY ---
    n_pvt = 22788023319565546964263399487675758137134779014563887812402564676347235286203662278798252463309843749572558050377812950473772344470408068709507263466037392754644463132672018210761757646035765011468017486843485144747863589450319153919124613159609813779453925784301408357494466310743127724136265019125406089502804979612894073352852336424615933644290442180436989092950385571606262163549565571508511435133387552524942610987659097451406657739575129713411339017124178057747724924536107411786446815442728535005874007582828385800558657265363667954379266971760279451132325516903787018690388587823380840591503381436455329575087
    e_pvt = 65537
    d_pvt = 22019231346183191587331492682859378058077071209794051598458959224474190483759298067765966331866871618863112609643794847211531005171629176787131802893789522461824851188482662087289608384467718313566743600894922567043093362002089060242038623265414209795957997836591100990992791455118777274798461311976951809929437378746806626328429839836891170784071446319762599977442866348517870338501978884864460666338265895856682876491715957103211125089660740283907856453251479662394349576236107768961717434521345558283452345179034647351836318798508223196970733173677737550316288821826956411589716342273535422566472124565081380965713
    p_pvt = 2942860722325352248824979440303575458041409193000328280802090629397643563051064231544082337553718254157559200409920496365994173046105910681205595362162134483306364761624488826256927832445515929270945746302532414047391861248713962530589168245754788666322526075666067444350758878974451726204960894573085244896288851285146667944827
    q_pvt = 7743493651156958793749374077568144280884491329973964668680116243000387302014066600798141433995648307750449595915728136234065175868223125399484074091889608807323140544904710586397752151655501444853473084640092002267792596765059907563573704283230338021933395117132424347918259620693456748381

    pubkey = PublicKey(n_pub, e_pub)
    privkey = PrivateKey(n_pvt, e_pvt, d_pvt, p_pvt, q_pvt)

    return pubkey, privkey

def setup_rsa():
    print("\nGeneration RSA Keys...")
    (public_key, private_key) = newkeys(2048)

    # # Save key in DER format
    # with open("pubkey.der", "wb") as f:
    #     f.write(pubkey.save_pkcs1(format='DER'))

    # with open("privkey.der", "wb") as f:
    #     f.write(privkey.save_pkcs1(format='DER'))

    # Save keys in PEM format
    with open("public.pem", "wb") as f:
        f.write(pubkey.save_pkcs1(format='PEM'))

    with open("private.pem", "wb") as f:
        f.write(privkey.save_pkcs1(format='PEM'))

    # Print components for use in custom encryption
    print("----- PUBLIC KEY -----")
    print("n =", pubkey.n)
    print("e =", pubkey.e)

    print("\n----- PRIVATE KEY -----")
    print("n =", privkey.n)
    print("e =", privkey.e)
    print("d =", privkey.d)
    print("p =", privkey.p)
    print("q =", privkey.q)



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

test_encryption(7, "HYBRID")
test_encryption(7, "AES")
test_encryption(7, "RSA")
