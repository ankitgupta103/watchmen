try:
    import time
    from rsa.key import newkeys
    from rsa.pkcs1 import encrypt, decrypt, sign, verify
except ImportError as e:
    print("RSA library not found or failed to import.")
    print("Error:", e)
else:
    print("RSA library imported")

    try:
        print("\nTesting Encryption/Decryption:")

        start_key = time.ticks_ms()
        (public_key, private_key) = newkeys(2048)
        end_key = time.ticks_ms()
        keygen_time = time.ticks_diff(end_key, start_key) / 1000
        print(f"Key Generation Time: {keygen_time:.3f} seconds")

        message = "hello micropython is a small implimentation afkjnsdfnasfknsfjnskf sidfnkjsf nkjsbfkjsbfsfkjndfkjnsdkjfnkjfdnskdjfnjknsdkfjnskdjnfn dslkfsllksdsqqqqqq ".encode("utf-8")
        print(f"message_size: {len(message)}")

        start_enc = time.ticks_ms()
        encrypted_message = encrypt(message, public_key)
        end_enc = time.ticks_ms()
        enc_time = time.ticks_diff(end_enc, start_enc) / 1000
        print(f"Encryption Time: {enc_time:.3f} seconds")
        print(f"encrypted_data_size:{len(encrypted_message)}")

        start_dec = time.ticks_ms()
        decrypted_message = decrypt(encrypted_message, private_key)
        end_dec = time.ticks_ms()
        dec_time = time.ticks_diff(end_dec, start_dec) / 1000
        print(f" Decryption Time: {dec_time:.3f} seconds")
        print("Decrypted Message:", decrypted_message.decode("utf-8"))

        print("\nTesting Sign/Verify:")
        message_str = "legit data"
        hash_method = "SHA-256"
        signature = sign(message_str, private_key, hash_method)

        if verify(message_str, signature, public_key) == hash_method:
            print("Signature verified successfully!")
        else:
            print("Signature verification failed!")
    except Exception as test_error:
        print("Error during RSA operations:")
        print(test_error)
