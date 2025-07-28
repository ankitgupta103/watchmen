import rsa

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

# --- Your RSA Keys ---
n = 17137440455843848950481875150631737022736154257065297701812475847978114399732264735927775853371799030685286724310264465564309364089427386220887191257573292508281307329069584113167081903408457599506928088154361712265501112905423351175920217555974170362922297976183581700680237046563837134255012986832036203123759951600299568186862408890553036610966636967628186560798496806787496514526440241699655625593229083632980910855617738004743818057471515437942887009896231377488967374719942108774184891163446147523843438432365782085999110091159141885308918643274317353722487770773019656768635161675703118510899416835513918095843
e = 65537
d = 12615187450009533620978944762377388180537105601776113600386640711872807314742567521481967293196449343689065526967973642556402896863851647061267082225904578337076996345214214052695721993166214809542895337852371516621520212855277762649799640745729311699016745064086310511404499379547113765777433297009134539523777624900684374282201690134310128956793708925693155974317133931947830198369788194144628762425198047535927171705756461275458808811907690456799727302086389080155967585204568108550975572684331157770719110820487517512655378445684085939335175115951599496571067753599254778933192794939648200859515974319007877278793


def et_bit_length(n):
    length = 0
    while n:
        length += 1
        n >>= 1
    return length

# --- Helper Functions ---
def rsa_encrypt(message: bytes) -> int:
    m = int.from_bytes(message, 'big')
    if m >= n:
        raise ValueError("Message too large for this key size")
    return mod_exp(m, e, n)

def rsa_decrypt(ciphertext: int) -> bytes:
    m = mod_exp(ciphertext, d, n)
    length = (et_bit_length(m) + 7) // 8
    return m.to_bytes(length, 'big')

# --- Example Usage ---
test_msg = b'this is an test to encrypt and decrypt message of big length to know the caapabnility of the encryption is it feasableaaaaaaaaa ' * 2
print(f"length of the raw message: {len(test_msg)}\n")
print("Original:", test_msg)

cipher = rsa_encrypt(test_msg)
print("Encrypted:", cipher)

# Convert the integer to bytes before using len()
def get_bit_length(x):
    length = 0
    while x:
        x >>= 1
        length += 1
    return length

cipher_bytes = cipher.to_bytes((get_bit_length(cipher) + 7) // 8, 'big')
# cipher_bytes = cipher.to_bytes((cipher.bit_length() + 7) // 8, byteorder='big')
print(f"Length of the encrypted message: {len(cipher_bytes)}")

decrypted = rsa_decrypt(cipher)
print("Decrypted:", decrypted)

print("Match:", decrypted == test_msg)



# ----------- How to generate the raw numerical components of rsa key --------------
# import rsa

# (public_key, private_key) = rsa.newkeys(2048)

# print("Modulus n =", public_key.n)
# print("Public exponent e =", public_key.e)
# print("Private exponent d =", private_key.d)



# ----------- Explanation of the part of rsa key signing ---------
# RSA with PEM keys - not supported on openmv and does not have support int he present lib that we are using
# (modulus n, public exponent e, and private exponent d)
# PEM = a format that wraps data like
# n, e, and d using ASN.1 DER encoding → then Base64-encoded → then wrapped in headers.

# These are raw numerical components of an RSA key:

# Component	                       Description
#   n	                  modulus = p * q, product of two primes
#   e	                  public exponent (usually 65537)
#   d                     private exponent, used for decryption/signing



# ------------- How to cunstruct raw components to PEM----------
# import rsa

# # Construct key from numbers
# n = <your modulus n>
# e = <your public exponent>
# d = <your private exponent>

# pub_key = rsa.PublicKey(n, e)
# priv_key = rsa.PrivateKey(n, e, d, 0, 0)  # You can use dummy 0s if p, q not available

# # Save PEM format
# with open("public.pem", "wb") as f:
#     f.write(pub_key.save_pkcs1("PEM"))

# with open("private.pem", "wb") as f:
#     f.write(priv_key.save_pkcs1("PEM"))

